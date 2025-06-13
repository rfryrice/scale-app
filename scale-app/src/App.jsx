import { useState, useEffect } from 'react'
import { ColorModeContext, useMode } from './theme'
import { CssBaseline, Drawer, ThemeProvider } from "@mui/material"
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import LoginForm from "./components/Login"
import RegisterForm from "./components/Register"
import Dashboard from "./components/Dashboard"
import ListData from "./components/ListData"
import LiveStream from "./components/LiveStream"
import TopBar from "./scenes/global/TopBar"
import PersistentDrawerLeft from "./scenes/global/Drawer"
import SensorControl from "./components/SensorControl"
import RecordingControl from './components/RecordingControl'

function App() {
  const [theme, colorMode] = useMode()
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isSidebar, setIsSidebar] = useState(true)
  const [isLivestreamActive, setIsLivestreamActive] = useState(false);
  const [isRecordingActive, setIsRecordingActive] = useState(false);
  const [username, setUsername] = useState('')
  const [showRegister, setShowRegister] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [listKey, setListKey] = useState(0)


// Example api call to backend
/*   const fetchAPI = async() => {
    const response = await axios.get("http://localhost:8080/api/users")
    console.log(response.data.users)
    setArray(response.data.users)
  }; */

  useEffect(() => {
    // Restore login state from localStorage
    const savedLogin = localStorage.getItem('isLoggedIn') === 'true';
    const savedUsername = localStorage.getItem('username') || '';
    setIsLoggedIn(savedLogin);
    setUsername(savedUsername);
    const fetchStatuses = async () => {
      const liveRes = await axios.get(`${API_URL}/livestream/status`);
      setIsLivestreamActive(liveRes.data.running);

      const recRes = await axios.get(`${API_URL}/recording/status`);
      setIsRecordingActive(recRes.data.running);
    };
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 2000); // Poll every 2s
    return () => clearInterval(interval);
  }, []);

  const handleLogin = (user) => {
    setIsLoggedIn(true)
    setUsername(user)
  // Save to localStorage
    localStorage.setItem('isLoggedIn', 'true');
    localStorage.setItem('username', user);
  };

  const handleLogout = () => {
    setIsLoggedIn(false)
    setUsername('')
    // Clear localStorage
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('username');
  }

  const switchToRegister = () => setShowRegister(true);
  const switchToLogin = () => setShowRegister(false);

  // Handle file selection from ListData
  const handleFileSelect = (filename) => {
    setSelectedFile(filename);
  };

  const handleDataChanged = () => setListKey(k => k + 1);

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline/>
        <div className="app">
          <PersistentDrawerLeft open={drawerOpen} onClose={() => setDrawerOpen(false)} isSidebar={isSidebar} />
          <main className="content">
            <TopBar setIsSidebar={setIsSidebar} onDrawerOpen={() => setDrawerOpen(true)} />

            <div>
              <a href="https://vite.dev" target="_blank">
                <img src={viteLogo} className="logo" alt="Vite logo" />
              </a>
              <a href="https://react.dev" target="_blank">
                <img src={reactLogo} className="logo react" alt="React logo" />
              </a>
            </div>
            <h1>Scale-App</h1>
            <p>Interface with scale and livestream using this app</p>

            <div className="card">
              {isLoggedIn ? (
                <>
                  <p>Welcome, {username}!</p>
                  <button onClick={handleLogout}>Log out</button>

                  {/* Flex layout for ListData and Dashboard */}
                  <div className="dashboard">
                    <ListData key={listKey} onFileSelect={handleFileSelect} selectedFile={selectedFile} />
                    <Dashboard selectedFile={selectedFile} />
                    <LiveStream />
                    <RecordingControl />
                    <SensorControl onDataChanged={handleDataChanged}/>
                  </div>
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
  )
}

export default App
