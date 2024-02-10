#!/bin/bash
pactl set-default-sink `pactl list sinks | grep "Name: tunnel.MediaServer" | cut -d ' ' -f2-`
