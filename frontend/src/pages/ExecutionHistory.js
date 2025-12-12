import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function ExecutionHistory() {
  const [runs, setRuns] = useState([]);
  const [containerLogs, setContainerLogs] = useState([]);
  const [selectedContainer, setSelectedContainer] = useState('');
  const [logTail, setLogTail] = useState(100);
  const [showContainerLogs, setShowContainerLogs] = useState(false);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    sortBy: 'started_at',
    sortOrder: 'desc', // Latest first as default
    startDate: '',
    endDate: ''
  });
  const [currentRunsPage, setCurrentRunsPage] = useState(1);
  const [runsPerPage] = useState(10);

  const fetchRuns = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/runs`);
      const data = await response.json();
      
      // ISO 문자열로 직접 정렬 (한국어 날짜 파싱 문제 해결)
      const sortedData = data.sort((a, b) => {
        return b.started_at.localeCompare(a.started_at); // 문자열 비교로 최신순
      });
      
      setRuns(sortedData);
    } catch (error) {
      console.error('Error fetching runs:', error);
    }
  };

  const fetchRunDetails = async (runId) => {
    try {
      const response = await fetch(`${API_BASE}/api/runs/${runId}/logs`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching run details:', error);
      return null;
    }
  };

  const viewContainerLogs = async (runId) => {
    const details = await fetchRunDetails(runId);
    if (details && details.container_id) {
      setSelectedContainer(details.container_id);
      setShowContainerLogs(true);
      fetchContainerLogs(details.container_id);
    } else {
      alert('Container logs not available for this run');
    }
  };

  const fetchContainerLogs = async (containerId) => {
    try {
      const response = await fetch(`${API_BASE}/api/containers/${containerId}/logs?tail=${logTail}`);
      const data = await response.json();
      setContainerLogs(data.logs || []);
    } catch (error) {
      console.error('Error fetching container logs:', error);
      setContainerLogs([]);
    }
  };

  const filteredRuns = runs.filter(run => {
    const matchesSearch = run.job_name.toLowerCase().includes(filters.search.toLowerCase()) ||
                         run.user.toLowerCase().includes(filters.search.toLowerCase());
    const matchesStatus = !filters.status || run.status === filters.status;
    
    let matchesDate = true;
    if (filters.startDate || filters.endDate) {
      const runDate = new Date(run.started_at);
      if (filters.startDate) {
        matchesDate = matchesDate && runDate >= new Date(filters.startDate);
      }
      if (filters.endDate) {
        matchesDate = matchesDate && runDate <= new Date(filters.endDate + 'T23:59:59');
      }
    }
    
    return matchesSearch && matchesStatus && matchesDate;
  }).sort((a, b) => {
    // ISO 문자열 비교로 최신순 정렬 (한국어 날짜 파싱 문제 해결)
    return b.started_at.localeCompare(a.started_at);
  });

  const paginatedRuns = filteredRuns.slice(
    (currentRunsPage - 1) * runsPerPage,
    currentRunsPage * runsPerPage
  );

  useEffect(() => {
    fetchRuns();
  }, []);

  return (
    <div className="execution-history-page">
      <div className="section-header">
        <h2>Execution History</h2>
        <button className="refresh-btn" onClick={fetchRuns}>
          🔄 Refresh
        </button>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Search by job name or user..."
          value={filters.search}
          onChange={(e) => setFilters({...filters, search: e.target.value})}
        />
        <select
          value={filters.status}
          onChange={(e) => setFilters({...filters, status: e.target.value})}
        >
          <option value="">All Status</option>
          <option value="RUNNING">Running</option>
          <option value="SUCCESS">Success</option>
          <option value="FAILED">Failed</option>
        </select>
        <input
          type="date"
          value={filters.startDate}
          onChange={(e) => setFilters({...filters, startDate: e.target.value})}
          placeholder="Start Date"
        />
        <input
          type="date"
          value={filters.endDate}
          onChange={(e) => setFilters({...filters, endDate: e.target.value})}
          placeholder="End Date"
        />
        <select
          value={`${filters.sortBy}-${filters.sortOrder}`}
          onChange={(e) => {
            const [sortBy, sortOrder] = e.target.value.split('-');
            setFilters({...filters, sortBy, sortOrder});
          }}
        >
          <option value="started_at-desc">🕒 Latest (Newest First)</option>
          <option value="started_at-asc">🕒 Oldest First</option>
          <option value="job_name-asc">📝 Job Name A-Z</option>
          <option value="job_name-desc">📝 Job Name Z-A</option>
          <option value="status-asc">📊 Status A-Z</option>
        </select>
      </div>

      <div className="pagination">
        <button 
          onClick={() => setCurrentRunsPage(prev => Math.max(prev - 1, 1))}
          disabled={currentRunsPage === 1}
        >
          ← Previous
        </button>
        <span>Page {currentRunsPage} of {Math.ceil(filteredRuns.length / runsPerPage)}</span>
        <button 
          onClick={() => setCurrentRunsPage(prev => Math.min(prev + 1, Math.ceil(filteredRuns.length / runsPerPage)))}
          disabled={currentRunsPage === Math.ceil(filteredRuns.length / runsPerPage)}
        >
          Next →
        </button>
      </div>

      <div className="runs-table">
        <table>
          <thead>
            <tr>
              <th>Job Name</th>
              <th>Status</th>
              <th>Started At</th>
              <th>Finished At</th>
              <th>Exit Code</th>
              <th>User</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedRuns.map(run => (
              <tr key={run.run_id}>
                <td>{run.job_name || 'N/A'}</td>
                <td>
                  <span className={`status-badge ${(run.status || '').toLowerCase()}`}>
                    {run.status || 'UNKNOWN'}
                  </span>
                </td>
                <td>{run.started_at ? new Date(run.started_at).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', hour12: false}) : 'N/A'}</td>
                <td>{run.finished_at ? new Date(run.finished_at).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', hour12: false}) : 'Running...'}</td>
                <td>{run.exit_code !== null ? run.exit_code : 'N/A'}</td>
                <td>{run.user || 'System'}</td>
                <td>
                  <span className={`run-type-badge ${(run.run_type || '').toLowerCase()}`}>
                    {run.run_type || 'UNKNOWN'}
                  </span>
                </td>
                <td>
                  <button 
                    className="logs-button"
                    onClick={() => viewContainerLogs(run.run_id)}
                  >
                    📋 Logs
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showContainerLogs && (
        <div className="modal-overlay" onClick={() => setShowContainerLogs(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Container Logs - {selectedContainer}</h3>
              <button onClick={() => setShowContainerLogs(false)}>✕</button>
            </div>
            <div className="log-controls">
              <label>
                Tail lines:
                <input
                  type="number"
                  value={logTail}
                  onChange={(e) => setLogTail(e.target.value)}
                  min="10"
                  max="1000"
                />
              </label>
              <button onClick={() => fetchContainerLogs(selectedContainer)}>
                🔄 Refresh Logs
              </button>
            </div>
            <div className="logs-container">
              {containerLogs.map((log, index) => (
                <div key={index} className="log-line">
                  <span className="log-timestamp">{log.timestamp}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ExecutionHistory;
