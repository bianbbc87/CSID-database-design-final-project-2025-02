import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function Schedules() {
  const [schedules, setSchedules] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    job_id: '',
    cron_expression: ''
  });

  const fetchSchedules = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules`);
      const data = await response.json();
      setSchedules(data);
    } catch (error) {
      console.error('Error fetching schedules:', error);
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/jobs`);
      const data = await response.json();
      setJobs(data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const createSchedule = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/schedules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSchedule),
      });
      
      if (response.ok) {
        alert('Schedule created successfully!');
        setShowScheduleModal(false);
        setNewSchedule({
          job_id: '',
          cron_expression: ''
        });
        fetchSchedules();
      }
    } catch (error) {
      console.error('Error creating schedule:', error);
    }
  };

  const toggleSchedule = async (scheduleId, currentStatus) => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules/${scheduleId}/toggle`, {
        method: 'PUT',
      });
      
      if (response.ok) {
        alert(`Schedule ${currentStatus ? 'deactivated' : 'activated'}!`);
        fetchSchedules();
      }
    } catch (error) {
      console.error('Error toggling schedule:', error);
    }
  };

  const deleteSchedule = async (scheduleId) => {
    if (window.confirm('Are you sure you want to delete this schedule?')) {
      try {
        const response = await fetch(`${API_BASE}/api/schedules/${scheduleId}`, {
          method: 'DELETE',
        });
        
        if (response.ok) {
          alert('Schedule deleted successfully!');
          fetchSchedules();
        }
      } catch (error) {
        console.error('Error deleting schedule:', error);
      }
    }
  };

  useEffect(() => {
    fetchSchedules();
    fetchJobs();
  }, []);

  return (
    <div className="schedules-page">
      <div className="section-header">
        <h2>Job Schedules</h2>
        <button className="add-schedule-btn" onClick={() => setShowScheduleModal(true)}>
          ➕ Add Schedule
        </button>
      </div>

      <div className="schedules-table">
        <table>
          <thead>
            <tr>
              <th>Job Name</th>
              <th>Cron Expression</th>
              <th>Status</th>
              <th>Created At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {schedules.map(schedule => (
              <tr key={schedule.schedule_id}>
                <td>{schedule.job_name}</td>
                <td><code>{schedule.cron_expression}</code></td>
                <td>
                  <span className={`status-badge ${schedule.is_active ? 'active' : 'inactive'}`}>
                    {schedule.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{new Date(schedule.created_at).toLocaleString()}</td>
                <td>
                  <button 
                    className={`toggle-btn ${schedule.is_active ? 'deactivate' : 'activate'}`}
                    onClick={() => toggleSchedule(schedule.schedule_id, schedule.is_active)}
                  >
                    {schedule.is_active ? '⏸️ Deactivate' : '▶️ Activate'}
                  </button>
                  <button 
                    className="delete-btn"
                    onClick={() => deleteSchedule(schedule.schedule_id)}
                  >
                    🗑️ Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showScheduleModal && (
        <div className="modal-overlay" onClick={() => setShowScheduleModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Schedule</h3>
              <button onClick={() => setShowScheduleModal(false)}>✕</button>
            </div>
            <form onSubmit={createSchedule}>
              <div className="form-group">
                <label>Job:</label>
                <select
                  value={newSchedule.job_id}
                  onChange={(e) => setNewSchedule({...newSchedule, job_id: e.target.value})}
                  required
                >
                  <option value="">Select Job</option>
                  {jobs.map(job => (
                    <option key={job.job_id} value={job.job_id}>{job.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Cron Expression:</label>
                <input
                  type="text"
                  value={newSchedule.cron_expression}
                  onChange={(e) => setNewSchedule({...newSchedule, cron_expression: e.target.value})}
                  placeholder="0 0 * * * (every day at midnight)"
                  required
                />
                <small>Format: second minute hour day month weekday</small>
              </div>
              <div className="form-actions">
                <button type="button" onClick={() => setShowScheduleModal(false)}>
                  Cancel
                </button>
                <button type="submit">Create Schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Schedules;
