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
        print("Schedule mode:",self.dev.settings.schedule_mode)
        print("Battery Level", self.dev.battery)
    
    @staticmethod 
    def scan():
        for x in eTRVDevice.scan():
            print("Address:", x[0].addr)
            # You need to press key on Danfoss to share secret key
            print("Secret Key:", x[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Danfoss heater control')
    parser.add_argument('--scan', '-S', action='store_true', dest="scan",
                    help='enable if You want scan devices')
    parser.add_argument('-t','-temperature', dest='temperature', type=int,
                    help='an integer for the temperature', default=0, nargs="?")
    parser.add_argument('-s','-schedule', dest='schedule', action="store_true",
                    help='set on schedule mode')
    parser.add_argument('-r','--roomNumber', choices=['0','1','2','3'], dest='roomNumber',            
                    help='1 - livingroom, 2 - bedroom, 3 - office, every room without argument', default='0')

    args = parser.parse_args()


    BEDROOM_KEY = bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    BEDROOM_ETRV_ADDRESS = "AA:AA:AA:AA:AA:AA"
    LIVINGROOM_KEY = bytes.fromhex("aaaaaaaaaaaaaaaaaa")
    LIVINGROOM_ETRV_ADDRESS = "AA:AA:AA:AA:AA:AA"
    OFFICE_KEY = bytes.fromhex("aaaaaaaaaaaaaaaaa")
    OFFICE_ETRV_ADDRESS = "AA:AA:AA:AA:AA:AA"
    
    if args.scan:
        print("SCANNING")
        Danfoss.scan()
    elif args.temperature != 0:
        print("SET TEMPERATURE")
        if args.roomNumber != '0':
            if args.roomNumber == '1':
                print("LIVING ROOM")
                livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
                livingroom.setScheduleMode(ScheduleMode.MANUAL)
                livingroom.setTemperature(args.temperature)
                livingroom.showStatus()
            if args.roomNumber == '2':
                print("BEDROOM")
                bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
                bedroom.setScheduleMode(ScheduleMode.MANUAL)
                bedroom.setTemperature(args.temperature)
                bedroom.showStatus()
            if args.roomNumber == '3':
                print("OFFICE")
                bedroom = Danfoss(OFFICE_ETRV_ADDRESS, OFFICE_KEY)
                bedroom.setScheduleMode(ScheduleMode.MANUAL)
                bedroom.setTemperature(args.temperature)
                bedroom.showStatus() 
        else:
            print("all rooms")
            livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
            livingroom.setScheduleMode(ScheduleMode.MANUAL)
            livingroom.setTemperature(args.temperature)
            livingroom.showStatus()
            bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
            bedroom.setScheduleMode(ScheduleMode.MANUAL)
            bedroom.setTemperature(args.temperature)
            bedroom.showStatus()
            office = Danfoss(OFFICE_ETRV_ADDRESS, OFFICE_KEY)
            office.setScheduleMode(ScheduleMode.MANUAL)
            office.setTemperature(args.temperature)
            office.showStatus()
    elif args.schedule != 0:
        print("SET SCHEDULE")
        if args.roomNumber != '0':
            if args.roomNumber == '1':
                print("LIVINGROOM")
                livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
                livingroom.setScheduleMode(ScheduleMode.SCHEDULED)
                livingroom.showStatus()
            if args.roomNumber == '2':
                print("BEDROOM")
                bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
                bedroom.setScheduleMode(ScheduleMode.SCHEDULED)
                bedroom.showStatus()
            if args.roomNumber == '3':
                print("OFFICE")
                office = Danfoss(OFFICE_ETRV_ADDRESS, OFFICE_KEY)
                office.setScheduleMode(ScheduleMode.SCHEDULED)
                office.showStatus() 
        else:
            print("all rooms")
            livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
            livingroom.setScheduleMode(ScheduleMode.SCHEDULED)
            livingroom.showStatus()
            bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
            bedroom.setScheduleMode(ScheduleMode.SCHEDULED)
            bedroom.showStatus()
            office = Danfoss(OFFICE_ETRV_ADDRESS, OFFICE_KEY)
            office.setScheduleMode(ScheduleMode.SCHEDULED)
            office.showStatus() 
    else:
        print("STATUS")
        livingroom = Danfoss(LIVINGROOM_ETRV_ADDRESS, LIVINGROOM_KEY)
        livingroom.showStatus()
        bedroom = Danfoss(BEDROOM_ETRV_ADDRESS, BEDROOM_KEY)
        bedroom.showStatus()
        office = Danfoss(OFFICE_ETRV_ADDRESS, OFFICE_KEY)
        office.showStatus()
