import { useState, useEffect, useRef } from "react";
import { ColorModeContext, useMode } from "./theme";
import {
  CssBaseline,
  ThemeProvider,
  Card,
  CardContent,
  Box,
  Typography
} from "@mui/material";
import Grid from "@mui/material/Grid"; // Use Grid v2
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";
import LoginForm from "./components/Login";
import RegisterForm from "./components/Register";
import Dashboard from "./components/Dashboard";
import ListData from "./components/ListData";
import VideoControl from "./components/VideoControl";
import TopBar from "./scenes/global/TopBar";
import PersistentDrawerLeft from "./scenes/global/Drawer";
import SensorControl from "./components/SensorControl";
import SystemMonitor from "./components/SystemMonitor";

function App() {
  const [theme, colorMode] = useMode();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isSidebar, setIsSidebar] = useState(true);
  const [isLivestreamActive, setIsLivestreamActive] = useState(false);
  const [isRecordingActive, setIsRecordingActive] = useState(false);
  const [username, setUsername] = useState("");
  const [showRegister, setShowRegister] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [listKey, setListKey] = useState(0);
  const headerRef = useRef();

  // Example api call to backend
  /*   const fetchAPI = async() => {
    const response = await axios.get("http://localhost:8080/api/users")
    console.log(response.data.users)
    setArray(response.data.users)
  }; */

  useEffect(() => {
    // Restore login state from localStorage
    const savedLogin = localStorage.getItem("isLoggedIn") === "true";
    const savedUsername = localStorage.getItem("username") || "";
    setIsLoggedIn(savedLogin);
    setUsername(savedUsername);

    /* const fetchStatuses = async () => {
      const liveRes = await axios.get(`${API_URL}/video/status`);
      setIsLivestreamActive(liveRes.data.running);

      const recRes = await axios.get(`${API_URL}/video/status`);
      setIsRecordingActive(recRes.data.running);
    };
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 2000); // Poll every 2s
    return () => clearInterval(interval); */
  }, []);

  useEffect(() => {
    const onScroll = () => {
      if (headerRef.current) {
        if (window.scrollY > 40) {
          headerRef.current.classList.add("scrolled");
        } else {
          headerRef.current.classList.remove("scrolled");
        }
      }
    };
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogin = (user) => {
    setIsLoggedIn(true);
    setUsername(user);
    // Save to localStorage
    localStorage.setItem("isLoggedIn", "true");
    localStorage.setItem("username", user);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUsername("");
    // Clear localStorage
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("username");
  };

  const switchToRegister = () => setShowRegister(true);
  const switchToLogin = () => setShowRegister(false);

  // Handle file selection from ListData
  const handleFileSelect = (filename) => {
    setSelectedFile(filename);
  };

  const handleDataChanged = () => setListKey((k) => k + 1);

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <div className="app">
          <PersistentDrawerLeft
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            isSidebar={isSidebar}
          />
          <main className="content">
            <TopBar
              setIsSidebar={setIsSidebar}
              onDrawerOpen={() => setDrawerOpen(true)}
              username={username}
              onLogout={handleLogout}
            />

            <Box
              className="header-row"
              ref={headerRef}
              sx={{
                backgroundColor: theme.palette.background.paper,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "1.5rem",
                position: "sticky",
                top: "64px",
                zIndex: 1100,
                transition: "opacity 0.3s",
                boxShadow: "0 2px 8px -6px rgba(0,0,0,0.15)",
                "&.scrolled": {
                  opacity: 0,
                  pointerEvents: "none",
                },
                // Remove default margin from h1 inside Box
                "& h1": {
                  margin: 0,
                },
              }}
            >
              <a href="https://vite.dev" target="_blank">
                <img src={viteLogo} className="logo" alt="Vite logo" />
              </a>
              <Typography variant="h1" className="header-title"> Scale App</Typography>
              <a href="https://react.dev" target="_blank">
                <img src={reactLogo} className="logo react" alt="React logo" />
              </a>
            </Box>
            
            <Typography variant="body1">Interface with scale and livestream using this app</Typography>

            <div className="dashboard-layout">
              {isLoggedIn ? (
                <>
                  <Grid container spacing={2}>
                    {/* Sidebar: ListData spans 2 rows on md+ */}
                    <Grid size={{ xs: 12, md: 3 }}>
                      <Card sx={{ height: { md: "100%" } }}>
                        <CardContent>
                          <ListData
                            key={listKey}
                            onFileSelect={handleFileSelect}
                            selectedFile={selectedFile}
                          />
                        </CardContent>
                      </Card>
                    </Grid>
                    {/* Main content: Dashboard, SensorControl, VideoControl */}
                    <Grid size={{ xs: 12, md: 9 }}>
                      <Grid container spacing={2} alignItems={"stretch"}>
                        <Grid size={{ xs: 12, md: 8 }}>
                          <Card sx={{ mb: 2, height: "100%" }}>
                            <CardContent>
                              <Dashboard selectedFile={selectedFile} />
                            </CardContent>
                          </Card>
                        </Grid>
                        <Grid size={{ xs: 12, md: 4 }}>
                          <Card sx={{ height: "100%" }}>
                            <CardContent>
                              <SensorControl onDataChanged={handleDataChanged} />
                            </CardContent>
                          </Card>
                        </Grid>
                        <Grid size={{ xs: 12, md: 12 }}>
                          <Card sx={{ mb: 2 }}>
                              <VideoControl selectedFile={selectedFile} /> {/* CardMedia and CardContent inside component */}
                          </Card>
                        </Grid>
                        <Grid size={{ xs: 12, md: 12 }}>
                          <Card sx={{ mb: 2 }}>
                            <CardContent>
                              <SystemMonitor />
                            </CardContent>
                          </Card>
                        </Grid>
                      </Grid>
                    </Grid>
                  </Grid>
                </>
              ) : showRegister ? (
                <RegisterForm
                  onRegister={switchToLogin}
                  switchToLogin={switchToLogin}
                />
              ) : (
                <LoginForm
                  onLogin={handleLogin}
                  switchToRegister={switchToRegister}
                />
              )}
            </div>
            <p className="read-the-docs">
              Click on the Vite and React logos to learn more
            </p>
          </main>
        </div>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export default App;
