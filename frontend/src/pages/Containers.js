import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function Containers() {
  const [containers, setContainers] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [containersPerPage] = useState(6);

  const fetchContainers = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/containers`);
      const data = await response.json();
      setContainers(data);
    } catch (error) {
      console.error('Error fetching containers:', error);
    }
  };

  const startContainer = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE}/api/containers/${jobId}/start`, {
        method: 'POST',
      });
      const result = await response.json();
      
      if (result.success) {
        alert(result.message);
        fetchContainers();
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  const stopContainer = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE}/api/containers/${jobId}/stop`, {
        method: 'POST',
      });
      const result = await response.json();
      
      if (result.success) {
        alert(result.message);
        fetchContainers();
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  const deleteJob = async (jobId, jobName) => {
    if (!window.confirm(`Are you sure you want to delete job "${jobName}"? This will remove all related data permanently.`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        fetchContainers();
      } else {
        alert(`Error: ${result.detail}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  const viewLatestRun = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE}/api/containers/${jobId}/latest-run`);
      const data = await response.json();
      
      if (data.message) {
        alert(data.message);
      } else {
        alert(`Latest Run:\nStatus: ${data.status}\nStarted: ${data.started_at}\nUser: ${data.user}\nType: ${data.run_type}`);
      }
    } catch (error) {
      console.error('Error fetching latest run:', error);
    }
  };

  useEffect(() => {
    fetchContainers();
  }, []);

  return (
    <div className="containers-page">
      <div className="dashboard-stats">
        <div className="stat-card">
          <h3>Total Containers</h3>
          <p>{containers.length}</p>
        </div>
        <div className="stat-card">
          <h3>Running</h3>
          <p>{containers.filter(c => c.container_status === 'RUNNING').length}</p>
        </div>
        <div className="stat-card">
          <h3>Stopped</h3>
          <p>{containers.filter(c => c.container_status === 'STOPPED').length}</p>
        </div>
      </div>
      
      <div className="section-header">
        <h2>Container Management</h2>
        <button className="refresh-btn" onClick={fetchContainers}>
          🔄 Refresh
        </button>
      </div>
      
      <div className="pagination">
        <button 
          onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
          disabled={currentPage === 1}
        >
          ←
        </button>
        <span>Page {currentPage} of {Math.ceil(containers.length / containersPerPage)}</span>
        <button 
          onClick={() => setCurrentPage(prev => Math.min(prev + 1, Math.ceil(containers.length / containersPerPage)))}
          disabled={currentPage === Math.ceil(containers.length / containersPerPage)}
        >
          →
        </button>
      </div>
      
      <div className="jobs-grid">
        {containers
          .slice((currentPage - 1) * containersPerPage, currentPage * containersPerPage)
          .map(container => (
          <div key={container.job_id} className="job-card">
            <h3>{container.name}</h3>
            <p><strong>Status:</strong> <span className={`status-badge ${container.container_status.toLowerCase()}`}>{container.container_status}</span></p>
            <p><strong>Type:</strong> {container.type_name}</p>
            <p><strong>Image:</strong> <code>{container.docker_image || 'N/A'}</code></p>
            <p><strong>Owner:</strong> {container.username}</p>
            <div className="job-actions">
              {container.container_status === 'RUNNING' && (
                <button 
                  className="delete-btn"
                  onClick={() => stopContainer(container.job_id)}
                >
                  Stop
                </button>
              )}
              {(container.container_status === 'STOPPED' || container.container_status === 'CREATED') && (
                <button 
                  className="run-button"
                  onClick={() => startContainer(container.job_id)}
                >
                  ▶ Start
                </button>
              )}
              <button 
                className="delete-btn"
                onClick={() => deleteJob(container.job_id, container.name)}
              >
                Delete (Only References)
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Containers;
