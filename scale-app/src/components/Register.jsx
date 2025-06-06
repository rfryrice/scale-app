import React, { useState } from "react";
import axios from 'axios'
import "./LoginForm.css";

const RegisterForm = ( {onRegister, switchToLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await axios.post('http://localhost:8080/register', {
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
        <button type="submit">Register</button>
        {error && <div style={{color: 'red'}}>{error}</div>}
      </form>
    </div>
  );
};

export default RegisterForm;