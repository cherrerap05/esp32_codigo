from entrada_analoga import SenalAnaloga
import time

sensor = SenalAnaloga(2)   #el mismo pin que PIN_YL69

while True:
    print(sensor.leer_valor())
    time.sleep_ms(500)