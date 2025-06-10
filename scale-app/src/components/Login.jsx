import React, { useState } from "react";
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import axios from 'axios'
import "./LoginForm.css";

const API_URL = import.meta.env.VITE_API_URL;

const LoginForm = ( {onLogin, switchToRegister }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await axios.post(`${API_URL}/login`, {
        username,
        password,
      });
      if (res.status === 200) {
        onLogin(username); // Notify parent
      }
    } catch (err) {
      setError('Invalid username or password');
    }
  };


  return (
    <div id="login-form">
      <h1>Login</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="username">Username:</label>
        <input
          type="text"
          id="username"
          name="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <label htmlFor="password">Password:</label>
        <input
          type="password"
          id="password"
          name="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" variant="contained">Submit</Button>
        {error && <div style={{color: 'red'}}>{error}</div>}
        <div>
          Don't have an account?{' '}
          <Link href="#" underline="hover" onClick={switchToRegister}>Register</Link>
        </div>
      </form>
    </div>
  );
};

export default LoginForm;