import React, { useState, useEffect} from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

const API_URL = import.meta.env.VITE_API_URL;

function SensorControl() {
  const [status, setStatus] = useState(null); // { step, message }
  const [loading, setLoading] = useState(false);
  const [knownWeight, setKnownWeight] = useState("");
  const [sensorRunning, setSensorRunning] = useState(false);
  const [confirmationMsg, setConfirmationMsg] = useState("");

  // Check sensor running status on mount and after calibration
  useEffect(() => {
    axios.get(`${API_URL}/sensor/status`)
      .then(res => setSensorRunning(res.data.running))
      .catch(() => setSensorRunning(false));
  }, []);

  // Start calibration
  const startCalibrate = async () => {
    setLoading(true);
    setStatus(null);
    setKnownWeight("");
    setConfirmationMsg("");
    try {
      const res = await axios.post(`${API_URL}/sensor/calibrate/start`);
      setStatus(res.data);
    } catch (err) {
      setStatus({ step: "error", message: err?.response?.data?.message || "Error starting calibration" });
    }
    setLoading(false);
  };

  // Read weight after placing known object
  const readWeight = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/sensor/calibrate/read_weight`);
      setStatus(res.data);
    } catch (err) {
      setStatus({ step: "error", message: err?.response?.data?.message || "Error reading weight" });
    }
    setLoading(false);
  };

  // Set known weight value
  const submitKnownWeight = async () => {
    if (!knownWeight || isNaN(Number(knownWeight))) {
      setStatus(s => ({ ...s, message: "Please enter a valid number for known weight." }));
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/sensor/calibrate/set_known_weight`, { weight: knownWeight });
      setStatus(res.data);
      if (res.data.step === "done") {
        setConfirmationMsg(res.data.message);
        setStatus(null); // Reset calibration UI, but keep confirmation message
        // Refresh sensor running status after calibration
        axios.get(`${API_URL}/sensor/status`)
          .then(res => setSensorRunning(res.data.running))
          .catch(() => setSensorRunning(false));
      }
    } catch (err) {
      setStatus({ step: "error", message: err?.response?.data?.message || "Error setting known weight" });
    }
    setLoading(false);
  };

  // Start sensor data logging
  const startSensorLoop = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/sensor/start`);
      setSensorRunning(true);
      setConfirmationMsg(res.data.message);
    } catch (err) {
      setConfirmationMsg(err?.response?.data?.message || "Error starting sensor loop");
    }
    setLoading(false);
  };

  // Render calibration flow UI
  return (
    <div style={{ minWidth: 300 }}>
      <h2>Sensor Control</h2>
      {confirmationMsg && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {confirmationMsg}
        </Alert>
      )}
      {status && status.message && (
        <Alert severity={status.step === "error" ? "error" : "info"}>
          {status.message}
        </Alert>
      )}
      {loading && <CircularProgress size={32} sx={{ my: 2 }} />}
      {/* Calibration Steps */}
      {!status && (
        <>
          <Button
            variant="contained"
            color="primary"
            onClick={startCalibrate}
            disabled={loading}
            sx={{ mr: 2 }}
          >
            Calibrate
          </Button>
          {!sensorRunning && (
            <Button
              variant="outlined"
              color="success"
              onClick={startSensorLoop}
              disabled={loading}
            >
              Start Sensor
            </Button>
          )}
          {sensorRunning && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Sensor is running.
            </Alert>
          )}
        </>
      )}
      {status?.step === "place_weight" && (
        <Button
          variant="contained"
          color="secondary"
          onClick={readWeight}
          disabled={loading}
        >
          Read Weight
        </Button>
      )}
      {status?.step === "enter_weight" && (
        <form
          onSubmit={e => {
            e.preventDefault();
            submitKnownWeight();
          }}
          style={{ marginTop: 12 }}
        >
          <TextField
            label="Known Weight (grams)"
            type="number"
            value={knownWeight}
            onChange={e => setKnownWeight(e.target.value)}
            size="small"
            style={{ marginRight: 8 }}
            disabled={loading}
            inputProps={{ min: "0", step: "any" }}
            required
          />
          <Button
            variant="contained"
            color="success"
            type="submit"
            disabled={loading}
          >
            Set Known Weight
          </Button>
        </form>
      )}
      {status?.step === "error" && (
        <Button
          variant="outlined"
          onClick={startCalibrate}
          style={{ marginTop: 12 }}
        >
          Restart Calibration
        </Button>
      )}
    </div>
  );
}

export default SensorControl;