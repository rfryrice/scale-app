import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  Box,
  Typography,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Tooltip,
  CardContent,
} from "@mui/material";
import SevenSegmentDisplay from "./SevenSegmentDisplay";

function RecordingControl({ selectedFile, onDataChanged }) {
  const API_URL = import.meta.env.VITE_API_URL;
  // Sensor state
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [knownWeight, setKnownWeight] = useState("");
  const [sensorRunning, setSensorRunning] = useState(false);
  const [confirmationMsg, setConfirmationMsg] = useState("");
  const [csvFilename, setCsvFilename] = useState(null);
  const [sensorValue, setSensorValue] = useState(null);
  const [lastCalibration, setLastCalibration] = useState(null);
  // Video state
  const [videoStatus, setVideoStatus] = useState({
    running: false,
    mode: null,
    filename: null,
  });
  const [recordStartTime, setRecordStartTime] = useState(null);
  const [recordRuntime, setRecordRuntime] = useState("00:00:00");
  const [error, setError] = useState("");
  const intervalRef = useRef(null);
  const runtimeIntervalRef = useRef(null);
  // Sync state
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  // Sensor polling
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

  // Calibration ratio on mount
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

  // Video runtime
  useEffect(() => {
    if (
      videoStatus?.running &&
      videoStatus?.mode === "record" &&
      recordStartTime
    ) {
      clearInterval(runtimeIntervalRef.current);
      runtimeIntervalRef.current = setInterval(() => {
        const now = Date.now();
        const start = Number(recordStartTime);
        const elapsed = now - start;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        setRecordRuntime(
          `${String(hours).padStart(2, "0")}:${String(minutes).padStart(
            2,
            "0"
          )}:${String(seconds).padStart(2, "0")}`
        );
        // Check if midnight has passed
        const startDate = new Date(start);
        const nowDate = new Date(now);
        if (
          startDate.getDate() !== nowDate.getDate() ||
          startDate.getMonth() !== nowDate.getMonth() ||
          startDate.getFullYear() !== nowDate.getFullYear()
        ) {
          setRecordRuntime("00:00:00");
        }
      }, 1000);
      return () => clearInterval(runtimeIntervalRef.current);
    } else {
      setRecordRuntime("00:00:00");
      clearInterval(runtimeIntervalRef.current);
    }
  }, [videoStatus?.running, videoStatus?.mode, recordStartTime]);

  // Sensor handlers
  const tareSensor = async () => {
    setLoading(true);
    setConfirmationMsg("");
    try {
      const res = await axios.post(`${API_URL}/sensor/tare`);
      setConfirmationMsg(res.data.message || "Sensor tared (zeroed).");
    } catch (err) {
      setConfirmationMsg(err?.response?.data?.message || "Error taring sensor");
    }
    setLoading(false);
  };

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
        setStatus(null);
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

  const stopSensorLoop = async () => {
    setLoading(true);
    setCsvFilename(null);
    try {
      const res = await axios.post(`${API_URL}/sensor/stop`);
      setSensorRunning(false);
      setConfirmationMsg(res.data.message);
      setCsvFilename(res.data.filename);
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setConfirmationMsg(
        err?.response?.data?.message || "Error stopping sensor loop"
      );
    }
    setLoading(false);
  };

  // Video handlers
  const handleStartVideo = async (mode = "record", filename = null) => {
    setError("");
    try {
      const now = new Date();
      const formatted = `${now.getFullYear()}-${String(
        now.getMonth() + 1
      ).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(
        now.getHours()
      ).padStart(2, "0")}-${String(now.getMinutes()).padStart(2, "0")}-${String(
        now.getSeconds()
      ).padStart(2, "0")}`;
      const body =
        mode === "record"
          ? { mode, filename: filename || `output_${formatted}.mp4` }
          : { mode };
      const res = await fetch(`${API_URL}/video/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setVideoStatus(data);
      if (mode === "record") setRecordStartTime(Date.now());
      return data;
    } catch (err) {
      setError("Failed to start.");
      return null;
    }
  };

  // Sync handler
  const handleSyncStart = async () => {
    setSyncLoading(true);
    setSyncMsg("");
    try {
      const res = await axios.post(`${API_URL}/sync/start`);
      setSyncMsg(res.data.message || "Sensor and video recording started.");
      setSensorRunning(true);
      setVideoStatus({
        running: true,
        mode: "record",
        filename: res.data.filename || null,
      });
      setRecordStartTime(Date.now());
    } catch (err) {
      setSyncMsg(
        err?.response?.data?.message || "Error starting sync recording"
      );
    }
    setSyncLoading(false);
  };

  const handleStopVideo = async () => {
    setError("");
    try {
      await axios.post(`${API_URL}/video/stop`);
      setVideoStatus({ running: false, mode: null, filename: null });
      setRecordRuntime("00:00:00");
    } catch (err) {
      setError("Failed to stop.");
    }
  };

  // Unified layout
  return (
    <Box
      sx={{
        background: "#181818",
        borderRadius: 2,
        boxShadow: 2,
        p: 3,
        maxWidth: "90%",
        margin: "0 auto",
        color: "#fff",
      }}
    >
      <Typography variant="h2" sx={{ fontWeight: 700, mb: 2 }}>
        Recording Control
      </Typography>
      {/* Sensor Section */}
      <Box sx={{ mb: 3 }}>
        <Typography
          variant="h3"
          sx={{ fontWeight: 600, mb: 1, color: "#90caf9" }}
        >
          Sensor
        </Typography>
        {sensorRunning && (
          <Box sx={{ mb: 2 }}>
            <SevenSegmentDisplay value={sensorValue} />
          </Box>
        )}
        {confirmationMsg && (
          <Alert severity="success" sx={{ mb: 2, width: "80%" }}>
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
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              gap: 2,
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
                    px: 2,
                    py: 1.5,
                    fontSize: "1.15rem",
                    borderRadius: 3,
                    minWidth: 120,
                    boxShadow: 2,
                    width: "100%",
                    maxWidth: 180,
                  }}
                >
                  Calibrate
                </Button>
              </span>
            </Tooltip>
            <Button
              variant="contained"
              color="info"
              onClick={tareSensor}
              disabled={loading}
              sx={{
                px: 2,
                py: 1.5,
                fontSize: "1.15rem",
                borderRadius: 3,
                minWidth: 120,
                boxShadow: 2,
                width: "100%",
                maxWidth: 180,
              }}
            >
              Tare (Zero Scale)
            </Button>
            {!sensorRunning && (
              <Button
                variant="contained"
                color="success"
                onClick={startSensorLoop}
                disabled={loading}
                sx={{
                  px: 2,
                  py: 1.5,
                  fontSize: "1.15rem",
                  borderRadius: 3,
                  minWidth: 120,
                  boxShadow: 2,
                  width: "100%",
                  maxWidth: 180,
                }}
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
                sx={{
                  px: 2,
                  py: 1.5,
                  fontSize: "1.15rem",
                  borderRadius: 3,
                  minWidth: 120,
                  boxShadow: 2,
                  width: "100%",
                  maxWidth: 180,
                }}
              >
                Stop Sensor
              </Button>
            )}
            {/* Sync Button */}
            <Box sx={{ mb: 2 }}>
              <Button
                variant="contained"
                color="warning"
                onClick={handleSyncStart}
                disabled={syncLoading || sensorRunning || videoStatus.running}
                sx={{
                  px: 2,
                  py: 1.5,
                  fontSize: "1.15rem",
                  borderRadius: 3,
                  minWidth: 120,
                  boxShadow: 2,
                  width: "100%",
                  maxWidth: 180,
                }}
              >
                Start Sensor & Video Recording
              </Button>
              {syncLoading && <CircularProgress size={24} sx={{ ml: 2 }} />}
              {syncMsg && (
                <Alert
                  severity={
                    syncMsg.toLowerCase().includes("error")
                      ? "error"
                      : "success"
                  }
                  sx={{ mt: 2, width: "80%" }}
                >
                  {syncMsg}
                </Alert>
              )}
            </Box>
          </Box>
        )}
        {status?.step === "place_weight" && (
          <Button
            variant="contained"
            color="secondary"
            onClick={readWeight}
            disabled={loading}
            sx={{ mt: 2 }}
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
      </Box>
      {/* Video Section */}
      <Box sx={{ mt: 4 }}>
        <Typography
          variant="h3"
          sx={{ fontWeight: 600, mb: 1, color: "#f48fb1" }}
        >
          Video
        </Typography>
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            gap: 2,
            alignItems: "center",
            mb: 2,
          }}
        >
          <Button
            variant="contained"
            color="primary"
            onClick={() => handleStartVideo("livestream")}
            disabled={videoStatus.running}
            sx={{
              px: 2,
              py: 1.5,
              fontSize: "1.15rem",
              borderRadius: 3,
              minWidth: 120,
              boxShadow: 2,
              width: "100%",
              maxWidth: 180,
            }}
          >
            Start Livestream
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={() => handleStartVideo("record")}
            disabled={videoStatus.running}
            sx={{
              px: 2,
              py: 1.5,
              fontSize: "1.15rem",
              borderRadius: 3,
              minWidth: 120,
              boxShadow: 2,
              width: "100%",
              maxWidth: 180,
            }}
          >
            Start Recording
          </Button>
          <Button
            variant="contained"
            onClick={handleStopVideo}
            disabled={!videoStatus.running}
            sx={{
              px: 2,
              py: 1.5,
              fontSize: "1.15rem",
              borderRadius: 3,
              minWidth: 120,
              boxShadow: 2,
              width: "100%",
              maxWidth: 180,
            }}
          >
            Stop
          </Button>
        </Box>
        {videoStatus.mode === "record" && videoStatus.filename && (
          <div style={{ color: "green", marginTop: "1em" }}>
            <Typography variant="body1">
              Recording to file: <strong>{videoStatus.filename}</strong>
            </Typography>
            <Typography variant="body1">
              Runtime:{" "}
              <span style={{ fontWeight: "bold" }}>{recordRuntime}</span>
            </Typography>
          </div>
        )}
        {error && <div style={{ color: "red", marginTop: "1em" }}>{error}</div>}
        {videoStatus.running && videoStatus.mode === "livestream" && (
          <div style={{ marginTop: "1em" }}>
            <img
              src={`${API_URL}/video_feed?${Date.now()}`}
              alt="Video Stream"
              style={{ width: "75%", border: "2px solid #333" }}
            />
          </div>
        )}
      </Box>
    </Box>
  );
}

export default RecordingControl;
