import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

function LiveStream() {
  const [isLivestreamActive, setIsLivestreamActive] = useState(false);
  const [isRecordingActive, setIsRecordingActive] = useState(false);
  const [error, setError] = useState('');
  const intervalRef = useRef(null);

  // Fetch livestream and recording status periodically
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [livestreamRes, recordingRes] = await Promise.all([
          axios.get(`${API_URL}/livestream/status`),
          axios.get(`${API_URL}/recording/status`)
        ]);
        setIsLivestreamActive(livestreamRes.data.running);
        setIsRecordingActive(recordingRes.data.running);
      } catch (err) {
        setError('Failed to fetch stream status from backend.');
      }
    };
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 2000); // Poll every 2 seconds
    return () => clearInterval(intervalRef.current);
  }, []);

  // Start livestream handler
  const handleStartLivestream = async () => {
    setError('');
    try {
      await axios.post(`${API_URL}/livestream/start`);
      setIsLivestreamActive(true);
    } catch (err) {
      setError(
        err.response && err.response.data && err.response.data.message
          ? err.response.data.message
          : 'Failed to start livestream.'
      );
    }
  };

  // Stop livestream handler
  const handleStopLivestream = async () => {
    setError('');
    try {
      await axios.post(`${API_URL}/livestream/stop`);
      setIsLivestreamActive(false);
    } catch (err) {
      setError(
        err.response && err.response.data && err.response.data.message
          ? err.response.data.message
          : 'Failed to stop livestream.'
      );
    }
  };

  return (
    <div style={{ minWidth: 350 }}>
      <h2>Livestream</h2>
      <div>
        <button
          onClick={handleStartLivestream}
          disabled={isLivestreamActive || isRecordingActive}
        >
          Start Livestream
        </button>
        <button
          onClick={handleStopLivestream}
          disabled={!isLivestreamActive}
        >
          Stop Livestream
        </button>
      </div>
      {isRecordingActive && (
        <div style={{ color: 'red', marginTop: '1em' }}>
          Cannot start livestream while recording is active.
        </div>
      )}
      {error && <div style={{ color: 'red', marginTop: '1em' }}>{error}</div>}
      {isLivestreamActive && (
        <div style={{ marginTop: '1em' }}>
          {/* Replace with your actual <video> or <img> tag for stream video feed */}
          <img
            src={`${API_URL}/video_feed`}
            alt="Livestream"
            style={{ width: '320px', border: '2px solid #333' }}
          />
        </div>
      )}
    </div>
  );
}

export default LiveStream;