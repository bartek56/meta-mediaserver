# Mapa konfiguracji dostarczanej przez Yocto

Mapa została przygotowana z analizy warstwy `meta-mediaserver`. Ścieżki
docelowe wynikają z `do_install()` i plików jednostek; wpisy z `/var` nie są
traktowane jako konfiguracja do automatycznego kopiowania.

| Obszar | Przepis / źródło | Typ | Migracja |
|---|---|---|---|
| MPD | `recipes-multimedia/mpd/mpd_%.bbappend`, `mpd.conf*` | konfiguracja zależna od maszyny | porównać model audio i wersję MPD; preferować recepturę |
| PulseAudio | `recipes-multimedia/pulseaudio/pulseaudio_%.bbappend` | reguły ALSA, usługa, PA policy | przenieść tylko wspólne wejścia; wyjścia audio zweryfikować na Pi |
| Snapcast | `recipes-multimedia/snapcast/snapcast_0.35.0.bb`, `snap*.conf` | konfiguracja usługi | porównać wersję i adres serwera; bez sekretów |
| MiniDLNA | `recipes-multimedia/minidlna/minidlna_%.bbappend` | konfiguracja + katalogi mediów | receptura jest źródłem; media to dane użytkownika |
| Samba | `recipes-network/samba/samba_%.bbappend`, `smb.conf` | konfiguracja usługi | nie kopiować udziałów/uprawnień bez przeglądu |
| Transmission | `recipes-network/transmission/transmission_%.bbappend`, `settings.json` | konfiguracja + stan kolejki | ustawienia porównać z nową wersją; kolejka osobno |
| Sieć | `recipes-network/wpa-supplicant/*`, `dhcpcd_%.bbappend` | sieć i systemd | klasa C; nie nadpisywać automatycznie |
| SSH | obraz ma `ssh-server-openssh`; systemowy `/etc/ssh` | tożsamość i dostęp | kluczy hosta nie kopiować; klasa C/D |
| Usługi systemd | większość `recipes-*/**/*.bb`, `systemd_system_unitdir` | jednostki | porównać z obrazem, nie migrować runtime |
| MediaServer | `recipes-app/mediaserver*`, `configscript*`, `system-configurator*` | aplikacje i first boot | przenieść dane wejściowe, nie wygenerowany stan |
| PHP/Apache/FTP | `recipes-network/apache2`, `php`, `vsftpd` | usługi sieciowe i dane dostępu | ręczna decyzja, sekrety wykluczone |
| Dane aplikacji | `/var/lib`, `/var/cache`, `/var/log` | runtime/bazy/kolejki | osobny projekt migracji danych |

Wspólne konfiguracje obrazu są składane w
`classes/mediaserver-image-common.bbclass`; wariant Qt5/HDMI jest opisany w
`classes/mediaserver-image-hdmi.bbclass` i fragmentach `conf/yocto_conf`.
Ustawienia Raspberry Pi, HDMI i urządzeń nie powinny być kopiowane ze starego
egzemplarza bez sprawdzenia `MACHINE` i sprzętu.
