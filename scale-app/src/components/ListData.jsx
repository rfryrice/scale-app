import React, { useEffect, useState } from "react";
import {
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
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
        setFiles(res.data.avi_files || []);
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
        <Tab label="Videos (.avi)" />
      </Tabs>
      <List>
        {files.map((file) => {
          // Determine download URL
          let downloadUrl = "";
          if (tab === 0) {
            // CSV files are in the data directory
            downloadUrl = `${API_URL}/data/${file}`;
          } else {
            // AVI files are in the data/videos directory
            downloadUrl = `${API_URL}/data/${file}`;
          }
          return (
            <ListItem key={file} disablePadding secondaryAction={
              <a href={downloadUrl} download style={{ textDecoration: "none" }}>
                <button style={{ marginLeft: 8 }}>Download</button>
              </a>
            }>
              <ListItemButton
                selected={selectedFile === file}
                onClick={() => onFileSelect(file)}
              >
                <ListItemText primary={file} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </div>
  );
}
