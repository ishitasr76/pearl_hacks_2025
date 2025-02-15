import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(null);
  const [eventName, setEventName] = useState('');
  const [events, setEvents] = useState([]);

  const handleSignup = async () => {
    try {
      // Add headers to indicate JSON request
      await axios.post('http://127.0.0.1:5000/auth/signup', 
        { 
          email, 
          password, 
          name: "User" 
        }, 
        {
          headers: {
            'Content-Type': 'application/json' // Ensure the content type is application/json
          }
        }
      );
      alert('Signup successful!');
    } catch (error) {
      alert('Signup failed: ' + error.message); // Improved error message
    }
  };

  const handleLogin = async () => {
    try {
      const res = await axios.post('http://127.0.0.1:5000/auth/login', { email, password });
      setToken(res.data.access_token);
      alert('Login successful!');
    } catch (error) {
      alert('Login failed');
    }
  };

  const createEvent = async () => {
    try {
      const res = await axios.post('http://127.0.0.1:5000/event/create', { name: eventName, user_id: 1 }, {  // Replace 1 with the actual user_id
        headers: { Authorization: `Bearer ${token}` }
      });
      setEvents([...events, { id: res.data.event_id, name: eventName }]);
      alert('Event created!');
    } catch (error) {
      alert('Failed to create event');
    }
  };

  return (
    <div>
      <h1>Event Expense Splitter</h1>
      <h2>Signup/Login</h2>
      <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
      <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
      <button onClick={handleSignup}>Signup</button>
      <button onClick={handleLogin}>Login</button>

      {token && (
        <div>
          <h2>Create Event</h2>
          <input type="text" placeholder="Event Name" value={eventName} onChange={e => setEventName(e.target.value)} />
          <button onClick={createEvent}>Create Event</button>
          <h3>Your Events</h3>
          <ul>
            {events.map(event => <li key={event.id}>{event.name}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
