import React, { useState, useEffect } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import SevenSegmentDisplay from "./SevenSegmentDisplay";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

const API_URL = import.meta.env.VITE_API_URL;

function SensorControl({ onDataChanged }) {
  const [status, setStatus] = useState(null); // Calibration status
  const [loading, setLoading] = useState(false);
  const [knownWeight, setKnownWeight] = useState("");
  const [sensorRunning, setSensorRunning] = useState(false);
  const [confirmationMsg, setConfirmationMsg] = useState("");
  const [csvFilename, setCsvFilename] = useState(null);
  const [sensorValue, setSensorValue] = useState(null);
  const [lastCalibration, setLastCalibration] = useState(null);

  // Check sensor running status on mount and after calibration
  useEffect(() => {
    axios
      .get(`${API_URL}/sensor/status`)
      .then((res) => {
        setSensorRunning(res.data.running);
        setLastCalibration(res.data.last_calibration);
      })
      .catch(() => {
        setSensorRunning(false);
        setLastCalibration(null);
      });
  }, []);

  // Poll sensor value when running
  useEffect(() => {
    let intervalId;
    if (sensorRunning) {
      // Fetch sensor value every 500ms
      intervalId = setInterval(() => {
        axios
          .get(`${API_URL}/sensor/value`)
          .then((res) => {
            let val = res.data.value;
            if (typeof val === "number") {
              setSensorValue(val.toFixed(2)); // Format to 2 decimal places
            } else setSensorValue(val); // Handle unexpected response
          })
          .catch(() => setSensorValue(null));
      }, 500);
    } else {
      setSensorValue(null);
    }
    return () => clearInterval(intervalId);
  }, [sensorRunning]);

  // Start calibration flow
  const startCalibrate = async () => {
    setLoading(true);
    setStatus(null);
    setKnownWeight("");
    setConfirmationMsg("");
    setCsvFilename(null);
    try {
      const res = await axios.post(`${API_URL}/sensor/calibrate/start`);
      setStatus(res.data);
    } catch (err) {
      setStatus({
        step: "error",
        message: err?.response?.data?.message || "Error starting calibration",
      });
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
      setStatus({
        step: "error",
        message: err?.response?.data?.message || "Error reading weight",
      });
    }
    setLoading(false);
  };

  // Set known weight value
  const submitKnownWeight = async () => {
    if (!knownWeight || isNaN(Number(knownWeight))) {
      setStatus((s) => ({
        ...s,
        message: "Please enter a valid number for known weight.",
      }));
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(
        `${API_URL}/sensor/calibrate/set_known_weight`,
        { weight: knownWeight }
      );
      setStatus(res.data);
      if (res.data.step === "done") {
        setConfirmationMsg(res.data.message);
        setStatus(null); // Reset calibration UI, but keep confirmation message
        // Refresh sensor running status after calibration
        axios
          .get(`${API_URL}/sensor/status`)
          .then((res) => setSensorRunning(res.data.running))
          .catch(() => setSensorRunning(false));
      }
    } catch (err) {
      setStatus({
        step: "error",
        message: err?.response?.data?.message || "Error setting known weight",
      });
    }
    setLoading(false);
  };

  // Start sensor data logging
  const startSensorLoop = async () => {
    setLoading(true);
    setCsvFilename(null);
    try {
      const res = await axios.post(`${API_URL}/sensor/start`);
      setSensorRunning(true);
      setConfirmationMsg(res.data.message);
    } catch (err) {
      setConfirmationMsg(
        err?.response?.data?.message || "Error starting sensor loop"
      );
    }
    setLoading(false);
  };

  // Stop sensor data logging
  const stopSensorLoop = async () => {
    setLoading(true);
    setCsvFilename(null);
    try {
      const res = await axios.post(`${API_URL}/sensor/stop`);
      setSensorRunning(false);
      setConfirmationMsg(res.data.message);
      setCsvFilename(res.data.filename);
      if (onDataChanged) onDataChanged(); // Notify parent to refresh file list
    } catch (err) {
      setConfirmationMsg(
        err?.response?.data?.message || "Error stopping sensor loop"
      );
    }
    setLoading(false);
  };

  // Render calibration flow UI
return (
    <div>
      <Typography variant="h2" gutterBottom>Sensor Control</Typography>
      {sensorRunning && (
        <div style={{ marginBottom: 16 }}>
          <SevenSegmentDisplay value={sensorValue} />
        </div>
      )}
      {confirmationMsg && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {confirmationMsg}
          {csvFilename && (
            <div>
              Data saved to: <strong>{csvFilename}</strong>
            </div>
          )}
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
          <Tooltip
            title={
              lastCalibration !== null
                ? `Last calibration ratio: ${lastCalibration}`
                : "No calibration data"
            }
            arrow
            placement="top"
          >
            <span>
              <Button
                variant="contained"
                color="primary"
                onClick={startCalibrate}
                disabled={loading || sensorRunning}
                sx={{ mr: 2 }}
              >
                Calibrate
              </Button>
            </span>
          </Tooltip>
          {!sensorRunning && (
            <Button
              variant="contained"
              color="success"
              onClick={startSensorLoop}
              disabled={loading}
            >
              Start Sensor
            </Button>
          )}
          {sensorRunning && (
            <Button
              variant="contained"
              color="error"
              onClick={stopSensorLoop}
              disabled={loading}
              sx={{ ml: 2 }}
            >
              Stop Sensor
            </Button>
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
          Continue
        </Button>
      )}
      {status?.step === "enter_weight" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitKnownWeight();
          }}
          style={{ marginTop: 12 }}
        >
          <TextField
            label="Known Weight (grams)"
            type="number"
            value={knownWeight}
            onChange={(e) => setKnownWeight(e.target.value)}
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
