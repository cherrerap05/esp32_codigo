from machine import Pin 
import time 

class Salida_Digital:
    def __init__(self, pin):
        self.pin_num = pin
        self.out = Pin(self.pin_num, Pin.OUT)

    def encender (self):
        self.out.value(1)

    def apagar (self):
        self.out.value(0)

    def toggle (self): 
        self.out.value(not self.out.value())

    def parpadear(self, intervalo=0.5, veces=None):
        
        if veces is None:
            while True:
                self.toggle()
                time.sleep(intervalo)
        else:
            for _ in range(veces):
                self.toggle()
                time.sleep(intervalo)