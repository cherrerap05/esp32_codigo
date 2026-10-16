import time
 
class HTU21D:
    def __init__(self, i2c, addr=0x40):
        self.i2c = i2c
        self.addr = addr
 
    def _read2(self, cmd, delay_ms=35):
        self.i2c.writeto(self.addr, bytes([cmd]))
        time.sleep_ms(delay_ms)

        d = self.i2c.readfrom(self.addr, 2)

        return (d[0] << 8) | d[1]
 
    def temperature(self):
        raw = self._read2(0xF3, delay_ms=50)
        return -46.85 + (175.72 * raw / 65536.0)
 
    def humidity(self):
        raw = self._read2(0xF5, delay_ms=50)

        rh = -6.0 + (125.0 * raw / 65536.0)

        if rh < 0:
            rh = 0

        if rh > 100:
            rh = 100

        return rh
 
    def measure(self):
        return self.temperature(), self.humidity()