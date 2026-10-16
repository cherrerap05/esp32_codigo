from machine import Pin
import time

class Entrada_digital:
    def __init__(self, pin, modo_pull=Pin.PULL_DOWN):
        self.pin_num = pin
        self.pin = Pin(self.pin_num, Pin.IN, modo_pull)

    def leer(self):
        return self.pin.value()
    