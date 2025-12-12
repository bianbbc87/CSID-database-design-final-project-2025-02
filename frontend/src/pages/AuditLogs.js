import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function AuditLogs() {
  const [auditLogs, setAuditLogs] = useState([]);

  const fetchAuditLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/audit-logs`);
      const data = await response.json();
      setAuditLogs(data);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    }
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
              <th>Action</th>
              <th>Entity Type</th>
              <th>Entity ID</th>
              <th>User</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map(log => (
              <tr key={log.audit_id}>
                <td>{new Date(log.created_at).toLocaleString()}</td>
                <td>
                  <span className={`action-badge ${getActionBadgeClass(log.action_type)}`}>
                    {log.action_type}
                  </span>
                </td>
                <td>{log.target_type}</td>
                <td><code>{log.target_id}</code></td>
                <td>{log.username || 'System'}</td>
                <td>
                  {log.details && (
                    <details>
                      <summary>View Details</summary>
                      <pre>{formatJsonValue(log.details)}</pre>
                    </details>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AuditLogs;
