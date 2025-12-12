import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function AuditLogs() {
  const [auditLogs, setAuditLogs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchAuditLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/audit-logs`);
      const data = await response.json();
      setAuditLogs(data);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    }
  };

  const getContainerName = (afterValue) => {
    try {
      const parsed = typeof afterValue === 'string' ? JSON.parse(afterValue) : afterValue;
      return parsed?.container_name || 'N/A';
    } catch {
      return 'N/A';
    }
  };

  const openLogModal = (log) => {
    setSelectedLog(log);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedLog(null);
  };

  const getActionBadgeClass = (action) => {
    switch (action) {
      case 'AUTO_JOB_START': return 'action-create';
      case 'CREATE': return 'action-create';
      case 'DELETE': return 'action-delete';
      case 'ACTIVATE': return 'action-activate';
      case 'DEACTIVATE': return 'action-deactivate';
      default: return 'action-default';
    }
  };

  const formatJsonValue = (value) => {
    if (!value) return 'N/A';
    try {
      if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
      }
      const parsed = JSON.parse(value);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return value;
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  return (
    <div className="audit-logs-page">
      <div className="section-header">
        <h2>Audit Logs</h2>
        <button className="refresh-btn" onClick={fetchAuditLogs}>
          🔄 Refresh
        </button>
      </div>

      <div className="audit-logs-table">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Container Name</th>
              <th>Entity Type</th>
              <th>Entity ID</th>
              <th>User</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map(log => (
              <tr key={log.audit_id}>
                <td>{new Date(log.created_at).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', hour12: false})}</td>
                <td>{getContainerName(log.after_value)}</td>
                <td>{log.target_type}</td>
                <td><code>{log.target_id}</code></td>
                <td>{log.username || 'System'}</td>
                <td>
                  <button 
                    className="details-btn"
                    onClick={() => openLogModal(log)}
                  >
                    📋 View Logs
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 로그 모달 */}
      {showModal && selectedLog && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Container Logs - {getContainerName(selectedLog.after_value)}</h3>
              <button className="close-btn" onClick={closeModal}>✕</button>
            </div>
            <div className="modal-body">
              <pre className="log-text">
                {(() => {
                  try {
                    const parsed = typeof selectedLog.after_value === 'string' 
                      ? JSON.parse(selectedLog.after_value) 
                      : selectedLog.after_value;
                    return parsed?.logs || 'No logs available';
                  } catch {
                    return 'Error parsing logs';
                  }
                })()}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AuditLogs;
