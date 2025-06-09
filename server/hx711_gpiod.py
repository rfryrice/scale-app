import time
import gpiod

class HX711:
    """
    HX711 ADC interface using python-gpiod 2.x API (tested with v2.3.0).
    """
    def __init__(self, dout_pin, pd_sck_pin, chip='/dev/gpiochip0', gain=128):
        """
        dout_pin: BCM GPIO number for DOUT (data output of HX711)
        pd_sck_pin: BCM GPIO number for PD_SCK (clock pin of HX711)
        chip: gpiod chip device (e.g. '/dev/gpiochip0')
        gain: 128, 64, or 32
        """
        self.dout_pin = dout_pin
        self.pd_sck_pin = pd_sck_pin
        self.gain = gain
        self.offset = 0
        self.scale = 1

        # Open the GPIO chip using python-gpiod 2.x API
        self.chip = gpiod.Chip(chip)

        # DOUT as input
        self.dout_request = self.chip.request_lines(
            consumer="hx711_dout",
            lines=[self.dout_pin],
            direction=gpiod.LineDirection.INPUT
        )
        # PD_SCK as output, start low
        self.pd_sck_request = self.chip.request_lines(
            consumer="hx711_pd_sck",
            lines=[self.pd_sck_pin],
            direction=gpiod.LineDirection.OUTPUT,
            default_vals=[0]
        )

        self.set_gain(gain)
        # Ensure clock is low
        self.pd_sck_request.set_values([0])

    def set_gain(self, gain):
        """
        Set channel/gain for next reading.
        """
        if gain == 128:
            self.gain_pulses = 1  # Channel A, gain 128
        elif gain == 64:
            self.gain_pulses = 3  # Channel A, gain 64
        elif gain == 32:
            self.gain_pulses = 2  # Channel B, gain 32
        else:
            raise ValueError("Gain must be 128, 64, or 32")
        self.gain = gain

    def is_ready(self):
        """
        Check if HX711 is ready (DOUT goes LOW).
        """
        # get_values returns a list of values for each line
        return self.dout_request.get_values()[0] == 0

    def _read_raw(self):
        """
        Read 24 raw bits from the HX711.
        """
        # Wait until chip is ready (DOUT low)
        timeout = time.time() + 1
        while not self.is_ready():
            if time.time() > timeout:
                raise TimeoutError("HX711 not ready")
            time.sleep(0.001)

        count = 0
        for _ in range(24):
            self.pd_sck_request.set_values([1])
            time.sleep(0.000001)
            count = count << 1
            self.pd_sck_request.set_values([0])
            time.sleep(0.000001)
            if self.dout_request.get_values()[0]:
                count += 1

        # Pulse clock to set gain/channel for next conversion
        for _ in range(self.gain_pulses):
            self.pd_sck_request.set_values([1])
            time.sleep(0.000001)
            self.pd_sck_request.set_values([0])
            time.sleep(0.000001)

        # Convert from 24 bit signed (two's complement)
        if count & 0x800000:
            count |= ~0xffffff  # fill upper bits with 1's for negative numbers
        return count

    def read_average(self, times=5):
        """
        Read multiple times and average.
        """
        return sum(self._read_raw() for _ in range(times)) / times

    def tare(self, times=15):
        """
        Zero the scale (set offset).
        """
        self.offset = self.read_average(times)
        return self.offset

    def set_scale(self, scale):
        """
        Set scale value (calibration ratio).
        """
        self.scale = scale

    def get_units(self, times=5):
        """
        Return scaled value (grams if scale set accordingly).
        """
        value = self.read_average(times) - self.offset
        return value / self.scale

    def power_down(self):
        """
        Power down the HX711.
        """
        self.pd_sck_request.set_values([0])
        self.pd_sck_request.set_values([1])
        time.sleep(0.0001)

    def power_up(self):
        """
        Power up the HX711.
        """
        self.pd_sck_request.set_values([0])
        time.sleep(0.0001)