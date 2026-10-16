from machine import Pin, PWM

class SalidaPWM:
    def __init__(self,pin, frecuencia=1000):
        self.pin_num= pin
        self.pwm = PWM(Pin(self.pin_num))
        self.pwm.freq(frecuencia)

    def escribir(self,valor):
        valor = max(0, min(100,valor)) 
        duty = int((valor/100)*65535)
        self.pwm.duty_u16(duty)

    def escribir_pot(self,valor_adc):
        duty = int((valor_adc/4095)*65535) 
        self.pwm.duty_u16(duty)