import time
import gpiod
import statistics as stat

class HX711:
    def __init__(self, dout_pin, pd_sck_pin, chip='gpiochip0', gain=128, select_channel='A'):
        if not isinstance(dout_pin, int) or not isinstance(pd_sck_pin, int):
            raise TypeError('Pins must be integers')
        self._pd_sck = pd_sck_pin
        self._dout = dout_pin
        self.gain = gain
        self.offset = 0
        self.scale = 1
        self.chip = gpiod.Chip(chip)
        self._gain_channel_A = gain
        self._offset_A_128 = 0
        self._offset_A_64 = 0
        self._offset_B = 0
        self._current_channel = ''
        self._scale_ratio_A_128 = 1
        self._scale_ratio_A_64 = 1
        self._scale_ratio_B = 1
        self._debug_mode = False
        dout_settings = gpiod.LineSettings()
        dout_settings.direction = gpiod.line.Direction.INPUT
        pd_sck_settings = gpiod.LineSettings()
        pd_sck_settings.direction = gpiod.line.Direction.OUTPUT
        config = {self._dout: dout_settings, self._pd_sck: pd_sck_settings}
        output_values = {self._pd_sck: gpiod.line.Value.INACTIVE}
        self.lines = self.chip.request_lines(
            config=config,
            consumer="hx711",
            output_values=output_values,
        )
        self.line_indices = {pin: idx for idx, pin in enumerate(config.keys())}
        self.dout_idx = self.line_indices[self._dout]
        self.pd_sck_idx = self.line_indices[self._pd_sck]
        self.select_channel(select_channel)
        self.set_gain_A(gain)
        self.set_pd_sck(0)

    def select_channel(self, channel):
        channel = channel.capitalize()
        if channel not in ('A', 'B'):
            raise ValueError('Channel must be "A" or "B"')
        self._wanted_channel = channel
        self._read()
        time.sleep(0.5)

    def set_gain_A(self, gain):
        if gain not in (128, 64, 32):
            raise ValueError("Gain must be 128, 64, or 32")
        self._gain_channel_A = gain
        self.gain = gain

    @property
    def gain_pulses(self):
        if self._wanted_channel == 'A':
            return 1 if self._gain_channel_A == 128 else 3
        else:
            return 2

    def is_ready(self):
        return self.lines.get_values()[self.dout_idx] == gpiod.line.Value.INACTIVE

    def set_pd_sck(self, value):
        self.lines.set_value(
            self._pd_sck,
            gpiod.line.Value.ACTIVE if value else gpiod.line.Value.INACTIVE
        )

    def _ready(self):
        return self.lines.get_value(self._dout).value == 0

    def _set_channel_gain(self, num):
        for _ in range(num):
            self.set_pd_sck(1)
            self.set_pd_sck(0)
        return True

    def _read(self):
        self.set_pd_sck(0)
        ready_counter = 0
        while (not self._ready() and ready_counter <= 40):
            time.sleep(0.01)
            ready_counter += 1
            if ready_counter == 50:
                return False
        data_in = 0
        for _ in range(24):
            self.set_pd_sck(1)
            self.set_pd_sck(0)
            data_in = (data_in << 1) | self.lines.get_value(self._dout).value
        if self._wanted_channel == 'A' and self._gain_channel_A == 128:
            if not self._set_channel_gain(1): return False
            self._current_channel = 'A'
            self._gain_channel_A = 128
        elif self._wanted_channel == 'A' and self._gain_channel_A == 64:
            if not self._set_channel_gain(3): return False
            self._current_channel = 'A'
            self._gain_channel_A = 64
        else:
            if not self._set_channel_gain(2): return False
            self._current_channel = 'B'
        if (data_in == 0x7fffff or data_in == 0x800000):
            return False
        if (data_in & 0x800000):
            signed_data = -((data_in ^ 0xffffff) + 1)
        else:
            signed_data = data_in
        return signed_data

    def get_raw_data_mean(self, readings=30):
        data_list = [self._read() for _ in range(readings)]
        data = [num for num in data_list if isinstance(num, int)]
        if not data: return False
        return int(stat.mean(self.outliers_filter(data)))

    def get_data_mean(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result is False: return False
        if self._current_channel == 'A' and self._gain_channel_A == 128:
            return result - self._offset_A_128
        elif self._current_channel == 'A' and self._gain_channel_A == 64:
            return result - self._offset_A_64
        else:
            return result - self._offset_B

    def get_weight_mean(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result is False: return False
        if self._current_channel == 'A' and self._gain_channel_A == 128:
            return float((result - self._offset_A_128) / self._scale_ratio_A_128)
        elif self._current_channel == 'A' and self._gain_channel_A == 64:
            return float((result - self._offset_A_64) / self._scale_ratio_A_64)
        else:
            return float((result - self._offset_B) / self._scale_ratio_B)

    def outliers_filter(self, data_list, stdev_thresh=1.0):
        if not data_list: return []
        median = stat.median(data_list)
        dists = [abs(x - median) for x in data_list]
        stdev = stat.stdev(dists) if len(dists) > 1 else 0
        if not stdev: return [median]
        return [x for x, d in zip(data_list, dists) if d / stdev < stdev_thresh]

    def tare(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result is False: return True
        if self._current_channel == 'A' and self._gain_channel_A == 128:
            self._offset_A_128 = result
            self.offset = result
        elif self._current_channel == 'A' and self._gain_channel_A == 64:
            self._offset_A_64 = result
            self.offset = result
        elif self._current_channel == 'B':
            self._offset_B = result
            self.offset = result
        else:
            return True
        return False

    def set_scale(self, scale):
        if self.gain == 128:
            self._scale_ratio_A_128 = scale
            self.scale = scale
        elif self.gain == 64:
            self._scale_ratio_A_128 = scale
            self.scale = scale

    def power_down(self):
        self.set_pd_sck(0)
        self.set_pd_sck(1)
        time.sleep(0.0001)

    def power_up(self):
        self.set_pd_sck(0)
        time.sleep(0.0001)