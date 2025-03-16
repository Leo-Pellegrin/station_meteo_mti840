import smbus
import time

class PCF8591:
    def __init__(self, address=0x48, bus=1):
        self.address = address
        self.bus = smbus.SMBus(bus)

    def read(self, channel):
        assert 0 <= channel <= 3, "Le canal doit être entre 0 et 3"
        self.bus.write_byte(self.address, channel)
        self.bus.read_byte(self.address)  # Lecture initiale (nécessaire)
        return self.bus.read_byte(self.address)

    def write(self, value):
        self.bus.write_byte_data(self.address, 0x40, value)

if __name__ == "__main__":
    adc = PCF8591()
    while True:
        value = adc.read(0)
        print(f"Valeur du canal 0 : {value}")
        time.sleep(1)
