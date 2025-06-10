import React, { useState, useRef } from "react";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL;

const STREAM_URL = `${API_URL}/video_feed`;

function LiveStream() {
  const [recording, setRecording] = useState(false);
  const [msg, setMsg] = useState("");
  const [streamError, setStreamError] = useState(false);
  const imgRef = useRef();

  const handleStart = async () => {
    try {
      await axios.post(`${API_URL}/start_recording`, {
        filename: "recorded_" + Date.now() + ".avi"
      });
      setRecording(true);
      setMsg("Recording started.");
    } catch (e) {
      setMsg("Failed to start recording.");
    }
  };

  const handleStop = async () => {
    try {
      await axios.post(`${API_URL}/stop_recording`);
      setRecording(false);
      setMsg("Recording stopped.");
    } catch (e) {
      setMsg("Failed to stop recording.");
    }
  };

  // Error handling for stream
  const handleImageError = () => {
    setStreamError(true);
    setMsg("Camera is currently in use by another user or tab.");
  };

  // Reset error if stream is retried
  const handleImageLoad = () => {
    setStreamError(false);
    setMsg("");
  };

  return (
    <Paper elevation={4} sx={{ p: 2, margin: "2rem auto", maxWidth: 700 }}>
      <Typography variant="h6" gutterBottom>
        Live Camera Feed
      </Typography>
      <div style={{ background: "#111", textAlign: "center" }}>
        {!streamError ? (
          <img
            ref={imgRef}
            src={STREAM_URL}
            alt="Camera Stream"
            style={{ width: "100%", maxWidth: 640, borderRadius: 8 }}
            onError={handleImageError}
            onLoad={handleImageLoad}
          />
        ) : (
          <Typography color="error" style={{padding: '2em', fontWeight: 'bold'}}>
            Camera is currently in use by another user or tab.<br/>
            Please close other streams and refresh this page.
          </Typography>
        )}
      </div>
      <div style={{ marginTop: 16 }}>
        <Button
          variant="contained"
          color="success"
          onClick={handleStart}
          disabled={recording || streamError}
          sx={{ mr: 2 }}
        >
          Start Recording
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleStop}
          disabled={!recording || streamError}
        >
          Stop Recording
        </Button>
      </div>
      <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
        {msg}
      </Typography>
    </Paper>
  );
}

export default LiveStream;