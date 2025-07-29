import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import Tooltip from "@mui/material/Tooltip";
import { Typography, CardMedia, CardContent } from "@mui/material";

const API_URL = import.meta.env.VITE_API_URL;

function VideoControl({ selectedFile }) {
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
  const [showVideo, setShowVideo] = useState(false);
  // Helper: is the selected file a video?
  const isVideoFile = selectedFile && selectedFile.endsWith('.mp4');
  // DASH manifest URL for selected video
  const dashManifestUrl = isVideoFile ? `${API_URL}/video/dash/manifest?file=${encodeURIComponent(selectedFile.replace(/^videos\//, ""))}` : null;
  // Fallback direct video URL
  const videoUrl = isVideoFile ? `${API_URL}/video-file?file=${encodeURIComponent(selectedFile)}` : null;
  // Ref for dash.js video element
  const dashVideoRef = useRef(null);
  // Dynamically load dash.js and attach to video element if DASH manifest is available
  useEffect(() => {
    if (!isVideoFile || !showVideo) return;
    if (!dashManifestUrl) return;
    let player = null;
    let script = null;
    // Only attach dash.js if the drawer is open
    if (showVideo && dashVideoRef.current) {
      // Dynamically load dash.js if not already loaded
      if (!window.dashjs) {
        script = document.createElement('script');
        script.src = 'https://cdn.dashjs.org/latest/dash.all.min.js';
        script.async = true;
        script.onload = () => {
          if (window.dashjs && dashVideoRef.current) {
            player = window.dashjs.MediaPlayer().create();
            player.initialize(dashVideoRef.current, dashManifestUrl, false);
          }
        };
        document.body.appendChild(script);
      } else {
        player = window.dashjs.MediaPlayer().create();
        player.initialize(dashVideoRef.current, dashManifestUrl, false);
      }
    }
    return () => {
      if (player) {
        player.reset();
      }
      if (script) {
        document.body.removeChild(script);
      }
    };
    // Only rerun if drawer, file, or manifest changes
  }, [showVideo, dashManifestUrl, isVideoFile, selectedFile]);

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

  // Track recording runtime and handle midnight rollover, interrupt on error
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
          // Check for backend error (VideoStreamer)
          try {
            const statusRes = await axios.get(`${API_URL}/video/status`);
            if (statusRes.data.error) {
              setError(statusRes.data.error);
              setPolling(false);
              clearInterval(runtimeIntervalRef.current);
              return;
            }
          } catch (err) {
            setError(err.response?.data?.message || "VideoStreamer error.");
            setPolling(false);
            clearInterval(runtimeIntervalRef.current);
            return;
          }
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
                const newFilename = `output_${formatted}.mp4`;
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
              clearInterval(runtimeIntervalRef.current);
              return;
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
          ? { mode, filename: filename || `output_${formatted}.mp4` }
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
        {/* Animated CardMedia drawer */}
        {/* Video preview moved into CardContent below */}
        <CardContent style={{ flex: 1, minWidth: 0 }}>
          {/* DASH video player and label inside CardContent */}
          {isVideoFile && showVideo && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 16 }}>
              <video
                ref={dashVideoRef}
                controls
                style={{ width: 320, height: 240, border: "2px solid #333", borderRadius: 8, background: "#000", transition: "width 0.4s, height 0.4s" }}
                poster=""
              />
              <Typography variant="subtitle1" gutterBottom sx={{ color: '#333', mt: 1 }}>
                Video Preview (DASH): {selectedFile.replace(/^videos\//, "")}
              </Typography>
            </div>
          )}
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
    </div>
  );
}

export default VideoControl;
