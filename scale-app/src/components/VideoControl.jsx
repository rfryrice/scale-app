import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import Button from "@mui/material/Button";

const API_URL = import.meta.env.VITE_API_URL;

function VideoControl() {
  const [videoStatus, setVideoStatus] = useState({ running: false, mode: null, filename: null });
  const [error, setError] = useState('');
  const [polling, setPolling] = useState(false);
  const [filename, setFilename] = useState('');
  const intervalRef = useRef(null);

  // Fetch status only if polling (i.e. after starting)
  useEffect(() => {
    if (polling) {
      const fetchStatus = async () => {
        try {
          const res = await axios.get(`${API_URL}/video/status`);
          setVideoStatus(res.data);
          if (!res.data.running) setPolling(false);
        } catch (err) {
          setError('Failed to fetch video status');
        }
      };
      fetchStatus();
      intervalRef.current = setInterval(fetchStatus, 2000);
      return () => clearInterval(intervalRef.current);
    }
  }, [polling]);

  // Start livestream or recording
  const handleStart = async (mode) => {
    setError('');
    try {
      const body = mode === "record" ? { mode, filename: filename || `output_${Date.now()}.avi` } : { mode };
      const res = await axios.post(`${API_URL}/video/start`, body);
      setVideoStatus(res.data);
      setPolling(true);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to start.');
    }
  };

  // Stop
  const handleStop = async () => {
    setError('');
    try {
      await axios.post(`${API_URL}/video/stop`);
      setVideoStatus({ running: false, mode: null, filename: null });
      setPolling(false);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to stop.');
    }
  };

  return (
    <div style={{ minWidth: 350 }}>
      <h2>Video Control</h2>
      <div>
        <Button
          variant = "contained"
          color = "primary"
          onClick={() => handleStart("livestream")}
          disabled={videoStatus.running}
        >
          Start Livestream
        </Button>
        <Button
          variant = "contained"
          color = "secondary"
          onClick={() => handleStart("record")}
          disabled={videoStatus.running}
        >
          Start Recording
        </Button>
        <Button
          onClick={handleStop}
          disabled={!videoStatus.running}
        >
          Stop
        </Button>
      </div>
      {videoStatus.mode === 'record' && videoStatus.filename && (
        <div style={{ color: 'green', marginTop: '1em' }}>
          Recording to file: <strong>{videoStatus.filename}</strong>
        </div>
      )}
      {error && <div style={{ color: 'red', marginTop: '1em' }}>{error}</div>}
      {videoStatus.running && videoStatus.mode === 'livestream' && (
        <div style={{ marginTop: '1em' }}>
          <img
            src={`${API_URL}/video_feed?${Date.now()}`}
            alt="Video Stream"
            style={{ width: '320px', border: '2px solid #333' }}
          />
        </div>
      )}
    </div>
  );
}

export default VideoControl;