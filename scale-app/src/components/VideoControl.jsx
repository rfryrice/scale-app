import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import Tooltip from "@mui/material/Tooltip";
import { Typography, CardMedia, CardContent } from "@mui/material";

const API_URL = import.meta.env.VITE_API_URL;

function VideoControl({ selectedFile, videoStatus, recordStartTime, onStartVideo }) {
  const [error, setError] = useState("");
  const [polling, setPolling] = useState(false);
  const [filename, setFilename] = useState("");
  const [recordRuntime, setRecordRuntime] = useState("00:00:00");
  const intervalRef = useRef(null);
  const runtimeIntervalRef = useRef(null);
  const [showVideo, setShowVideo] = useState(false);
  // Helper: is the selected file a video?
  const isVideoFile = selectedFile && selectedFile.endsWith('.mp4');
  // Direct video file URL
  const videoUrl = isVideoFile ? `${API_URL}/video-file?file=${encodeURIComponent(selectedFile)}` : null;

  // Fetch status only if polling (i.e. after starting)
  useEffect(() => {
    if (polling) {
      const fetchStatus = async () => {
        try {
          const res = await axios.get(`${API_URL}/video/status`);
          // Parent should update videoStatus, so just check running
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

  // Track recording runtime and handle midnight rollover, interrupt on error
  useEffect(() => {
    if (videoStatus?.running && videoStatus?.mode === "record" && recordStartTime) {
      runtimeIntervalRef.current = setInterval(() => {
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
          setRecordRuntime("00:00:00");
        }
      }, 1000);
      return () => clearInterval(runtimeIntervalRef.current);
    } else {
      setRecordRuntime("00:00:00");
      clearInterval(runtimeIntervalRef.current);
    }
  }, [videoStatus?.running, videoStatus?.mode, recordStartTime]);

  // Start livestream or recording using parent's handler
  const handleStart = async (mode) => {
    setError("");
    try {
      await onStartVideo && onStartVideo(mode, filename);
      setPolling(true);
    } catch (err) {
      setError("Failed to start.");
    }
  };

  // Stop
  const handleStop = async () => {
    setError("");
    try {
      await axios.post(`${API_URL}/video/stop`);
      setPolling(false);
      setRecordRuntime("00:00:00");
    } catch (err) {
      setError("Failed to stop.");
    }
  };

  return (
    <div style={{ minWidth: 350, position: 'relative' }}>
      {/* Toggle icon button for video drawer - absolute top left */}
      {isVideoFile && (
        <IconButton
          onClick={() => setShowVideo((v) => !v)}
          color={showVideo ? "secondary" : "primary"}
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 10,
            background: '#fff',
            boxShadow: 1,
            '&:hover': { background: '#f0f0f0' },
          }}
        >
          {showVideo ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      )}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "flex-start",
          minHeight: 300,
          position: "relative",
        }}
      >
        {/* Video drawer on the left */}
        {isVideoFile && showVideo && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: 24, marginBottom: 16 }}>
            <video
              src={videoUrl}
              controls
              style={{ width: 320, height: 240, border: "2px solid #333", borderRadius: 8, background: "#000", transition: "width 0.4s, height 0.4s" }}
              poster=""
            />
            <Typography variant="subtitle1" gutterBottom sx={{ color: '#333', mt: 1 }}>
              Video Preview: {selectedFile.replace(/^videos\//, "")}
            </Typography>
          </div>
        )}
        {/* CardContent to the right of video drawer */}
        <CardContent style={{ flex: 1, minWidth: 0 }}>
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
            <div style={{ color: "green", marginTop: "1em" }}>
              <Typography variant="body1">
                Recording to file: <strong>{videoStatus.filename}</strong>
              </Typography>
              <Typography variant="body1">
                Runtime: <span style={{ fontWeight: "bold" }}>{recordRuntime}</span>
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
        </CardContent>
      </div>
    </div>
  );
}

export default VideoControl;
