#!/bin/bash

STATUS_ALARM=$(systemctl is-active alarm.service)
STATUS_ALARMSNOOZE=$(systemctl is-active alarm_snooze.service)

if [ "$STATUS_ALARM" = "activating" ] || [ "$STATUS_ALARMSNOOZE" = "activating" ]; then
    echo "Alarm is starting. Nothing to do"
else
    echo "Alarm is not active (status: $STATUS_ALARM). Start main app"
    systemctl start start.service
fi
