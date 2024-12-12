import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import './App.css';

import Containers from './pages/Containers';
import ExecutionHistory from './pages/ExecutionHistory';
import Schedules from './pages/Schedules';
import AuditLogs from './pages/AuditLogs';
import Users from './pages/Users';

function Navigation() {
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path;

  return (
    <nav className="main-nav">
      <Link 
        to="/containers" 
        className={isActive('/containers') ? 'nav-link active' : 'nav-link'}
      >
        🐳 Containers
      </Link>
      <Link 
        to="/execution-history" 
        className={isActive('/execution-history') ? 'nav-link active' : 'nav-link'}
      >
        📊 Execution History
      </Link>
      <Link 
        to="/schedules" 
        className={isActive('/schedules') ? 'nav-link active' : 'nav-link'}
      >
        ⏰ Schedules
      </Link>
      <Link 
        to="/audit-logs" 
        className={isActive('/audit-logs') ? 'nav-link active' : 'nav-link'}
      >
        📋 Audit Logs
      </Link>
      <Link 
        to="/users" 
        className={isActive('/users') ? 'nav-link active' : 'nav-link'}
      >
        사용자 관리
      </Link>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>🚀 Job Management System</h1>
          <Navigation />
        </header>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Containers />} />
            <Route path="/containers" element={<Containers />} />
            <Route path="/execution-history" element={<ExecutionHistory />} />
            <Route path="/schedules" element={<Schedules />} />
            <Route path="/audit-logs" element={<AuditLogs />} />
            <Route path="/users" element={<Users />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
