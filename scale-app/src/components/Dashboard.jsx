import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart } from '@mui/x-charts/LineChart';
import { Typography } from '@mui/material';

// Display graph data

const API_URL = import.meta.env.VITE_API_URL;

// Helper to parse ISO string with 'Z' (UTC) to Date object
function parseTimestamp(ts) {
  // Some browsers need the 'Z' at the end for UTC, but Date.parse() usually works with ISO 8601.
  // However, we explicitly parse and check for valid Date.
  const d = new Date(ts);
  return isNaN(d.getTime()) ? null : d;
}

// Calculate 5-point moving average for an array of numbers
function movingAverage(values, windowSize = 5) {
  if (!Array.isArray(values)) return [];
  const avg = [];
  for (let i = 0; i < values.length; i++) {
    if (i < windowSize - 1) {
      avg.push(null); // Not enough data points
    } else {
      const window = values.slice(i - windowSize + 1, i + 1);
      avg.push(window.reduce((sum, v) => sum + v, 0) / window.length);
    }
  }
  return avg;
}

function Dashboard({ selectedFile }) {
  const [data, setData] = useState([]);
  const [filename, setFilename] = useState(selectedFile);

  useEffect(() => {
    if (!selectedFile || !selectedFile.endsWith('.csv')) return;
    setFilename(selectedFile);
    axios
      .get(`${API_URL}/dashboard?file=${encodeURIComponent(selectedFile)}`)
      .then(res => setData(res.data.data))
      .catch(err => setData([]));
  }, [selectedFile]);

  const xData = data.map(point => parseTimestamp(point.Timestamp)).filter(Boolean);
  const yData = data
    .map(point => point.Value)
    .slice(0, xData.length); // Ensure lengths match

const maData = movingAverage(yData, 5)

  return (
    <div style={{ width: "100%" }}>
      <Typography variant="h2" gutterBottom>Data Plot</Typography>
      {filename && (
        <div style={{ marginBottom: "1rem" }}>
          File: <strong>{filename}</strong>
        </div>
      )}
      {filename && filename.endsWith('.csv') ? (
        xData.length > 0 ? (
          <LineChart
            xAxis={[
              {
                data: xData,
                label: "Timestamp",
                scaleType: "time",
                valueFormatter: (date) => {
                  if (!(date instanceof Date) || isNaN(date)) return "";
                  return date.toLocaleString();
                },
              },
            ]}
            series={[
              {
                data: yData,
                label: "Value",
                color: "#4254fb"
              },
              {
                data: maData,
                label: "5-point Moving Avg",
                color: "#ff9100",
              },
            ]}
            width="100%"
            height={350}
          />
        ) : (
          <div>No data available for this file.</div>
        )
      ) : (
        <div>Select a CSV file to view the data plot.</div>
      )}
      <div style={{ marginTop: "1em", fontSize: "0.9em", color: "#888" }}>
        Purple: Original Value &nbsp;|&nbsp; Orange: 5-point Moving Average
      </div>
    </div>
  );
}

export default Dashboard;