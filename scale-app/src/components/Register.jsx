import React, { useState } from "react";
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import axios from 'axios'
import "./LoginForm.css";

const API_URL = import.meta.env.VITE_API_URL;

const RegisterForm = ( {onRegister, switchToLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await axios.post(`${API_URL}/register`, {
        username,
        password,
      });
      if (res.status === 201) {
        setSuccess('Registration successful! You can now log in.');
        setUsername('');
        setPassword('');
        // Optionally, you could auto-switch to login
        // onRegister();
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        setError(err.response.data.message);
      } else {
        setError('Registration failed.');
      }
    }
  };



  return (
    <div id="login-form">
      <h1>Register</h1>
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
        <Button type="submit" variant="contained">Register</Button>
        {error && <div style={{color: 'red'}}>{error}</div>}
        {success && <div style={{color: 'green'}}>{success}</div>}
        <div>
          Already have an account?{' '}
          <Link underline="hover" onClick={switchToLogin}>Log In</Link>
        </div>
      </form>
    </div>
  );
};

export default RegisterForm;