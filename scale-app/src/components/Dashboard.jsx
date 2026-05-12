import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Typography } from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
);

const API_URL = import.meta.env.VITE_API_URL;

function parseTimestamp(ts) {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? null : d;
}

function movingAverage(values, windowSize = 5) {
  return values.map((_, i) => {
    if (i < windowSize - 1) return null;
    const slice = values.slice(i - windowSize + 1, i + 1);
    return slice.reduce((sum, v) => sum + v, 0) / slice.length;
  });
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
      .catch(() => setData([]));
  }, [selectedFile]);

  const validPoints = data
    .map(point => ({ x: parseTimestamp(point.Timestamp), y: point.Value }))
    .filter(p => p.x !== null);

  const yValues = validPoints.map(p => p.y);
  const maValues = movingAverage(yValues);

  const chartData = {
    datasets: [
      {
        label: 'Value',
        data: validPoints,
        borderColor: '#4254fb',
        backgroundColor: 'rgba(66, 84, 251, 0.1)',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.2,
      },
      {
        label: '5-point Moving Avg',
        data: validPoints.map((p, i) => ({ x: p.x, y: maValues[i] })),
        borderColor: '#ff9100',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          title: items => new Date(items[0].parsed.x).toLocaleString(),
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: { tooltipFormat: 'PPpp' },
        title: { display: true, text: 'Timestamp' },
        ticks: { maxTicksLimit: 8, maxRotation: 30 },
      },
      y: {
        title: { display: true, text: 'Value' },
      },
    },
  };

  return (
    <div style={{ width: '100%' }}>
      <Typography variant="h2" gutterBottom>Data Plot</Typography>
      {filename && (
        <div style={{ marginBottom: '1rem' }}>
          File: <strong>{filename}</strong>
        </div>
      )}
      {filename && filename.endsWith('.csv') ? (
        validPoints.length > 0 ? (
          <div style={{ position: 'relative', height: 350 }}>
            <Line data={chartData} options={options} />
          </div>
        ) : (
          <div>No data available for this file.</div>
        )
      ) : (
        <div>Select a CSV file to view the data plot.</div>
      )}
    </div>
  );
}

export default Dashboard;