import React, { useState, useEffect } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

function Users() {
  const [users, setUsers] = useState([]);
  const [systemUsers, setSystemUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/users`);
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const fetchSystemUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/system-users`);
      const data = await response.json();
      setSystemUsers(data);
    } catch (error) {
      console.error('Error fetching system users:', error);
      alert('Failed to fetch system users');
    } finally {
      setLoading(false);
    }
  };

  const syncUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/users/sync`, {
        method: 'POST'
      });
      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        fetchUsers(); // DB 사용자 목록 새로고침
      } else {
        alert('Sync failed: ' + result.detail);
      }
    } catch (error) {
      console.error('Error syncing users:', error);
      alert('Sync failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="users-page">
      <div className="section-header">
        <h2>User Management</h2>
        <div className="user-actions">
          <button 
            className="btn btn-secondary" 
            onClick={fetchSystemUsers}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Scan System Users'}
          </button>
          <button 
            className="btn btn-primary" 
            onClick={syncUsers}
            disabled={loading}
          >
            {loading ? 'Syncing...' : 'Sync to Database'}
          </button>
        </div>
      </div>

      <div className="users-grid">
        {/* DB Users */}
        <div className="user-section">
          <h3>Database Users ({users.length})</h3>
          <div className="user-table-container">
            <table className="user-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.user_id}>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* System Users */}
        {systemUsers.length > 0 && (
          <div className="user-section">
            <h3>System Users ({systemUsers.length})</h3>
            <div className="user-table-container">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>UID</th>
                    <th>Home Directory</th>
                    <th>Shell</th>
                  </tr>
                </thead>
                <tbody>
                  {systemUsers.map(user => (
                    <tr key={user.uid}>
                      <td>{user.username}</td>
                      <td>{user.uid}</td>
                      <td>{user.home_dir}</td>
                      <td>{user.shell}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Users;
