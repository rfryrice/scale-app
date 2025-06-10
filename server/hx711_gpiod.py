import time
import gpiod
import statistics as stat

class HX711:
    """
    HX711 ADC interface using python-gpiod 2.x API (tested with v2.3.0+).
    """
    def __init__(self, dout_pin, pd_sck_pin, chip='gpiochip0', gain=128, select_channel='A'):
        """
        dout_pin: BCM GPIO number for DOUT (data output of HX711)
        pd_sck_pin: BCM GPIO number for PD_SCK (clock pin of HX711)
        chip: gpiod chip device (e.g. '/dev/gpiochip0')
        gain: 128, 64, or 32
        """

        if (isinstance(dout_pin, int)):
            if (isinstance(pd_sck_pin, int)):
                self._pd_sck = pd_sck_pin
                self._dout = dout_pin
            else:
                raise TypeError('pd_sck_pin must be type int. '
                                'Received pd_sck_pin: {}'.format(pd_sck_pin))
        else:
            raise TypeError('dout_pin must be type int. '
                            'Received dout_pin: {}'.format(dout_pin))
        
        self.gain = gain
        self.offset = 0
        self.scale = 1
        self.chip = gpiod.Chip(chip)

        self._gain_channel_A = 0
        self._offset_A_128 = 0  # offset for channel A and gain 128
        self._offset_A_64 = 0  # offset for channel A and gain 64
        self._offset_B = 0  # offset for channel B
        self._last_raw_data_A_128 = 0
        self._last_raw_data_A_64 = 0
        self._last_raw_data_B = 0
        self._wanted_channel = ''
        self._current_channel = ''
        self._scale_ratio_A_128 = 1  # scale ratio for channel A and gain 128
        self._scale_ratio_A_64 = 1  # scale ratio for channel A and gain 64
        self._scale_ratio_B = 1  # scale ratio for channel B
        self._debug_mode = False
        self._data_filter = self.outliers_filter  # default it is used outliers_filter

        # Prepare line settings, using gpiod.line.LineSettings and gpiod.line.Direction
        dout_settings = gpiod.LineSettings()
        dout_settings.direction = gpiod.line.Direction.INPUT

        pd_sck_settings = gpiod.LineSettings()
        pd_sck_settings.direction = gpiod.line.Direction.OUTPUT

        # Request both lines with correct settings using config dict
        config = {
            self._dout: dout_settings,
            self._pd_sck: pd_sck_settings,
        }
        # Set PD_SCK low initially
        output_values = {self._pd_sck: gpiod.line.Value.INACTIVE}


        # Request lines from the chip (multi-line request)
        self.lines = self.chip.request_lines(
            config=config,
            consumer="hx711",
            output_values=output_values,
        )
        # Indexing: we need to know which index in the multiline request corresponds to which pin
        # The order is the order of keys in config, which in Python 3.7+ is insertion order.
        # We'll store the index for each pin.
        self.line_indices = {pin: idx for idx, pin in enumerate(config.keys())}
        # For convenience
        self.dout_idx = self.line_indices[self._dout]
        self.pd_sck_idx = self.line_indices[self._pd_sck]

        self.select_channel(select_channel)
        self.set_gain_A(gain)
        # Ensure clock is low
        self.set_pd_sck(0)

    def select_channel(self, channel):
        """
        select_channel method evaluates if the desired channel
        is valid and then sets the _wanted_channel variable.

        Args:
            channel(str): the channel to select. Options ('A' || 'B')
        Raises:
            ValueError: if channel is not 'A' or 'B'
        """
        channel = channel.capitalize()
        if (channel == 'A'):
            self._wanted_channel = 'A'
        elif (channel == 'B'):
            self._wanted_channel = 'B'
        else:
            raise ValueError('Parameter "channel" has to be "A" or "B". '
                             'Received: {}'.format(channel))
        # after changing channel or gain it has to wait 50 ms to allow adjustment.
        # the data before is garbage and cannot be used.
        self._read()
        time.sleep(0.5)

    def set_gain_A(self, gain):
        """
        Set channel/gain for next reading.
        """
        if gain == 128:
            self._gain_channel_A = gain
        elif gain == 64:
            self._gain_channel_A = gain

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
            self._pd_sck,
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

    def _save_last_raw_data(self, channel, gain_A, data):
        """
        _save_last_raw_data saves the last raw data for specific channel and gain.
        
        Args:
            channel(str):
            gain_A(int):
            data(int):
        Returns: False if error occured
        """
        if channel == 'A' and gain_A == 128:
            self._last_raw_data_A_128 = data
        elif channel == 'A' and gain_A == 64:
            self._last_raw_data_A_64 = data
        elif channel == 'B':
            self._last_raw_data_B = data
        else:
            return False

    def _ready(self):
        """
        _ready method check if data is prepared for reading from HX711

        Returns: bool True if ready else False when not ready        
        """
        # if DOUT pin is low data is ready for reading
        if self.lines.get_value(self._dout) == 0:
            return True
        else:
            return False
            
    def _set_channel_gain(self, num):
        """
        _set_channel_gain is called only from _read method.
        It finishes the data transmission for HX711 which sets
        the next required gain and channel.

        Args:
            num(int): how many ones it sends to HX711
                options (1 || 2 || 3)
        
        Returns: bool True if HX711 is ready for the next reading
            False if HX711 is not ready for the next reading
        """
        for _ in range(num):
            start_counter = time.perf_counter()
            self.set_pd_sck(1)
            self.set_pd_sck(0)
            end_counter = time.perf_counter()
            # check if hx 711 did not turn off...
            if end_counter - start_counter >= 0.00006:
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                if self._debug_mode:
                    print('Not enough fast while setting gain and channel')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                # hx711 has turned off. First few readings are inaccurate.
                # Despite it, this reading was ok and data can be used.
                result = self.get_raw_data_mean(6)  # set for the next reading.
                if result == False:
                    return False
        return True

    def _read(self):
        """
        _read method reads bits from hx711, converts to INT
        and validate the data.
        
        Returns: (bool || int) if it returns False then it is false reading.
            if it returns int then the reading was correct
        """
        self.set_pd_sck(0)  # start by setting the pd_sck to 0
        ready_counter = 0
        while (not self._ready() and ready_counter <= 40):
            time.sleep(0.01)  # sleep for 10 ms because data is not ready
            ready_counter += 1
            if ready_counter == 50:  # if counter reached max value then return False
                if self._debug_mode:
                    print('self._read() not ready after 40 trials\n')
                return False

        # read first 24 bits of data
        data_in = 0  # 2's complement data from hx 711
        for _ in range(24):
            start_counter = time.perf_counter()
            # request next bit from hx 711
            self.set_pd_sck(1)
            self.set_pd_sck(0)
            end_counter = time.perf_counter()
            if end_counter - start_counter >= 0.00006:  # check if the hx 711 did not turn off...
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                if self._debug_mode:
                    print('Not enough fast while reading data')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                return False
            # Shift the bits as they come to data_in variable.
            # Left shift by one bit then bitwise OR with the new bit.
            data_in = (data_in << 1) | self.lines.get_value(self._dout)

        if self._wanted_channel == 'A' and self._gain_channel_A == 128:
            if not self._set_channel_gain(1):  # send only one bit which is 1
                return False  # return False because channel was not set properly
            else:
                self._current_channel = 'A'  # else set current channel variable
                self._gain_channel_A = 128  # and gain
        elif self._wanted_channel == 'A' and self._gain_channel_A == 64:
            if not self._set_channel_gain(3):  # send three ones
                return False  # return False because channel was not set properly
            else:
                self._current_channel = 'A'  # else set current channel variable
                self._gain_channel_A = 64
        else:
            if not self._set_channel_gain(2):  # send two ones
                return False  # return False because channel was not set properly
            else:
                self._current_channel = 'B'  # else set current channel variable

        if self._debug_mode:  # print 2's complement value
            print('Binary value as received: {}'.format(bin(data_in)))

        #check if data is valid
        if (data_in == 0x7fffff
                or  # 0x7fffff is the highest possible value from hx711
                data_in == 0x800000
           ):  # 0x800000 is the lowest possible value from hx711
            if self._debug_mode:
                print('Invalid data detected: {}\n'.format(data_in))
            return False  # rturn false because the data is invalid

        # calculate int from 2's complement
        signed_data = 0
        # 0b1000 0000 0000 0000 0000 0000 check if the sign bit is 1. Negative number.
        if (data_in & 0x800000):
            signed_data = -(
                (data_in ^ 0xffffff) + 1)  # convert from 2's complement to int
        else:  # else do not do anything the value is positive number
            signed_data = data_in

        if self._debug_mode:
            print('Converted 2\'s complement value: {}'.format(signed_data))

        return signed_data

    def get_raw_data_mean(self, readings=30):
        """
        get_raw_data_mean returns mean value of readings.

        Args:
            readings(int): Number of readings for mean.

        Returns: (bool || int) if False then reading is invalid.
            if it returns int then reading is valid
        """
        # do backup of current channel befor reading for later use
        backup_channel = self._current_channel
        backup_gain = self._gain_channel_A
        data_list = []
        # do required number of readings
        for _ in range(readings):
            data_list.append(self._read())
        data_mean = False
        if readings > 2 and self._data_filter:
            filtered_data = self._data_filter(data_list)
            if not filtered_data:
                return False
            if self._debug_mode:
                print('data_list: {}'.format(data_list))
                print('filtered_data list: {}'.format(filtered_data))
                print('data_mean:', stat.mean(filtered_data))
            data_mean = stat.mean(filtered_data)
        else:
            data_mean = stat.mean(data_list)
        self._save_last_raw_data(backup_channel, backup_gain, data_mean)
        return int(data_mean)

    def outliers_filter(self, data_list, stdev_thresh = 1.0):
        """
        It filters out outliers from the provided list of int.
        Median is used as an estimator of outliers.
        Outliers are compared to the standard deviation from the median
        Default filter is of 1.0 standard deviation from the median

        Args:
            data_list([int]): List of int. It can contain Bool False that is removed.
        
        Returns: list of filtered data. Excluding outliers.
        """
        # filter out -1 which indicates no signal
        # filter out booleans
        data = [num for num in data_list if (num != -1 and num != False and num != True)] 
        if not data:
            return []

        median = stat.median(data)
        dists_from_median = [(abs(measurement - median)) for measurement in data]
        stdev = stat.stdev(dists_from_median)
        if stdev:
            ratios_to_stdev = [(dist / stdev) for dist in dists_from_median]
        else:
            # stdev is 0. Therefore return just the median
            return [median]
        filtered_data = []
        for i in range(len(data)):
            if ratios_to_stdev[i] < stdev_thresh:
                filtered_data.append(data[i])
        return filtered_data

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