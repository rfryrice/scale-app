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

export default function ListData({ onFileSelect, selectedFile }) {
  const [tab, setTab] = useState(0);
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchFiles = async () => {
      const res = await axios.get(`${API_URL}/list-files`);
      if (tab === 0) {
        setFiles(res.data.csv_files || []);
      } else {
        setFiles(res.data.mp4_files || []);
      }
    };
    fetchFiles();
  }, [tab]);

  const handleTabChange = (event, newValue) => setTab(newValue);

  return (
    <div>
      <Typography variant="h2" gutterBottom>
        Files
      </Typography>
      <Tabs value={tab} onChange={handleTabChange} centered>
        <Tab label="Data (.csv)" />
        <Tab label="Videos (.mp4)" />
      </Tabs>
      <List>
        {files.map((file) => {
          // Determine download URL
          let downloadUrl = "";
          let displayName = file;
          if (tab === 0) {
            // CSV files are in the data directory
            downloadUrl = `${API_URL}/data/${file}`;
          } else {
            // MP4 files are in the data/videos directory
            downloadUrl = `${API_URL}/data/${file}`;
            // Remove 'videos/' prefix for display
            if (file.startsWith("videos/")) {
              displayName = file.replace(/^videos\//, "");
            }
          }
          return (
            <ListItem key={file} disablePadding
              secondaryAction={
                selectedFile === file ? (
                  <a href={downloadUrl} download style={{ textDecoration: "none" }}>
                    <Button
                      variant="contained"
                      color="secondary"
                      size="small"
                      sx={{ ml: 1 }}
                    >
                      Download
                    </Button>
                  </a>
                ) : null
              }
            >
              <ListItemButton
                selected={selectedFile === file}
                onClick={() => onFileSelect(file)}
              >
                <ListItemText primary={displayName} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </div>
  );
}
