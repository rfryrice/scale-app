import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import { Typography, CardMedia, CardContent } from "@mui/material";

const API_URL = import.meta.env.VITE_API_URL;

function VideoControl({ selectedFile }) {
  // Helper: is the selected file a video?
  const isVideoFile = selectedFile && selectedFile.endsWith('.avi');
  // Compute video URL if selected, using new backend route
  const videoUrl = isVideoFile ? `${API_URL}/video-file?file=${encodeURIComponent(selectedFile)}` : null;
  const [videoStatus, setVideoStatus] = useState({
    running: false,
    mode: null,
    filename: null,
  });
  const [error, setError] = useState("");
  const [polling, setPolling] = useState(false);
  const [filename, setFilename] = useState("");
  const [recordStartTime, setRecordStartTime] = useState(null);
  const [recordRuntime, setRecordRuntime] = useState("00:00:00");
  const intervalRef = useRef(null);
  const runtimeIntervalRef = useRef(null);

  // Fetch status only if polling (i.e. after starting)
  useEffect(() => {
    if (polling) {
      const fetchStatus = async () => {
        try {
          const res = await axios.get(`${API_URL}/video/status`);
          setVideoStatus(res.data);
          if (!res.data.running) setPolling(false);
        } catch (err) {
          setError("Failed to fetch video status");
        }
      };
      fetchStatus();
      intervalRef.current = setInterval(fetchStatus, 2000);
      return () => clearInterval(intervalRef.current);
    }
  }, [polling]);

  // Track recording runtime and handle midnight rollover
  useEffect(() => {
    if (videoStatus.running && videoStatus.mode === "record") {
      if (!recordStartTime) {
        setRecordStartTime(Date.now());
      }
      runtimeIntervalRef.current = setInterval(async () => {
        if (recordStartTime) {
          const now = new Date();
          const start = new Date(recordStartTime);
          const elapsed = Date.now() - recordStartTime;
          const hours = Math.floor(elapsed / 3600000);
          const minutes = Math.floor((elapsed % 3600000) / 60000);
          const seconds = Math.floor((elapsed % 60000) / 1000);
          setRecordRuntime(
            `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
          );
          // Check if midnight has passed
          if (
            start.getDate() !== now.getDate() ||
            start.getMonth() !== now.getMonth() ||
            start.getFullYear() !== now.getFullYear()
          ) {
            // Stop current recording and start a new one
            try {
              await axios.post(`${API_URL}/video/stop`);
              // Wait a moment to ensure backend is ready
              setTimeout(async () => {
                const formatted = `${now.getFullYear()}-${String(
                  now.getMonth() + 1
                ).padStart(2, "0")}-${String(now.getDate()).padStart(
                  2,
                  "0"
                )}_${String(now.getHours()).padStart(2, "0")}-${String(
                  now.getMinutes()
                ).padStart(2, "0")}-${String(now.getSeconds()).padStart(
                  2,
                  "0"
                )}`;
                const newFilename = `output_${formatted}.avi`;
                const res = await axios.post(`${API_URL}/video/start`, {
                  mode: "record",
                  filename: newFilename,
                });
                setVideoStatus(res.data);
                setRecordStartTime(Date.now());
                setRecordRuntime("00:00:00");
                setFilename(newFilename);
              }, 1000);
            } catch (err) {
              setError(
                err.response?.data?.message ||
                  "Failed to rollover recording at midnight."
              );
              setPolling(false);
            }
          }
        }
      }, 1000);
      return () => clearInterval(runtimeIntervalRef.current);
    } else {
      setRecordStartTime(null);
      setRecordRuntime("00:00:00");
      clearInterval(runtimeIntervalRef.current);
    }
  }, [videoStatus.running, videoStatus.mode, recordStartTime]);

  // Start livestream or recording
  const handleStart = async (mode) => {
    setError("");
    try {
      const now = new Date(Date.now());
      const formatted = `${now.getFullYear()}-${String(
        now.getMonth() + 1
      ).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(
        now.getHours()
      ).padStart(2, "0")}-${String(now.getMinutes()).padStart(
        2,
        "0"
      )}-${String(now.getSeconds()).padStart(2, "0")}`;
      const body =
        mode === "record"
          ? { mode, filename: filename || `output_${formatted}.avi` }
          : { mode };
      const res = await axios.post(`${API_URL}/video/start`, body);
      setVideoStatus(res.data);
      setPolling(true);
      if (mode === "record") {
        setRecordStartTime(Date.now());
      }
    } catch (err) {
      setError(err.response?.data?.message || "Failed to start.");
    }
  };

  // Stop
  const handleStop = async () => {
    setError("");
    try {
      await axios.post(`${API_URL}/video/stop`);
      setVideoStatus({ running: false, mode: null, filename: null });
      setPolling(false);
      setRecordStartTime(null);
      setRecordRuntime("00:00:00");
    } catch (err) {
      setError(err.response?.data?.message || "Failed to stop.");
    }
  };

  return (
    <div style={{ minWidth: 350 }}>
        {isVideoFile && (
          <div style={{ marginTop: "1.5em" }}>
            <Typography variant="subtitle1" gutterBottom>
              Video Preview: {selectedFile.replace(/^videos\//, "")}
            </Typography>
          </div>
        )}
      {isVideoFile && (
        <CardMedia
          component="video"
          src={videoUrl}
          controls
          style={{ width: "100%", maxWidth: 480, border: "2px solid #333", margin: "0 auto", display: "block" }}
        />
      )}
      <CardContent>
        <Tooltip title="Control livestream and recording from here">
          <Typography variant="h2" gutterBottom>Video Control</Typography>
        </Tooltip>
        <div>
          <Button
            variant="contained"
            color="primary"
            onClick={() => handleStart("livestream")}
            disabled={videoStatus.running}
            sx={{ mr: 2 }}
          >
            Start Livestream
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={() => handleStart("record")}
            disabled={videoStatus.running}
            sx={{ mr: 2 }}
          >
            Start Recording
          </Button>
          <Button
            variant="contained"
            onClick={handleStop}
            disabled={!videoStatus.running}
          >
            Stop
          </Button>
        </div>
        {videoStatus.mode === "record" && videoStatus.filename && (
          <div style={{ color: "green", marginTop: "1em", display: "flex", alignItems: "center", gap: "1em" }}>
            Recording to file: <strong>{videoStatus.filename}</strong> 
            Runtime: <span style={{ fontWeight: "bold" }}>{recordRuntime}</span>
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
      </CardContent>
    </div>
  );
}

export default VideoControl;
