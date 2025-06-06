import axios from "axios"
import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import LoginForm from "./components/Login"

function App() {
  const [count, setCount] = useState(0)
  const [array, setArray] = useState([])
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState('')

  const fetchAPI = async() => {
    const response = await axios.get("http://localhost:8080/api/users")
    console.log(response.data.users)
    setArray(response.data.users)
  };

  useEffect(() => {
    fetchAPI();
  }, []);

  const handleLogin = (user) => {
    setIsLoggedIn(true)
    setUsername(user)
  };

  const handleLogout = () => {
    setIsLoggedIn(false)
    setUsername('')
  }

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
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
          {
            array.map((user, index) => (
              <div key={index}>
              <span >{user}</span>
              <br></br>
              </div>
            ))
          }
      </div>
      <div>
        <LoginForm onLogin={handleLogin}/>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  )
}

export default App
