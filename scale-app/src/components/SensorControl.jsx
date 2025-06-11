import React, { useState } from "react";
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

  // Start calibration
  const startCalibrate = async () => {
    setLoading(true);
    setStatus(null);
    setKnownWeight("");
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
    } catch (err) {
      setStatus({ step: "error", message: err?.response?.data?.message || "Error setting known weight" });
    }
    setLoading(false);
  };

  // Render calibration flow UI
  return (
    <div style={{ minWidth: 300 }}>
      <h2>Sensor Control</h2>
      {status && status.message && (
        <Alert severity={status.step === "error" ? "error" : (status.step === "done" ? "success" : "info")}>
          {status.message}
        </Alert>
      )}
      {loading && <CircularProgress size={32} />}
      {/* Calibration Steps */}
      {!status && (
        <Button variant="contained" color="primary" onClick={startCalibrate} disabled={loading}>
          Calibrate
        </Button>
      )}
      {status?.step === "place_weight" && (
        <Button variant="contained" color="secondary" onClick={readWeight} disabled={loading}>
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
          <Button variant="contained" color="success" type="submit" disabled={loading}>
            Set Known Weight
          </Button>
        </form>
      )}
      {(status?.step === "done" || status?.step === "error") && (
        <Button variant="outlined" onClick={startCalibrate} style={{ marginTop: 12 }}>
          Restart Calibration
        </Button>
      )}
    </div>
  );
}

export default SensorControl;