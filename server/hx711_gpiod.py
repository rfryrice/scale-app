import time
import gpiod

class HX711:
    """
    HX711 ADC interface using python-gpiod 2.x API (tested with v2.3.0+).
    Uses request_lines for line requests as required in v2+.
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

        # Prepare line settings, using gpiod.line.LineSettings and gpiod.line.Direction
        dout_settings = gpiod.LineSettings()
        dout_settings.direction = gpiod.line.Direction.INPUT

        pd_sck_settings = gpiod.LineSettings()
        pd_sck_settings.direction = gpiod.line.Direction.OUTPUT

        # Request both lines with correct settings using config dict
        config = {
            self.dout_pin: dout_settings,
            self.pd_sck_pin: pd_sck_settings,
        }
        # Set PD_SCK low initially
        output_values = {self.pd_sck_pin: gpiod.line.Value.INACTIVE}

        # Request lines from the chip (multi-line request)
        self.lines = gpiod.Chip(chip).request_lines(
            config=config,
            consumer="hx711",
            output_values=output_values,
        )
        # Indexing: we need to know which index in the multiline request corresponds to which pin
        # The order is the order of keys in config, which in Python 3.7+ is insertion order.
        # We'll store the index for each pin.
        self.line_indices = {pin: idx for idx, pin in enumerate(config.keys())}
        # For convenience
        self.dout_idx = self.line_indices[self.dout_pin]
        self.pd_sck_idx = self.line_indices[self.pd_sck_pin]

        self.set_gain(gain)
        # Ensure clock is low
        self.set_pd_sck(0)

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
        # get_values returns a list of values for each requested line
        return self.lines.get_values()[self.dout_idx] == gpiod.line.Value.INACTIVE

    def set_pd_sck(self, value):
        """
        Set PD_SCK line (0 or 1).
        """
        self.lines.set_value(
            1,
            gpiod.line.Value.ACTIVE if value else gpiod.line.Value.INACTIVE
        )

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
            self.set_pd_sck(1)
            time.sleep(0.000001)
            count = count << 1
            self.set_pd_sck(0)
            time.sleep(0.000001)
            if self.lines.get_values()[self.dout_idx] == gpiod.line.Value.ACTIVE:
                count += 1

        # Pulse clock to set gain/channel for next conversion
        for _ in range(self.gain_pulses):
            self.set_pd_sck(1)
            time.sleep(0.000001)
            self.set_pd_sck(0)
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
        self.set_pd_sck(0)
        self.set_pd_sck(1)
        time.sleep(0.0001)

    def power_up(self):
        """
        Power up the HX711.
        """
        self.set_pd_sck(0)
        time.sleep(0.0001)