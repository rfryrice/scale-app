import time
import gpiod

class HX711:
    def __init__(self, dout_pin, pd_sck_pin, chip='/dev/gpiochip4', gain=128):
        """
        dout_pin: Data pin (DOUT) BCM number.
        pd_sck_pin: Clock pin (PD_SCK) BCM number.
        chip: gpiod chip device (default is '/dev/gpiochip4' for RPi 5).
        gain: Gain factor (128, 64, or 32).
        """
        self.dout_pin = dout_pin
        self.pd_sck_pin = pd_sck_pin
        self.gain = gain
        self.offset = 0
        self.scale = 1

        # Open GPIO chip
        self.chip = gpiod.Chip(chip)
        # Request lines
        self.dout_line = self.chip.get_line_info(self.dout_pin)
        self.pd_sck_line = self.chip.get_line_info(self.pd_sck_pin)
        self.dout_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_IN)
        self.pd_sck_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_OUT)

        self.set_gain(gain)

    def set_gain(self, gain):
        """Set HX711 gain and channel."""
        if gain == 128:
            self.gain_pulses = 1
        elif gain == 64:
            self.gain_pulses = 3
        elif gain == 32:
            self.gain_pulses = 2
        else:
            raise ValueError("Gain must be 128, 64, or 32")
        self.gain = gain

    def is_ready(self):
        """Check if HX711 is ready for data retrieval."""
        return self.dout_line.get_value() == 0

    def _read_raw(self):
        """Read 24 bits of data from HX711."""
        # Wait until ready
        timeout = time.time() + 1
        while not self.is_ready():
            if time.time() > timeout:
                raise TimeoutError("HX711 not ready")
            time.sleep(0.001)

        count = 0
        # Read 24 bits
        for _ in range(24):
            self.pd_sck_line.set_value(1)
            time.sleep(0.000001)
            count = count << 1
            self.pd_sck_line.set_value(0)
            time.sleep(0.000001)
            if self.dout_line.get_value():
                count += 1

        # Set channel and gain for next reading
        for _ in range(self.gain_pulses):
            self.pd_sck_line.set_value(1)
            time.sleep(0.000001)
            self.pd_sck_line.set_value(0)
            time.sleep(0.000001)

        # Convert from 2's complement
        if count & 0x800000:
            count |= ~0xffffff
        return count

    def read_average(self, times=5):
        return sum(self._read_raw() for _ in range(times)) / times

    def tare(self, times=15):
        """Zero the scale."""
        self.offset = self.read_average(times)
        return self.offset

    def set_scale(self, scale):
        self.scale = scale

    def get_units(self, times=5):
        """Return weight in units (grams if scale set accordingly)."""
        value = self.read_average(times) - self.offset
        return value / self.scale

    def power_down(self):
        """Power down the HX711."""
        self.pd_sck_line.set_value(0)
        self.pd_sck_line.set_value(1)
        time.sleep(0.0001)

    def power_up(self):
        """Power up the HX711."""
        self.pd_sck_line.set_value(0)
        time.sleep(0.0001)