import React, { useState } from "react";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import axios from "axios";

const STREAM_URL = "http://localhost:8080/video_feed";

function LiveStream() {
  const [recording, setRecording] = useState(false);
  const [msg, setMsg] = useState("");

  const handleStart = async () => {
    try {
      await axios.post("http://localhost:8080/start_recording", {
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
      await axios.post("http://localhost:8080/stop_recording");
      setRecording(false);
      setMsg("Recording stopped.");
    } catch (e) {
      setMsg("Failed to stop recording.");
    }
  };

  return (
    <Paper elevation={4} sx={{ p: 2, margin: "2rem auto", maxWidth: 700 }}>
      <Typography variant="h6" gutterBottom>
        Live Camera Feed
      </Typography>
      <div style={{ background: "#111", textAlign: "center" }}>
        <img
          src={STREAM_URL}
          alt="Camera Stream"
          style={{ width: "100%", maxWidth: 640, borderRadius: 8 }}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <Button
          variant="contained"
          color="success"
          onClick={handleStart}
          disabled={recording}
          sx={{ mr: 2 }}
        >
          Start Recording
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleStop}
          disabled={!recording}
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