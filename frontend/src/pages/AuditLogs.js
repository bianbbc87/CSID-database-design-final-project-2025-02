import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function AuditLogs() {
  const [auditLogs, setAuditLogs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  // Error type 추론 함수
  const inferErrorType = (log) => {
    if (!log.is_failed) return null;
    
    if (log.error_type) return log.error_type;
    
    // 기존 데이터에 대한 fallback 로직
    const exitCode = log.details?.exit_code;
    if (exitCode === 255 || exitCode > 128) return 'RESOURCE_ERROR';
    if (exitCode === 127) return 'SCRIPT_ERROR';
    if (exitCode === 126) return 'PERMISSION_ERROR';
    
    return 'SCRIPT_ERROR'; // 기본값
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/audit-logs`);
      const data = await response.json();
      setAuditLogs(data);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    }
  };

  const getContainerName = (log) => {
    try {
      // details에서 container_name 추출
      if (log.details && log.details.container_name) {
        return log.details.container_name;
      }
      
      // after_value에서도 시도 (백업)
      const afterValue = log.after_value;
      if (afterValue) {
        const parsed = typeof afterValue === 'string' ? JSON.parse(afterValue) : afterValue;
        return parsed?.container_name || 'N/A';
      }
      
      return 'N/A';
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
          Refresh
        </button>
      </div>

      <div className="audit-logs-table">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Container Name</th>
              <th>Status</th>
              <th>Error Type</th>
              <th>User</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map(log => (
              <tr key={log.audit_id}>
                <td>{new Date(log.created_at).toLocaleString('ko-KR', {
                  timeZone: 'Asia/Seoul',
                  year: 'numeric',
                  month: '2-digit', 
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  hour12: false
                })}</td>
                <td>{getContainerName(log)}</td>
                <td>
                  {log.is_failed ? (
                    <span className="status-badge failed">FAILED</span>
                  ) : (
                    <span className="status-badge success">SUCCESS</span>
                  )}
                </td>
                <td>
                  {inferErrorType(log) ? (
                    <span className={`error-type-badge ${inferErrorType(log).toLowerCase()}`}>
                      {inferErrorType(log)}
                    </span>
                  ) : (
                    <span className="error-type-badge none">-</span>
                  )}
                </td>
                <td>{log.username || 'System'}</td>
                <td>
                  <button 
                    className="details-btn"
                    onClick={() => openLogModal(log)}
                  >
                    View Logs
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
              <h3>Container Logs - {getContainerName(selectedLog)}</h3>
              <button className="close-btn" onClick={closeModal}>✕</button>
            </div>
            <div className="modal-body">
              <pre className="log-text">
                {(() => {
                  // details에서 logs 추출
                  if (selectedLog.details && selectedLog.details.logs) {
                    return selectedLog.details.logs;
                  }
                  
                  // after_value에서도 시도 (백업)
                  try {
                    const parsed = typeof selectedLog.after_value === 'string' 
                      ? JSON.parse(selectedLog.after_value) 
                      : selectedLog.after_value;
                    return parsed?.logs || 'No logs available';
                  } catch {
                    return 'No logs available';
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
