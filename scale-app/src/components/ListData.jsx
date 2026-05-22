import React, { useEffect, useState } from "react";
import {
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Button,
} from "@mui/material";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL;

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export default function ListData({ onFileSelect, selectedFile }) {
  const [tab, setTab] = useState(0);
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchFiles = async () => {
      const res = await axios.get(`${API_URL}/list-files`);
      if (tab === 0) {
        setFiles(res.data.csv_files || []);
      } else if (tab === 1) {
        setFiles(res.data.mp4_files || []);
      } else {
        setFiles(res.data.h264_files || []);
      }
    };
    fetchFiles();
  }, [tab]);

  const handleTabChange = (event, newValue) => setTab(newValue);

  return (
    <div style={{ height: "100%", overflow: "auto", display: "flex", flexDirection: "column" }}>
      <Typography variant="h2" gutterBottom>
        Files
      </Typography>
      <Tabs value={tab} onChange={handleTabChange} centered>
        <Tab label="Data (.csv)" />
        <Tab label="Videos (.mp4)" />
        <Tab label="Raw (.h264)" />
      </Tabs>
      <List>
        {files.map((entry) => {
          const fileName = entry.name;
          const fileSize = entry.size;
          const downloadUrl = `${API_URL}/download?file=${encodeURIComponent(fileName)}`;
          const displayName = fileName.startsWith("videos/")
            ? fileName.replace(/^videos\//, "")
            : fileName;
          return (
            <ListItem
              key={fileName}
              disablePadding
              secondaryAction={
                selectedFile === fileName ? (
                  <a href={downloadUrl} download style={{ textDecoration: "none" }}>
                    <Button variant="contained" color="secondary" size="small" sx={{ ml: 1 }}>
                      Download
                    </Button>
                  </a>
                ) : null
              }
            >
              <ListItemButton
                selected={selectedFile === fileName}
                onClick={() => onFileSelect(fileName)}
              >
                <ListItemText
                  primary={displayName}
                  secondary={formatBytes(fileSize)}
                  secondaryTypographyProps={{
                    variant: "caption",
                    sx: { color: "text.disabled", fontStyle: "italic" },
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </div>
  );
}
