import axios from "axios"
import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import LoginForm from "./components/Login"
import RegisterForm from "./components/Register"
import Dashboard from "./components/Dashboard"
import ListData from "./components/ListData"

function App() {
  const [count, setCount] = useState(0)
  const [array, setArray] = useState([])
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState('')
  const [showRegister, setShowRegister] = useState(false);


  const fetchAPI = async() => {
    const response = await axios.get("http://localhost:8080/api/users")
    console.log(response.data.users)
    setArray(response.data.users)
  };

  useEffect(() => {
    // Restore login state from localStorage
    const savedLogin = localStorage.getItem('isLoggedIn') === 'true';
    const savedUsername = localStorage.getItem('username') || '';
    setIsLoggedIn(savedLogin);
    setUsername(savedUsername);
    fetchAPI();
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



  return (
    <>
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
            <div>
              <button onClick={() => setCount((count) => count + 1)}>
                count is {count}
              </button>
            </div>
            <ListData />

            <Dashboard />

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
    </>
  )
}

export default App
