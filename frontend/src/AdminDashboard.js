import React, { useState, useEffect } from 'react';
import './AdminDashboard.css';

const API_BASE = 'http://localhost:8000';

function AdminDashboard() {
  const [jobs, setJobs] = useState([]);
  const [runs, setRuns] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // 5초마다 새로고침
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [jobsRes, runsRes, auditRes] = await Promise.all([
        fetch(`${API_BASE}/api/jobs`),
        fetch(`${API_BASE}/api/runs`),
        fetch(`${API_BASE}/api/audit-logs`)
      ]);
      
      setJobs(await jobsRes.json());
      setRuns(await runsRes.json());
      setAuditLogs(await auditRes.json());
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const fetchRunDetails = async (runId) => {
    try {
      const response = await fetch(`${API_BASE}/api/runs/${runId}/logs`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching run details:', error);
      return null;
    }
  };

  const openRunDetails = async (run) => {
    const details = await fetchRunDetails(run.run_id);
    setSelectedRun({ ...run, details });
    setShowModal(true);
  };

  const getStatusStats = () => {
    return runs.reduce((acc, run) => {
      acc[run.status] = (acc[run.status] || 0) + 1;
      return acc;
    }, {});
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS': return '#00D084';
      case 'FAILED': return '#F2495C';
      case 'RUNNING': return '#5794F2';
      default: return '#8E8E93';
    }
  };

  const stats = getStatusStats();
  const successRate = runs.length > 0 ? Math.round((stats.SUCCESS || 0) / runs.length * 100) : 0;

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <h1>🚀 Job Management System</h1>
        <div className="header-stats">
          <span className="live-indicator">🟢 Live</span>
          <span className="last-update">Last update: {new Date().toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <h3>Total Jobs</h3>
            <span className="metric-icon">🔧</span>
          </div>
          <div className="metric-value">{jobs.length}</div>
          <div className="metric-change">+{jobs.filter(j => new Date(j.created_at) > new Date(Date.now() - 24*60*60*1000)).length} today</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <h3>Success Rate</h3>
            <span className="metric-icon">✅</span>
          </div>
          <div className="metric-value">{successRate}%</div>
          <div className="metric-change">
            {successRate >= 90 ? '🟢 Healthy' : successRate >= 70 ? '🟡 Warning' : '🔴 Critical'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <h3>Running Jobs</h3>
            <span className="metric-icon">⚡</span>
          </div>
          <div className="metric-value">{stats.RUNNING || 0}</div>
          <div className="metric-change">Active now</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <h3>Failed Jobs</h3>
            <span className="metric-icon">❌</span>
          </div>
          <div className="metric-value">{stats.FAILED || 0}</div>
          <div className="metric-change">Need attention</div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="activity-panel">
          <h3>🔥 Recent Activity</h3>
          <div className="activity-list">
            {runs.slice(0, 8).map(run => (
              <div key={run.run_id} className="activity-item">
                <div 
                  className="status-indicator"
                  style={{ backgroundColor: getStatusColor(run.status) }}
                ></div>
                <div className="activity-info">
                  <div className="activity-header">
                    <strong>{run.job_name}</strong>
                    <span className={`status-badge ${run.status.toLowerCase()}`}>
                      {run.status}
                    </span>
                  </div>
                  <div className="activity-meta">
                    <span>👤 {run.user || 'System'}</span>
                    <span>🏠 {run.hostname}</span>
                    <span>⏰ {new Date(run.started_at).toLocaleString()}</span>
                  </div>
                </div>
                {run.status === 'FAILED' && (
                  <button 
                    className="error-details-btn"
                    onClick={() => openRunDetails(run)}
                  >
                    🔍 Error Details
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="audit-panel">
          <h3>🔍 Audit Trail</h3>
          <div className="audit-list">
            {auditLogs.slice(0, 6).map(log => (
              <div key={log.audit_id} className="audit-item">
                <div className="audit-icon">
                  {log.action_type === 'AUTO_JOB_START' ? '🚀' : 
                   log.action_type === 'CREATE_JOB' ? '➕' : 
                   log.action_type === 'UPDATE_JOB' ? '✏️' : '📝'}
                </div>
                <div className="audit-content">
                  <div className="audit-action">
                    <strong>{log.username}</strong> {log.action_type.toLowerCase().replace('_', ' ')}
                  </div>
                  <div className="audit-target">
                    {log.target_type}: {log.target_id.substring(0, 8)}...
                  </div>
                  <div className="audit-time">
                    {new Date(log.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Error Details Modal */}
      {showModal && selectedRun && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🔍 Error Analysis: {selectedRun.job_name}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              <div className="error-summary">
                <div className="error-info">
                  <span className="error-label">Status:</span>
                  <span className={`status-badge ${selectedRun.status.toLowerCase()}`}>
                    {selectedRun.status}
                  </span>
                </div>
                <div className="error-info">
                  <span className="error-label">Exit Code:</span>
                  <span className="error-value">{selectedRun.exit_code}</span>
                </div>
                <div className="error-info">
                  <span className="error-label">Duration:</span>
                  <span className="error-value">
                    {selectedRun.finished_at ? 
                      Math.round((new Date(selectedRun.finished_at) - new Date(selectedRun.started_at)) / 1000) + 's' 
                      : 'Running...'}
                  </span>
                </div>
              </div>

              {selectedRun.details?.errors?.length > 0 && (
                <div className="error-details">
                  <h4>🚨 Error Details</h4>
                  {selectedRun.details.errors.map((error, idx) => (
                    <div key={idx} className="error-block">
                      <div className="error-type">{error.type}</div>
                      <div className="error-message">{error.message}</div>
                      {error.stacktrace && (
                        <details className="stacktrace-details">
                          <summary>📋 Stack Trace</summary>
                          <pre className="stacktrace">{error.stacktrace}</pre>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {selectedRun.details?.logs && (
                <div className="logs-section">
                  <h4>📝 Execution Logs</h4>
                  <pre className="logs-content">{selectedRun.details.logs}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminDashboard;
