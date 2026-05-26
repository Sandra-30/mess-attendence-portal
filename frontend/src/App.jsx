import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import StudentDashboard from './pages/StudentDashboard';
import WardenDashboard from './pages/WardenDashboard';
import ViewToggle from './components/ViewToggle';
import './styles/global.css';

function App() {
  return (
    <Router>
      <ViewToggle />
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/student/*" element={<StudentDashboard />} />
        <Route path="/warden/*" element={<WardenDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
