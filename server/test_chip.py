""" import gpiod

chip_path = "/dev/gpiochip0"
chip = gpiod.Chip(chip_path)

info = chip.get_info()
print(f"Chip path: {chip.path}")
print(f"Label: {getattr(info, 'label', 'N/A')}")
print(f"Name: {getattr(info, 'name', 'N/A')}")
print(f"Number of lines: {info.num_lines}")
print()
print(f"{'Offset':>6}  {'Name':<16}  {'Direction':<8}  {'Active-low':<10}  {'Used by'}")

for offset in range(info.num_lines):
    line_info = chip.get_line_info(offset)
    line_name = getattr(line_info, "name", "")
    consumer = getattr(line_info, "consumer", "")
    direction = "output" if line_info.direction == gpiod.line.Direction.OUTPUT else "input"
    active_low = str(getattr(line_info, "active_low", False))
    print(f"{offset:>6}  {line_name:<16}  {direction:<8}  {active_low:<10}  {consumer}")

chip.close() """

import time
import datetime
import csv
from hx711_gpiod import HX711
from server import set_hx, calibrate_start, calibrate_weight_read, calibrate_set_known_weight, read_mass

# --- CONFIGURE YOUR PINS/CHIP HERE ---
DOUT_PIN = 21        # BCM GPIO number for HX711 DOUT
PD_SCK_PIN = 20      # BCM GPIO number for HX711 PD_SCK
GPIO_CHIP = '/dev/gpiochip0'  # Main GPIO controller on Raspberry Pi

CSV_FILENAME = f"test_scale_{datetime.date.today()}.csv"

def write_mass_to_csv(mass, timestamp, filename):
    """Append a mass reading and timestamp to a CSV file."""
    write_header = False
    try:
        with open(filename, 'r'):
            pass
    except FileNotFoundError:
        write_header = True

    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['Timestamp', 'Value'])
        writer.writerow([timestamp, mass])

def main():
    print("Initializing HX711...")
    hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN, chip=GPIO_CHIP)
    set_hx(hx)

    print("Step 1: Tare the scale (remove all weight).")
    if calibrate_start():
        print("Tare complete.")
    else:
        print("Tare failed.")
        return

    input("Place a known weight on the scale, then press Enter...")
    print("Step 2: Reading value with known weight...")
    if calibrate_weight_read():
        print("Value read successfully.")
    else:
        print("Failed to read weight.")
        return

    known_weight = None
    while True:
        try:
            known_weight = float(input("Enter the known weight value (in grams): "))
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    print("Step 3: Setting known weight for calibration...")
    if calibrate_set_known_weight(known_weight):
        print("Calibration successful.")
    else:
        print("Calibration failed.")
        return

    print(f"\nRecording data to CSV: {CSV_FILENAME}")
    print("Press Ctrl+C to stop recording.\n")
    try:
        while True:
            value = read_mass()
            timestamp = datetime.datetime.now().isoformat()
            write_mass_to_csv(value, timestamp, CSV_FILENAME)
            print(f"{timestamp}: {value:.3f} grams")
            time.sleep(0.5)  # Adjust for desired sample rate
    except KeyboardInterrupt:
        print("\nRecording stopped.")

if __name__ == "__main__":
    main()