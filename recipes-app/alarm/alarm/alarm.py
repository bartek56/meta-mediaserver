#!/usr/bin/env python3

import time
import os
import configparser
from mpd import MPDClient


# ---------------- CONFIG ----------------
CONFIG_FILE = "/etc/mediaserver/alarm.ini"

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

cfg = config["alarm"]

MIN_VOLUME = cfg.getint("min_volume")
MAX_VOLUME = cfg.getint("max_volume")
DEFAULT_VOLUME = cfg.getint("default_volume")
GROWING_VOLUME = cfg.getint("growing_volume")
GROWING_SPEED = cfg.getint("growing_speed")

PLAYLIST = cfg.get("playlist")
THE_NEWEST_SONGS = cfg.getboolean("the_newest_songs")


MPD_HOST = "localhost"
MPD_PORT = 6600

ALARM_CONFIG_FILE = "/tmp/alarmConfig"
# ----------------------------------------


client = MPDClient()


def connect():
    client.connect(MPD_HOST, MPD_PORT)


def prepare_mpd():
    client.stop()

    outputs = client.outputs()
    for o in outputs:
        client.disableoutput(o["outputid"])

    if outputs:
        client.enableoutput(outputs[0]["outputid"])

    client.clear()
    client.setvol(MIN_VOLUME)
    client.repeat(1)


def get_music_directory():
    conf_path = "/etc/mpd.conf"
    with open(conf_path, "r") as f:
        for line in f:
            if "music_directory" in line:
                return line.split('"')[1]
    raise RuntimeError("music_directory not found")


def play_newest_songs(offset):
    all_songs = client.listallinfo()

    songs = [s for s in all_songs if "file" in s]

    songs.sort(key=lambda x: x.get("last-modified", ""), reverse=True)

    number_of_songs = offset + 4
    selected = songs[:number_of_songs]

    client.clear()

    for s in selected:
        client.add(s["file"])

    client.random(0)
    client.play(0)

    for _ in range(offset):
        client.next()


def load_alarm_config():
    if os.path.exists(ALARM_CONFIG_FILE):
        with open(ALARM_CONFIG_FILE) as f:
            try:
                return int(f.read().strip())
            except:
                return 0
    return 0


def save_alarm_config(value):
    with open(ALARM_CONFIG_FILE, "w") as f:
        f.write(str(value))


def ensure_playing():
    status = client.status()
    if status.get("state") != "play":
        songs = client.listall()
        import random
        random.shuffle(songs)
        for s in songs[:10]:
            if "file" in s:
                client.add(s["file"])

        client.random(1)
        client.play()


def ramp_volume():
    while True:
        time.sleep(GROWING_SPEED)

        status = client.status()
        volume = int(status.get("volume", 0))

        new_volume = volume + GROWING_VOLUME
        if new_volume >= MAX_VOLUME:
            break

        client.setvol(new_volume)


def hold_max_volume():
    for i in range(10):
        print(f"MAX VALUE {i+1}")
        time.sleep(GROWING_SPEED)


def main():
    connect()
    prepare_mpd()

    if THE_NEWEST_SONGS:
        print("----- load the newest songs")

        config_param = None
        import sys
        if len(sys.argv) > 1:
            config_param = sys.argv[1]

        number_of_song = 0

        if config_param == "snooze":
            number_of_song = load_alarm_config() + 1

        save_alarm_config(number_of_song)

        play_newest_songs(number_of_song)

    else:
        print(f"----- load playlist {PLAYLIST}")
        client.load(PLAYLIST)
        client.random(1)
        client.play()

    print("----- start")
    ensure_playing()

    ramp_volume()
    hold_max_volume()

    print("----- Auto stop alarm")
    try:
        import subprocess
        subprocess.run(["systemctl", "stop", "alarm_gui.service"])
    except:
        pass

    client.stop()
    client.close()
    client.disconnect()


if __name__ == "__main__":
    main()
