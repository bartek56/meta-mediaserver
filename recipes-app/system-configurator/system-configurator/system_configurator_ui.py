#!/usr/bin/env python3
"""Textual UI for hostname, network and systemd service management."""

from __future__ import annotations

import os
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, RichLog, Static

from system_configurator import SystemConfigurator


class ConfirmRebootScreen(ModalScreen[bool]):
    CSS = """
    ConfirmRebootScreen { align: center middle; }
    #dialog { width: 60; height: auto; padding: 1 2; background: $surface; border: thick $error; }
    #buttons { height: 3; align: right middle; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Configuration applied. Restart the system?")
            with Horizontal(id="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Restart", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class SystemConfiguratorApp(App[None]):
    TITLE = "MediaServer — System Configurator"
    SUB_TITLE = "Hostname, network and services"
    CSS = """
    Screen { background: $background; }
    #main { height: 1fr; }
    #navigation { width: 20; padding: 1; border: round $primary; }
    #workspace { width: 1fr; padding: 1 2; }
    #sections { height: 1fr; }
    .section { height: 1fr; overflow-y: auto; }
    #status { height: 10; padding: 1 0; }
    #actions { height: auto; }
    .field-label { margin-top: 1; color: $text-muted; }
    Input { width: 100%; }
    Checkbox { margin-top: 1; }
    .nav-button { width: 100%; margin-bottom: 1; }
    .nav-button.active { background: $primary; color: $text; }
    .service-row { height: 3; margin-top: 1; }
    .service-name { width: 1fr; padding: 1 0; }
    .service-state { width: 20; padding: 1 0; color: $text-muted; }
    .service-boot { width: 20; }
    .service-action { width: 12; }
    #apply { margin-top: 2; width: 100%; }
    #reboot { margin-top: 1; width: 100%; }
    #summary { height: auto; padding: 1; border: round $secondary; }
    RichLog { height: 5; margin-top: 1; border: round $panel; }
    """

    NETWORK_OPTIONS = {"static_ip", "ip_address", "prefix_length", "gateway", "dns"}

    def __init__(self) -> None:
        super().__init__()
        self.variant = self._detect_variant()
        self.configurator = SystemConfigurator(variant=self.variant)
        self.network_options = self.configurator.load_network_config()
        self.mode = self.configurator.system_mode()
        self._refreshing_services = False

    @staticmethod
    def _detect_variant() -> str:
        requested = os.environ.get("MEDIASERVER_CONFIGURATOR_VARIANT", "").lower()
        if requested in {"minimal", "base", "qt5"}:
            return requested
        if Path("/opt/MediaServerApp").exists():
            return "qt5"
        if Path("/usr/bin/snapserver").exists():
            return "base"
        return "minimal"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            with Vertical(id="navigation"):
                yield Button("Main", id="nav-main", classes="nav-button active")
                yield Button("Network", id="nav-network", classes="nav-button")
                yield Button("Startup", id="nav-startup", classes="nav-button")
            with Vertical(id="workspace"):
                with Container(id="sections"):
                    with Vertical(id="main-section", classes="section"):
                        yield Label("System mode", classes="field-label")
                        yield Static(self._mode_text(), id="system-mode")
                        yield Label("Hostname", classes="field-label")
                        yield Input(value=self._stored_hostname(), placeholder="e.g. mediaserver", id="hostname")
                        yield Static(id="hostname-status")

                    with Vertical(id="network-section", classes="section"):
                        yield Label("Network configuration", classes="field-label")
                        yield Checkbox(
                            "Use static IPv4 configuration",
                            value=bool(self._stored_option("static_ip", False)),
                            id="static_ip",
                        )
                        yield Static("Connection type: Ethernet", id="ethernet_info")
                        yield Label("IP address", classes="field-label")
                        yield Input(value=str(self._stored_option("ip_address", "")), id="ip_address")
                        yield Label("Prefix length (CIDR)", classes="field-label")
                        yield Input(value=str(self._stored_option("prefix_length", "24")), id="prefix_length")
                        yield Label("Gateway (optional)", classes="field-label")
                        yield Input(value=str(self._stored_option("gateway", "")), id="gateway")
                        yield Label("DNS servers (optional)", classes="field-label")
                        yield Input(value=str(self._stored_option("dns", "")), id="dns")
                        yield Static(id="network-status")

                    with Vertical(id="startup-section", classes="section"):
                        yield Label("Startup services", classes="field-label")
                        yield Static("Enable a service for boot and use Start/Stop for its current state.", id="service-help")
                        for key, label, _service in self.configurator.available_services():
                            with Horizontal(classes="service-row"):
                                yield Label(label, classes="service-name")
                                yield Static("checking...", id=f"state-{key}", classes="service-state")
                                yield Checkbox("Start at boot", id=f"boot-{key}", classes="service-boot")
                                yield Button("Start", id=f"service-{key}", classes="service-action")

                with Horizontal(id="actions"):
                    yield Button("Apply hostname and network", variant="success", id="apply")
                    yield Button("Restart system", variant="error", id="reboot", disabled=True)
                with Vertical(id="status"):
                    yield Static(id="summary")
                    yield Label("Messages", classes="field-label")
                    yield RichLog(highlight=True, markup=False, id="log")
        yield Footer()

    def on_mount(self) -> None:
        self._show_section("main")
        self._update_network_controls()
        self._refresh_configuration_status()
        self._refresh_services()
        self._refresh_summary()
        self._log(f"System mode: {self.mode} (fixed by image target).")

    def _mode_text(self) -> str:
        if self.mode == "MediaClient":
            return "MediaClient — minimal image (Snapcast client)"
        suffix = " with Qt5" if self.variant == "qt5" else ""
        return f"MediaServer — {self.variant} image{suffix}"

    def _show_section(self, section: str) -> None:
        for name in ("main", "network", "startup"):
            self.query_one(f"#{name}-section").styles.display = "block" if name == section else "none"
            button = self.query_one(f"#nav-{name}")
            button.add_class("active") if name == section else button.remove_class("active")

    def _stored_hostname(self) -> str:
        state = self.configurator.load_state()
        return str(state.get("hostname") or self.configurator.current_hostname())

    def _stored_option(self, key: str, default: object) -> object:
        if key in self.network_options:
            return self.network_options[key]
        state = self.configurator.load_state()
        options = state.get("options")
        return options.get(key, default) if isinstance(options, dict) else default

    def _log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def _refresh_summary(self) -> None:
        services = self.configurator.available_services()
        active = sum("active" in self.configurator.service_status(service) for _, _, service in services)
        self.query_one("#summary", Static).update(
            f"Mode: {self.mode} (fixed by image target)\n"
            f"Image variant: {self.variant}\n"
            f"Services available: {len(services)} | Active: {active}"
        )

    def _set_status(self, widget: Static, done: bool, text: str = "") -> None:
        widget.update(text or ("Configured" if done else "Not configured"))
        widget.styles.color = "green" if done else "yellow"

    def _refresh_configuration_status(self) -> None:
        hostname = self.query_one("#hostname", Input).value.strip()
        self._set_status(
            self.query_one("#hostname-status", Static),
            hostname == self.configurator.current_hostname(),
        )
        values = self._network_values()
        actual = self.configurator.load_network_config()
        done = all(str(actual.get(k, "")) == str(v) for k, v in values.items())
        self._set_status(self.query_one("#network-status", Static), done)

    def _refresh_services(self) -> None:
        self._refreshing_services = True
        try:
            for key, _label, service in self.configurator.available_services():
                status = self.configurator.service_status(service)
                active = "active" in status
                enabled = "enabled" in status
                self.query_one(f"#state-{key}", Static).update(status)
                self.query_one(f"#boot-{key}", Checkbox).value = enabled
                button = self.query_one(f"#service-{key}", Button)
                button.label = "Stop" if active else "Start"
        finally:
            self._refreshing_services = False

    def _network_values(self) -> dict[str, object]:
        return {
            "static_ip": self.query_one("#static_ip", Checkbox).value,
            "ip_address": self.query_one("#ip_address", Input).value.strip(),
            "prefix_length": self.query_one("#prefix_length", Input).value.strip(),
            "gateway": self.query_one("#gateway", Input).value.strip(),
            "dns": " ".join(self.query_one("#dns", Input).value.split()),
        }

    def _update_network_controls(self) -> None:
        enabled = self.query_one("#static_ip", Checkbox).value
        for field in ("ip_address", "prefix_length", "gateway", "dns"):
            self.query_one(f"#{field}", Input).disabled = not enabled

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "static_ip":
            self._update_network_controls()
            return
        if self._refreshing_services or not event.checkbox.id.startswith("boot-"):
            return
        key = event.checkbox.id.removeprefix("boot-")
        service = next((s for k, _l, s in self.configurator.available_services() if k == key), None)
        if service:
            self._service_action(service, "enable" if event.value else "disable")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("nav-"):
            self._show_section(button_id.removeprefix("nav-"))
        elif button_id == "apply":
            self._apply_configuration()
        elif button_id == "reboot":
            self.push_screen(ConfirmRebootScreen(), self._reboot_result)
        elif button_id.startswith("service-"):
            key = button_id.removeprefix("service-")
            service = next((s for k, _l, s in self.configurator.available_services() if k == key), None)
            if service:
                active = "active" in self.configurator.service_status(service)
                self._service_action(service, "stop" if active else "start")

    def _apply_configuration(self) -> None:
        hostname = self.query_one("#hostname", Input).value.strip()
        if not hostname:
            self._log("Hostname cannot be empty.")
            return
        self._apply_worker(hostname, self._network_values())

    @work(thread=True)
    def _apply_worker(self, hostname: str, options: dict[str, object]) -> None:
        try:
            self.configurator.apply(self.mode, hostname, options, log=self._log)
            self.call_from_thread(self._refresh_configuration_status)
            self.call_from_thread(self._refresh_summary)
            self.call_from_thread(self._enable_reboot)
        except Exception as exc:
            self.call_from_thread(self._log, f"Configuration failed: {exc}")

    def _enable_reboot(self) -> None:
        self.query_one("#reboot", Button).disabled = False

    @work(thread=True)
    def _service_action(self, service: str, action: str) -> None:
        try:
            if action == "enable":
                self.configurator.set_service_enabled(service, True)
            elif action == "disable":
                self.configurator.set_service_enabled(service, False)
            elif action == "start":
                self.configurator.start_service(service)
            else:
                self.configurator.stop_service(service)
            self.call_from_thread(self._log, f"{action} {service}: done")
            self.call_from_thread(self._refresh_services)
            self.call_from_thread(self._refresh_summary)
        except Exception as exc:
            self.call_from_thread(self._log, f"{action} {service}: failed: {exc}")

    def _reboot_result(self, confirmed: bool) -> None:
        if confirmed:
            os.system("systemctl reboot")


def main() -> None:
    SystemConfiguratorApp().run()


if __name__ == "__main__":
    main()
