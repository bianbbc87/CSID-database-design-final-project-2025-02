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
  const [scheduleType, setScheduleType] = useState('simple'); // 'simple' or 'advanced'
  const [simpleSchedule, setSimpleSchedule] = useState({
    type: 'minutes', // 'seconds', 'minutes', 'hours', 'daily', 'weekly'
    value: 1,
    hour: 9,
    minute: 0,
    dayOfWeek: 1
  });

  // 간단한 스케줄을 cron 표현식으로 변환
  const convertToCron = (simple) => {
    switch (simple.type) {
      case 'seconds':
        return `*/${simple.value} * * * * *`; // 매 N초
      case 'minutes':
        return `0 */${simple.value} * * *`; // 매 N분
      case 'hours':
        return `0 0 */${simple.value} * *`; // 매 N시간
      case 'daily':
        return `${simple.minute} ${simple.hour} * * *`; // 매일 특정 시간
      case 'weekly':
        return `${simple.minute} ${simple.hour} * * ${simple.dayOfWeek}`; // 매주 특정 요일
      default:
        return '0 9 * * *';
    }
  };

  // cron 표현식을 간단한 형태로 변환 (표시용)
  const cronToReadable = (cron) => {
    const parts = cron.split(' ');
    if (parts.length === 5) {
      const [min, hour, day, month, dow] = parts;
      
      if (min.startsWith('*/') && hour === '*' && day === '*' && month === '*' && dow === '*') {
        return `매 ${min.slice(2)}분마다`;
      }
      if (min !== '*' && hour !== '*' && day === '*' && month === '*' && dow === '*') {
        return `매일 ${hour}:${min.padStart(2, '0')}`;
      }
      if (min !== '*' && hour !== '*' && day === '*' && month === '*' && dow !== '*') {
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        return `매주 ${days[dow]}요일 ${hour}:${min.padStart(2, '0')}`;
      }
    }
    return cron;
  };

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
      // 스케줄 타입에 따라 cron 표현식 생성
      const cronExpression = scheduleType === 'simple' 
        ? convertToCron(simpleSchedule)
        : newSchedule.cron_expression;

      const scheduleData = {
        job_id: newSchedule.job_id,
        cron_expression: cronExpression
      };

      const response = await fetch(`${API_BASE}/api/schedules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scheduleData),
      });
      
      if (response.ok) {
        alert('Schedule created successfully!');
        setShowScheduleModal(false);
        setNewSchedule({
          job_id: '',
          cron_expression: ''
        });
        setSimpleSchedule({
          type: 'minutes',
          value: 1,
          hour: 9,
          minute: 0,
          dayOfWeek: 1
        });
        setScheduleType('simple');
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
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_active: !currentStatus
        }),
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
                <td>
                  <div>
                    <div style={{fontSize: '14px', fontWeight: 'bold'}}>
                      {cronToReadable(schedule.cron_expression)}
                    </div>
                    <code style={{fontSize: '12px', color: '#666'}}>
                      {schedule.cron_expression}
                    </code>
                  </div>
                </td>
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
                <label>Schedule Type:</label>
                <div className="schedule-type-tabs">
                  <button
                    type="button"
                    className={scheduleType === 'simple' ? 'tab active' : 'tab'}
                    onClick={() => setScheduleType('simple')}
                  >
                    간단 설정
                  </button>
                  <button
                    type="button"
                    className={scheduleType === 'advanced' ? 'tab active' : 'tab'}
                    onClick={() => setScheduleType('advanced')}
                  >
                    고급 설정
                  </button>
                </div>
              </div>

              {scheduleType === 'simple' ? (
                <div className="simple-schedule">
                  <div className="form-group">
                    <label>실행 주기:</label>
                    <select
                      value={simpleSchedule.type}
                      onChange={(e) => setSimpleSchedule({...simpleSchedule, type: e.target.value})}
                    >
                      <option value="minutes">분 단위</option>
                      <option value="hours">시간 단위</option>
                      <option value="daily">매일</option>
                      <option value="weekly">매주</option>
                    </select>
                  </div>

                  {(simpleSchedule.type === 'minutes' || simpleSchedule.type === 'hours') && (
                    <div className="form-group">
                      <label>
                        매 {simpleSchedule.type === 'minutes' ? '분' : '시간'}:
                      </label>
                      <input
                        type="number"
                        min="1"
                        max={simpleSchedule.type === 'minutes' ? 59 : 23}
                        value={simpleSchedule.value}
                        onChange={(e) => setSimpleSchedule({...simpleSchedule, value: parseInt(e.target.value)})}
                      />
                    </div>
                  )}

                  {(simpleSchedule.type === 'daily' || simpleSchedule.type === 'weekly') && (
                    <div className="time-picker">
                      <div className="form-group">
                        <label>시간:</label>
                        <input
                          type="number"
                          min="0"
                          max="23"
                          value={simpleSchedule.hour}
                          onChange={(e) => setSimpleSchedule({...simpleSchedule, hour: parseInt(e.target.value)})}
                        />
                      </div>
                      <div className="form-group">
                        <label>분:</label>
                        <input
                          type="number"
                          min="0"
                          max="59"
                          value={simpleSchedule.minute}
                          onChange={(e) => setSimpleSchedule({...simpleSchedule, minute: parseInt(e.target.value)})}
                        />
                      </div>
                    </div>
                  )}

                  {simpleSchedule.type === 'weekly' && (
                    <div className="form-group">
                      <label>요일:</label>
                      <select
                        value={simpleSchedule.dayOfWeek}
                        onChange={(e) => setSimpleSchedule({...simpleSchedule, dayOfWeek: parseInt(e.target.value)})}
                      >
                        <option value={1}>월요일</option>
                        <option value={2}>화요일</option>
                        <option value={3}>수요일</option>
                        <option value={4}>목요일</option>
                        <option value={5}>금요일</option>
                        <option value={6}>토요일</option>
                        <option value={0}>일요일</option>
                      </select>
                    </div>
                  )}

                  <div className="cron-preview">
                    <strong>생성될 Cron 표현식:</strong> 
                    <code>{convertToCron(simpleSchedule)}</code>
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label>Cron Expression:</label>
                  <input
                    type="text"
                    value={newSchedule.cron_expression}
                    onChange={(e) => setNewSchedule({...newSchedule, cron_expression: e.target.value})}
                    placeholder="0 9 * * * (매일 오전 9시)"
                    required
                  />
                  <small>Format: minute hour day month weekday</small>
                </div>
              )}

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
