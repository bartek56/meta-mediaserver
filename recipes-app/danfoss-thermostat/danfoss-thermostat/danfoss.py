import sys
import argparse
from libetrv.data_struct import ScheduleMode
from libetrv.device import eTRVDevice


class Danfoss:    
    def __init__(self, address, secret_key):
        self.dev = eTRVDevice(address, secret=secret_key, pin=b'0000')

    def setTemperature(self, temperature):
        self.dev.temperature.set_point_temperature = temperature

    def setScheduleMode(self, mode):        
        self.dev.settings.schedule_mode = mode
        self.dev.settings.save()

    def showStatus(self):
        print("Name: ", self.dev.name)
        print("Current room temperature: {:.1f}°C".format(self.dev.temperature.room_temperature))
        print("Set point temperature:    {:.1f}°C".format(self.dev.temperature.set_point_temperature))
        print("Battery Level", self.dev.battery)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Danfoss heater control')
    parser.add_argument('temperature', metavar='temp', type=int,
                    help='an integer for the temperature', default=0, nargs="?")
    parser.add_argument('roomNumber', metavar='roomNumber', type=int,
                    help='1 - livingroom, 2 - bedroom, every room without argument', default=0, nargs="?")

    args = parser.parse_args()

    BEDROOM_KEY = bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    BEDROOM_ETRV_ADDRESS = "AA:AA:AA:AA:AA:AA"
    LIVINGROOM_KEY = bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    LIVINGROOM_ETRV_ADDRESS = "AA:AA:AA:AA:AA:AA"
   
    if args.temperature:
        if args.roomNumber:
            if args.roomNumber == 1:
                livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
                livingroom.setScheduleMode(ScheduleMode.MANUAL)
                livingroom.setTemperature(args.temperature)
                livingroom.showStatus()
            if args.roomNumber == 2:
                bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
                bedroom.setScheduleMode(ScheduleMode.MANUAL)
                bedroom.setTemperature(args.temperature)
                bedroom.showStatus()
        else:
            livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
            livingroom.setScheduleMode(ScheduleMode.MANUAL)
            livingroom.setTemperature(args.temperature)
            livingroom.showStatus()
            bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
            bedroom.setScheduleMode(ScheduleMode.MANUAL)
            bedroom.setTemperature(args.temperature)
            bedroom.showStatus()
    else:
        livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
        livingroom.showStatus()
        bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
        bedroom.showStatus()

