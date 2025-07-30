import React, { useState, useEffect } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import SevenSegmentDisplay from "./SevenSegmentDisplay";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

const API_URL = import.meta.env.VITE_API_URL;

function SensorControl({ onDataChanged }) {
  const [status, setStatus] = useState(null); // Calibration status
  const [loading, setLoading] = useState(false);
  const [knownWeight, setKnownWeight] = useState("");
  const [sensorRunning, setSensorRunning] = useState(false);
  const [confirmationMsg, setConfirmationMsg] = useState("");
  const [csvFilename, setCsvFilename] = useState(null);
  const [videoRuntime, setVideoRuntime] = useState(null); // New state for video runtime
  const [sensorValue, setSensorValue] = useState(null);
  const [lastCalibration, setLastCalibration] = useState(null);

  // Only check calibration ratio on mount
  useEffect(() => {
    axios
      .get(`${API_URL}/sensor/status`)
      .then((res) => {
        setLastCalibration(res.data.last_calibration);
      })
      .catch(() => {
        setLastCalibration(null);
      });
  }, []);

  // Poll sensor value only after sensor is started
  useEffect(() => {
    let intervalId;
    if (sensorRunning) {
      intervalId = setInterval(() => {
        axios
          .get(`${API_URL}/sensor/value`)
          .then((res) => {
            let val = res.data.value;
            if (typeof val === "number") {
              setSensorValue(val.toFixed(2));
            } else setSensorValue(val);
          })
          .catch(() => setSensorValue(null));
      }, 500);
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
      setSensorRunning(true); // Start polling only after button click
      setConfirmationMsg(res.data.message);
    } catch (err) {
      setConfirmationMsg(
        err?.response?.data?.message || "Error starting sensor loop"
      );
    }
    setLoading(false);
  };

  // Stop sensor data logging
  // Start both sensor and video recording in sync
  const startSensorAndVideo = async () => {
    setLoading(true);
    setConfirmationMsg("");
    setCsvFilename(null);
    try {
      const res = await axios.post(
        `${API_URL}/sync/start`,
        {},
        { headers: { "Content-Type": "application/json" } }
      );
      const sensorMsg = res.data.sensor?.message || "Sensor status unknown.";
      const videoMsg = res.data.video?.message || "Video status unknown.";
      setConfirmationMsg(`${sensorMsg} Video: ${videoMsg}`);
      setSensorRunning(true); // Start polling only after button click
      // If backend returns runtime info, set it here
      if (res.data.video?.runtime) {
        setVideoRuntime(res.data.video.runtime);
      } else {
        setVideoRuntime(null);
      }
    } catch (err) {
      console.error("Error starting sensor and video recording:", err);
      setConfirmationMsg(
        err?.response?.data?.message ||
          "Error starting sensor and video recording"
      );
      setVideoRuntime(null);
    }
    setLoading(false);
  };
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
      <Typography variant="h2" gutterBottom>
        Sensor Control
      </Typography>
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
      {/* Pass videoRuntime to VideoControl if available */}
      {videoRuntime && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Video runtime: {videoRuntime}
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
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: { xs: 2, md: 3 },
            alignItems: "center",
            mt: 2,
            mb: 2,
          }}
        >
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
                sx={{
                  px: { xs: 2, md: 3 },
                  py: { xs: 1, md: 1.5 },
                  fontSize: { xs: "1rem", md: "1.15rem" },
                  borderRadius: { xs: 2, md: 3 },
                  minWidth: 120,
                  boxShadow: 2,
                  width: "100%",
                  maxWidth: 260,
                }}
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
              sx={{
                px: { xs: 2, md: 3 },
                py: { xs: 1, md: 1.5 },
                fontSize: { xs: "1rem", md: "1.15rem" },
                borderRadius: { xs: 2, md: 3 },
                minWidth: 120,
                boxShadow: 2,
                width: "100%",
                maxWidth: 260,
              }}
            >
              Start Sensor
            </Button>
          )}
          {!sensorRunning && (
            <Button
              variant="contained"
              color="secondary"
              onClick={startSensorAndVideo}
              disabled={loading}
              sx={{
                px: { xs: 2, md: 3 },
                py: { xs: 1, md: 1.5 },
                fontSize: { xs: "1rem", md: "1.15rem" },
                borderRadius: { xs: 2, md: 3 },
                minWidth: 120,
                boxShadow: 2,
                width: "100%",
                maxWidth: 260,
              }}
            >
              Start Sensor & Video
            </Button>
          )}
          {sensorRunning && (
            <Button
              variant="contained"
              color="error"
              onClick={stopSensorLoop}
              disabled={loading}
              sx={{
                px: { xs: 2, md: 3 },
                py: { xs: 1, md: 1.5 },
                fontSize: { xs: "1rem", md: "1.15rem" },
                borderRadius: { xs: 2, md: 3 },
                minWidth: 120,
                boxShadow: 2,
                width: "100%",
                maxWidth: 260,
              }}
            >
              Stop Sensor
            </Button>
          )}
        </Box>
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
