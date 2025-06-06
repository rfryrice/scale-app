import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart } from '@mui/x-charts/LineChart';


// Helper to parse ISO string with 'Z' (UTC) to Date object
function parseTimestamp(ts) {
  // Some browsers need the 'Z' at the end for UTC, but Date.parse() usually works with ISO 8601.
  // However, we explicitly parse and check for valid Date.
  const d = new Date(ts);
  return isNaN(d.getTime()) ? null : d;
}

function Dashboard() {
  const [data, setData] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8080/dashboard')
      .then(res => setData(res.data.data))
      .catch(err => console.error(err));
  }, []);

  const xData = data.map(point => parseTimestamp(point.Timestamp)).filter(Boolean);
  const yData = data
    .map(point => point.Value)
    .slice(0, xData.length); // Ensure lengths match

  return (
    <div>
      <h2>Dashboard</h2>
      <LineChart
        xAxis={[
          {
            data: xData,
            label: "Timestamp",
            scaleType: 'time', // You can use 'time' if values are valid dates
            valueFormatter: (date) => {
              if (!(date instanceof Date) || isNaN(date)) return '';
              return date.toLocaleString();
            }
          }
        ]}
        series={[
          {
            data: yData,
            label: "Value"
          }
        ]}
        width={600}
        height={350}
      />
    </div>
  );
}

export default Dashboard;