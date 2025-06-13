import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

function RecordingControl() {
  const [isRecordingActive, setIsRecordingActive] = useState(false);
  const [isLivestreamActive, setIsLivestreamActive] = useState(false);
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const intervalRef = useRef(null);

  // Poll backend for status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [recordingRes, livestreamRes] = await Promise.all([
          axios.get(`${API_URL}/recording/status`),
          axios.get(`${API_URL}/livestream/status`)
        ]);
        setIsRecordingActive(recordingRes.data.running);
        setIsLivestreamActive(livestreamRes.data.running);
        setFilename(recordingRes.data.filename || '');
      } catch (err) {
        setError('Failed to fetch status from backend.');
      }
    };
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 2000);
    return () => clearInterval(intervalRef.current);
  }, []);

  // Start recording
  const handleStartRecording = async () => {
    setError('');
    try {
      const res = await axios.post(`${API_URL}/start_recording`, {
        filename: filename || `output_${Date.now()}.avi`
      });
      setIsRecordingActive(true);
      setFilename(res.data.filename);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        'Failed to start recording.'
      );
    }
  };

  // Stop recording
  const handleStopRecording = async () => {
    setError('');
    try {
      const res = await axios.post(`${API_URL}/stop_recording`);
      setIsRecordingActive(false);
      setFilename('');
    } catch (err) {
      setError(
        err.response?.data?.message ||
        'Failed to stop recording.'
      );
    }
  };

  return (
    <div style={{ minWidth: 350 }}>
      <h2>Recording Control</h2>
      <div>
        <button
          onClick={handleStartRecording}
          disabled={isRecordingActive || isLivestreamActive}
        >
          Start Recording
        </button>
        <button
          onClick={handleStopRecording}
          disabled={!isRecordingActive}
        >
          Stop Recording
        </button>
      </div>
      {isLivestreamActive && (
        <div style={{ color: 'red', marginTop: '1em' }}>
          Cannot start recording while livestream is active.
        </div>
      )}
      {error && <div style={{ color: 'red', marginTop: '1em' }}>{error}</div>}
      {isRecordingActive && filename && (
        <div style={{ color: 'green', marginTop: '1em' }}>
          Recording to file: <strong>{filename}</strong>
        </div>
      )}
    </div>
  );
}

export default RecordingControl;