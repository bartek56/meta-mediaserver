#!/bin/sh

set -eu

motd_tmp="${TMPDIR:-/run}/motd.status.$$"
motd_file="${MOTD_FILE:-/etc/motd}"
trap 'rm -f "$motd_tmp"' EXIT HUP INT TERM

cpu_usage() {
    set -- $(awk '/^cpu / {print $2, $3, $4, $5, $6, $7, $8, $9}' /proc/stat)
    idle_before=$(( $4 + $5 ))
    total_before=0
    for value in "$@"; do
        total_before=$((total_before + value))
    done

    sleep 1

    set -- $(awk '/^cpu / {print $2, $3, $4, $5, $6, $7, $8, $9}' /proc/stat)
    idle_after=$(( $4 + $5 ))
    total_after=0
    for value in "$@"; do
        total_after=$((total_after + value))
    done

    total_delta=$((total_after - total_before))
    idle_delta=$((idle_after - idle_before))
    if [ "$total_delta" -gt 0 ]; then
        awk -v idle="$idle_delta" -v total="$total_delta" \
            'BEGIN { printf "%d%%", (100 * (total - idle) / total) + 0.5 }'
    else
        printf '0%%'
    fi
}

format_bytes() {
    awk -v value="$1" '
        function human(v) {
            if (v >= 1099511627776) return sprintf("%.1f TiB", v / 1099511627776)
            if (v >= 1073741824) return sprintf("%.1f GiB", v / 1073741824)
            if (v >= 1048576) return sprintf("%.1f MiB", v / 1048576)
            return sprintf("%d KiB", v / 1024)
        }
        BEGIN { print human(value) }'
}

disk_line() {
    source="$1"
    mountpoint="$2"
    used="$3"
    total="$4"
    percent="$5"
    available="$6"
    name="$(lsblk -ndo LABEL "$source" 2>/dev/null || true)"
    device="$(basename "$source")"
    [ -n "$name" ] || name="$device"
    printf 'DISK:                 %s (%s, %s) — %s / %s (%s), free %s\n' \
        "$name" "$device" "$mountpoint" "$used" "$total" "$percent" "$available"
}

cpu="$(cpu_usage)"
host_name="$(hostname)"
host_padding=$(( (60 - ${#host_name}) / 2 ))
[ "$host_padding" -lt 0 ] && host_padding=0
ram_total_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
ram_available_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
ram_used_kib=$((ram_total_kib - ram_available_kib))
ram_percent=$((100 * ram_used_kib / ram_total_kib))

root_row="$(df -P -B1 / | awk 'NR == 2 {print $2, $3, $4, $5}')"
set -- $root_row
root_total="$1"
root_used="$2"
root_available="$3"
root_percent="$4"
root_source="$(df -P / | awk 'NR == 2 {print $1}')"
root_device="$(basename "$root_source")"
root_name="$(lsblk -ndo LABEL "$root_source" 2>/dev/null || true)"
[ -n "$root_name" ] || root_name="$root_device"

{
    printf '%s\n' '============================================================'
    printf '%*s%s\n' "$host_padding" '' "$host_name"
    printf '%s\n' '============================================================'
    printf 'CPU:                  %s usage\n' "$cpu"
    printf 'RAM:                  %s / %s (%s%%), free %s\n' \
        "$(format_bytes $((ram_used_kib * 1024)))" \
        "$(format_bytes $((ram_total_kib * 1024)))" \
        "$ram_percent" \
        "$(format_bytes $((ram_available_kib * 1024)))"
    printf 'SD:                   %s (%s) — %s / %s (%s), free %s\n' \
        "$root_name" "$root_device" \
        "$(format_bytes "$root_used")" "$(format_bytes "$root_total")" \
        "$root_percent" "$(format_bytes "$root_available")"

    df -P -B1 | awk 'NR > 1 && $1 ~ /^\/dev\// && $6 != "/" {print $1, $6, $3, $4, $5}' |
        while read -r source mountpoint used available percent; do
            disk_line "$source" "$mountpoint" "$(format_bytes "$used")" \
                "$(format_bytes "$((used + available))")" "$percent" "$(format_bytes "$available")"
        done
    printf '%s\n' '============================================================'
} > "$motd_tmp"

install -m 0644 "$motd_tmp" "$motd_file"
