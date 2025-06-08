import React, { useEffect, useState } from "react";
import axios from "axios";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

function ListData({ onFileSelect, selectedFile }) {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get("http://localhost:8080/list-csv")
      .then((res) => setFiles(res.data.files))
      .catch((err) => setError(err.message));
  }, []);

  const handleClick = (filename) => {
    if (onFileSelect) {
      onFileSelect(filename);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 2, maxWidth: 400, margin: "2rem auto" }}>
      <Typography variant="h6" gutterBottom>
        CSV Files in Data Directory
      </Typography>
      {error && <Typography color="error">{error}</Typography>}
      <List>
        {files.length === 0 ? (
          <ListItem>
            <ListItemText primary="No CSV files found." />
          </ListItem>
        ) : (
          files.map((file, idx) => (
            <ListItem
              button
              key={idx}
              onClick={() => handleClick(file)}
              selected={file === selectedFile}
              sx={{
                backgroundColor: file === selectedFile ? "primary.light" : "",
                cursor: "pointer"
              }}
            >
              <ListItemText primary={file} />
            </ListItem>
          ))
        )}
      </List>
    </Paper>
  );
}

export default ListData;