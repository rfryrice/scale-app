import React, { useState } from "react";
import VideoControl from "./VideoControl";
import SensorControl from "./SensorControl";

function RecordingControl({ selectedFile, onDataChanged }) {
  const [videoStatus, setVideoStatus] = useState({ running: false, mode: null, filename: null });
  const [recordStartTime, setRecordStartTime] = useState(null);

  // Handler to start video recording (called by either child)
  const handleStartVideo = async (mode = "record", filename = null) => {
    const API_URL = import.meta.env.VITE_API_URL;
    try {
      const now = new Date();
      const formatted = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}-${String(now.getMinutes()).padStart(2, "0")}-${String(now.getSeconds()).padStart(2, "0")}`;
      const body = mode === "record"
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
      return null;
    }
  };

  // Handler to start sensor+video recording (calls /sync/start)
  const handleStartSensorAndVideo = async (filename = null) => {
    const API_URL = import.meta.env.VITE_API_URL;
    try {
      const now = new Date();
      const formatted = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}-${String(now.getMinutes()).padStart(2, "0")}-${String(now.getSeconds()).padStart(2, "0")}`;
      const body = { mode: "record", filename: filename || `output_${formatted}.mp4` };
      const res = await fetch(`${API_URL}/sync/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.video) {
        setVideoStatus(data.video);
        setRecordStartTime(Date.now());
      }
      return data;
    } catch (err) {
      return null;
    }
  };

  return (
    <>
      <SensorControl
        onDataChanged={onDataChanged}
        onStartSensorAndVideo={handleStartSensorAndVideo}
        videoStatus={videoStatus}
        recordStartTime={recordStartTime}
      />
      <VideoControl
        selectedFile={selectedFile}
        videoStatus={videoStatus}
        recordStartTime={recordStartTime}
        onStartVideo={handleStartVideo}
      />
    </>
  );
}

export default RecordingControl;