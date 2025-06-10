import csv
import time
import datetime

# This is a debugging version of sensor.py, with extra print statements to help diagnose calibration/reporting issues.
DOUT_PIN = 21
PD_SCK_PIN = 20
GPIO_CHIP = 'gpiochip0'
hx = None

calibration_state = {
    "in_progress": False,
    "step": None,
    "message": "",
    "reading": None,
    "ratio": None,
    "known_weight": None,
    "debug": {}
}

def set_hx(new_hx):
    global hx
    hx = new_hx

def calibrate_start():
    calibration_state["in_progress"] = True
    calibration_state["step"] = "tare"
    calibration_state["message"] = "Remove all items from the scale. Taring..."
    try:
        hx.tare()
        tare_raw = hx.get_raw_data_mean()
        calibration_state["reading"] = tare_raw
        calibration_state["debug"] = {
            "tare_raw": tare_raw,
            "offset": getattr(hx, 'offset', None),
            "scale": getattr(hx, 'scale', None),
        }
        print(f"[DEBUG] Tare complete. tare_raw={tare_raw}, offset={hx.offset}, scale={hx.scale}")
        calibration_state["message"] = "Tare complete. Place a known weight on the scale."
        calibration_state["step"] = "place_weight"
        return True
    except Exception as e:
        calibration_state["in_progress"] = False
        calibration_state["message"] = f"Tare failed: {str(e)}"
        calibration_state["step"] = "error"
        print(f"[DEBUG] Tare failed: {e}")
        return False

def calibrate_weight_read():
    if not calibration_state["in_progress"] or calibration_state["step"] != "place_weight":
        calibration_state["message"] = "Calibration step error: not ready to read weight."
        calibration_state["step"] = "error"
        print("[DEBUG] Calibration step error: not ready to read weight.")
        return False
    raw_with_weight = hx.get_raw_data_mean()
    if raw_with_weight is not None:
        calibration_state["reading"] = raw_with_weight
        prev_debug = calibration_state.get("debug", {})
        prev_debug.update({
            "raw_with_weight": raw_with_weight,
        })
        calibration_state["debug"] = prev_debug
        print(f"[DEBUG] Weight read. raw_with_weight={raw_with_weight}")
        calibration_state["message"] = "Enter the known weight value (grams) in the frontend."
        calibration_state["step"] = "enter_weight"
        return True
    else:
        calibration_state["message"] = "Failed to read value with known weight."
        calibration_state["step"] = "error"
        print("[DEBUG] Failed to read value with known weight.")
        return False

def calibrate_set_known_weight(value):
    if not calibration_state["in_progress"] or calibration_state["step"] != "enter_weight":
        calibration_state["message"] = "Calibration step error: not ready to set known weight."
        calibration_state["step"] = "error"
        print("[DEBUG] Calibration step error: not ready to set known weight.")
        return False
    try:
        known_weight = float(value)
        tare_raw = calibration_state["debug"].get("tare_raw", None)
        raw_with_weight = calibration_state["debug"].get("raw_with_weight", None)
        offset = getattr(hx, 'offset', None)
        raw = calibration_state["reading"]
        ratio = (raw - offset) / known_weight

        hx.set_scale(ratio)
        calibration_state["ratio"] = ratio
        calibration_state["known_weight"] = known_weight
        calibration_state["debug"].update({
            "tare_raw": tare_raw,
            "raw_with_weight": raw_with_weight,
            "offset": offset,
            "scale": hx.scale,
            "ratio": ratio,
            "known_weight": known_weight,
        })
        print(f"[DEBUG] Calibration complete. tare_raw={tare_raw}, raw_with_weight={raw_with_weight}, offset={offset}, ratio={ratio}, scale={hx.scale}")
        calibration_state["step"] = "done"
        calibration_state["message"] = f"Calibration complete. Ratio set to {ratio:.4f}."
        calibration_state["in_progress"] = False
        return True
    except Exception as e:
        calibration_state["message"] = f"Failed to set known weight: {str(e)}"
        calibration_state["step"] = "error"
        print(f"[DEBUG] Failed to set known weight: {e}")
        return False

def calibrate_status():
    # Return all debug info as well for diagnosis
    return calibration_state.copy()

def read_mass():
    weight = hx.get_weight_mean(readings=5)
    try:
        raw = hx.get_raw_data_mean(readings=5)
        offset = getattr(hx, 'offset', None)
        scale = getattr(hx, 'scale', None)
        print(f"[DEBUG] read_mass: raw={raw}, offset={offset}, scale={scale}, weight={weight}")
    except Exception as e:
        print(f"[DEBUG] Exception in read_mass: {e}")
    return weight

def write_mass_to_csv(mass, timestamp, filename):
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, mass])

def read_sensor_loop():
    while True:
        value = read_mass()
        timestamp = datetime.datetime.now().isoformat()
        filename = f"{datetime.date.today()}.csv"
        write_mass_to_csv(value, timestamp, filename)
        time.sleep(0.1)