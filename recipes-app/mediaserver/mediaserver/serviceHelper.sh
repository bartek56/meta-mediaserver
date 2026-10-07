#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Use: $0 <service_name> <start/stop>"
    exit 1
fi


SERVICE_NAME=$1
SERVICE_COMMAND=$2

START_SERVICE_NAME="start.service"

ALARM_SERVICE_NAME="alarm.service"
ALARM_SNOOZE_SERVICE_NAME="alarm_snooze.service"
ALARM_GUI_SERVICE_NAME="alarm_gui.service"
MPC_MEDIASERVER_SERVICE_NAME="mpc_mediaserver.service"

STOP_COMMAND="stop"
START_COMMAND="start"


if [ "$SERVICE_NAME" = "$ALARM_SERVICE_NAME" ] || [ "$SERVICE_NAME" = "$ALARM_SNOOZE_SERVICE_NAME" ]; then
    if [ "$SERVICE_COMMAND" = "$START_COMMAND" ]; then
            echo "alarm.service start"
            systemctl stop $START_SERVICE_NAME
            systemctl stop $MPC_MEDIASERVER_SERVICE_NAME
    elif [ "$SERVICE_COMMAND" = "$STOP_COMMAND" ]; then
            echo "alarm.service stop"
    fi

elif [ "$SERVICE_NAME" = "$ALARM_GUI_SERVICE_NAME" ]; then
    if [ "$SERVICE_COMMAND" = "$START_COMMAND" ]; then
            echo "alarm_gui.service start"
    elif [ "$SERVICE_COMMAND" = "$STOP_COMMAND" ]; then
            echo "alarm_gui.service stop"
            systemctl start $START_SERVICE_NAME
    fi

elif [ "$SERVICE_NAME" = "$MPC_MEDIASERVER_SERVICE_NAME" ]; then
    if [ "$SERVICE_COMMAND" = "$START_COMMAND" ]; then
        echo "mpc_mediaserver.service start"
        systemctl stop $START_SERVICE_NAME
    elif [ "$SERVICE_COMMAND" = "$STOP_COMMAND" ]; then
        echo "mpc_mediaserver.service stop"
        STATUS_ALARM=$(systemctl is-active alarm.service)
        STATUS_ALARMSNOOZE=$(systemctl is-active alarm_snooze.service)

        if [ "$STATUS_ALARM" = "activating" ] || [ "$STATUS_ALARMSNOOZE" = "activating" ]; then
            echo "Alarm is starting. Nothing to do"
        else
            echo "Alarm is not active (status: $STATUS_ALARM). Start main app"
            systemctl start "$START_SERVICE_NAME"
        fi
    fi
fi
