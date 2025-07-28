import React, { useEffect, useRef, useState } from "react";
import { Card, CardContent, Typography, Box } from "@mui/material";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend
);

const API_URL = import.meta.env.VITE_API_URL;

export default function SystemMonitor() {
  const [data, setData] = useState({
    cpu_percent: 0,
    ram_percent: 0,
    ram_used: 0,
    ram_total: 0,
    timestamp: Date.now(),
  });
  const [history, setHistory] = useState([]);
  const intervalRef = useRef(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/system-status`);
        const json = await res.json();
        setData(json);
        setHistory((prev) => [
          ...prev.slice(-59),
          { time: new Date(json.timestamp * 1000), cpu: json.cpu_percent, ram: json.ram_percent }
        ]);
      } catch (e) {}
    };
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 1000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const cpuChartData = {
    labels: history.map((h) => h.time.toLocaleTimeString()),
    datasets: [
      {
        label: "CPU %",
        data: history.map((h) => h.cpu),
        borderColor: "#1976d2",
        backgroundColor: "rgba(25, 118, 210, 0.15)",
        tension: 0.3,
        pointRadius: 0,
        fill: true,
      },
    ],
  };
  const ramChartData = {
    labels: history.map((h) => h.time.toLocaleTimeString()),
    datasets: [
      {
        label: "RAM %",
        data: history.map((h) => h.ram),
        borderColor: "#d32f2f",
        backgroundColor: "rgba(211, 47, 47, 0.15)",
        tension: 0.3,
        pointRadius: 0,
        fill: true,
      },
    ],
  };
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: false },
    },
    elements: { line: { borderWidth: 2 } },
    scales: {
      y: { min: 0, max: 100, display: false },
      x: { display: false },
    },
    animation: false,
    maintainAspectRatio: false,
  };

  return (
    <Box sx={{
      background: '#181818',
      borderRadius: 2,
      boxShadow: 2,
      p: 2,
      minWidth: 340,
      maxWidth: 520,
      color: '#fff',
    }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1, color: '#fff' }}>System Monitor</Typography>
      <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ color: '#90caf9', fontWeight: 600 }}>CPU</Typography>
          <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 700, mb: 0 }}>{data.cpu_percent}%</Typography>
          <Box sx={{ height: 48, mt: 0.5 }}>
            <Line data={cpuChartData} options={chartOptions} height={48} />
          </Box>
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ color: '#f48fb1', fontWeight: 600 }}>RAM</Typography>
          <Typography variant="h4" sx={{ color: '#d32f2f', fontWeight: 700, mb: 0 }}>{data.ram_percent}%</Typography>
          <Typography variant="body2" sx={{ color: '#bbb', fontSize: 13, mb: 0.5 }}>
            {Math.round(data.ram_used / 1024 / 1024)} MB / {Math.round(data.ram_total / 1024 / 1024)} MB
          </Typography>
          <Box sx={{ height: 48, mt: 0.5 }}>
            <Line data={ramChartData} options={chartOptions} height={48} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
