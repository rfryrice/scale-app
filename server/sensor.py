import csv
import time
import datetime
import threading
import RPi.GPIO as GPIO
from hx711 import HX711


GPIO.setmode(GPIO.BCM)
hx = HX711(dout_pin=21, pd_sck_pin=20)

def calibrate(hx):
    err = hx.zero()
    # check if successful
    if err:
        raise ValueError('Tare is unsuccessful.')
    
    reading = hx.get_raw_data_mean()
    if reading:  # always check if you get correct value or only False
        # now the value is close to 0
        print('Data subtracted by offset but still not converted to units:',
              reading)
    else:
        print('invalid data', reading)

    # In order to calculate the conversion ratio to some units, in my case I want grams,
    # you must have known weight.
    input('Put known weight on the scale and then press Enter')
    reading = hx.get_data_mean()
    if reading:
        print('Mean value from HX711 subtracted by offset:', reading)
        known_weight_grams = input(
            'Write how many grams it was and press Enter: ')
        try:
            value = float(known_weight_grams)
            print(value, 'grams')
        except ValueError:
            print('Expected integer or float and I have got:',
                  known_weight_grams)

        # set scale ratio for particular channel and gain which is
        # used to calculate the conversion to units. Required argument is only
        # scale ratio. Without arguments 'channel' and 'gain_A' it sets
        # the ratio for current channel and gain.
        ratio = reading / value  # calculate the ratio for channel A and gain 128
        hx.set_scale_ratio(ratio)  # set ratio for current channel
        print('Ratio is set.')
    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)

    return hx

def read_mass():
    return hx.get_weight_mean(5)  # Average over 5 readings

def write_mass_to_csv(mass, timestamp, filename):
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, mass])

def read_sensor_loop():
    global hx
    hx = calibrate(hx)
    while True:
        value = read_mass()
        timestamp = datetime.datetime.now().isoformat()
        
        # Save to CSV if needed
        filename = f"{datetime.date.today()}.csv"
        write_mass_to_csv(value, timestamp, filename)
        
        time.sleep(0.1)  # 10Hz


if __name__ == '__main__':
    thread = threading.Thread(target=read_sensor_loop)
    thread.daemon = True
    thread.start()