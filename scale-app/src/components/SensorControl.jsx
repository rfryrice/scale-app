import React, { useState, useEffect } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

const API_URL = import.meta.env.VITE_API_URL;

function SensorControl() {
  const [status, setStatus] = useState(false);
  const [msg, setMsg] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/sensor/status`);
      setStatus(res.data.running);
    } catch (err) {
      setMsg("Failed to get sensor status.");
    }
  };

  useEffect(() => {
    fetchStatus();
    // Optionally, poll status every few seconds:
    // const interval = setInterval(fetchStatus, 5000);
    // return () => clearInterval(interval);
  }, []);

  const handleCalibrate = async () => {
    setMsg("Calibrating...");
    try {
      const res = await axios.post(`${API_URL}/sensor/calibrate/start`);
      setMsg(res.data.message);
    } catch (err) {
      setMsg(err.response?.data?.message || "Calibration failed.");
    }
  };

  const handleStart = async () => {
    setMsg("Starting sensor loop...");
    try {
      const res = await axios.post(`${API_URL}/sensor/start`);
      setMsg(res.data.message);
      fetchStatus();
    } catch (err) {
      setMsg(err.response?.data?.message || "Failed to start sensor loop.");
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 2, maxWidth: 400, margin: "2rem auto" }}>
      <Typography variant="h6" gutterBottom>
        Sensor Control
      </Typography>
      <Typography>Status: {status ? "Running" : "Stopped"}</Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={handleCalibrate}
        sx={{ m: 1 }}
      >
        Calibrate
      </Button>
      <Button
        variant="contained"
        color="secondary"
        onClick={handleStart}
        sx={{ m: 1 }}
        disabled={status}
      >
        Start Reading Loop
      </Button>
      <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
        {msg}
      </Typography>
    </Paper>
  );
}

export default SensorControl;