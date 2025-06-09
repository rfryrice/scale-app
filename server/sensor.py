import csv
import time
import datetime
import threading
from hx711_gpiod import HX711

DOUT_PIN = 21
PD_SCK_PIN = 20
GPIO_CHIP = '/dev/gpiochip0'
hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN, chip=GPIO_CHIP)

# Calibration state shared for frontend API
calibration_state = {
    "in_progress": False,
    "step": None,         # None, "tare", "place_weight", "enter_weight", "done"
    "message": "",
    "reading": None,
    "ratio": None,
    "known_weight": None
}

def calibrate_start():
    """Start the calibration process (tare the scale)."""
    calibration_state["in_progress"] = True
    calibration_state["step"] = "tare"
    calibration_state["message"] = "Remove all items from the scale. Taring..."
    try:
        hx.tare(times=15)
        calibration_state["reading"] = hx.read_average(times=10)
        calibration_state["message"] = "Tare complete. Place a known weight on the scale."
        calibration_state["step"] = "place_weight"
        return True
    except Exception as e:
        calibration_state["in_progress"] = False
        calibration_state["message"] = f"Tare failed: {str(e)}"
        calibration_state["step"] = "error"
        return False

def calibrate_weight_read():
    """Read value with known weight on the scale."""
    if not calibration_state["in_progress"] or calibration_state["step"] != "place_weight":
        calibration_state["message"] = "Calibration step error: not ready to read weight."
        calibration_state["step"] = "error"
        return False
    reading = hx.read_average(times=10)
    if reading is not None:
        calibration_state["reading"] = reading
        calibration_state["message"] = "Enter the known weight value (grams) in the frontend."
        calibration_state["step"] = "enter_weight"
        return True
    else:
        calibration_state["message"] = "Failed to read value with known weight."
        calibration_state["step"] = "error"
        return False

def calibrate_set_known_weight(value):
    """Set the known weight (grams) and compute calibration ratio."""
    if not calibration_state["in_progress"] or calibration_state["step"] != "enter_weight":
        calibration_state["message"] = "Calibration step error: not ready to set known weight."
        calibration_state["step"] = "error"
        return False
    try:
        known_weight = float(value)
        raw = calibration_state["reading"]
        ratio = (raw - hx.offset) / known_weight
        hx.set_scale(ratio)
        calibration_state["ratio"] = ratio
        calibration_state["known_weight"] = known_weight
        calibration_state["step"] = "done"
        calibration_state["message"] = f"Calibration complete. Ratio set to {ratio:.4f}."
        calibration_state["in_progress"] = False
        return True
    except Exception as e:
        calibration_state["message"] = f"Failed to set known weight: {str(e)}"
        calibration_state["step"] = "error"
        return False

def calibrate_status():
    """Return the current calibration state for the frontend."""
    return calibration_state.copy()

def read_mass():
    return hx.get_units(times=5)  # Average over 5 readings

def write_mass_to_csv(mass, timestamp, filename):
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, mass])

def read_sensor_loop():
    # Optionally start reading only after calibration
    while True:
        value = read_mass()
        timestamp = datetime.datetime.now().isoformat()
        filename = f"{datetime.date.today()}.csv"
        write_mass_to_csv(value, timestamp, filename)
        time.sleep(0.1)  # 10Hz

if __name__ == '__main__':
    thread = threading.Thread(target=read_sensor_loop)
    thread.daemon = True
    thread.start()