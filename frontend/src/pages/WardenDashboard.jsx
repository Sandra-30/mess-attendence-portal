import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Upload, Users, Image as ImageIcon, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import api from '../api';

export default function WardenDashboard() {
  const [activeTab, setActiveTab] = useState('whitelist');
  const [whitelistForm, setWhitelistForm] = useState({ name: '', email: '', room_number: '' });
  const [whitelistEntries, setWhitelistEntries] = useState([]);

  const [headcountDate, setHeadcountDate] = useState(new Date().toISOString().split('T')[0]);
  const [headcounts, setHeadcounts] = useState(null);

  const [billingMatrix, setBillingMatrix] = useState(null);
  const [billingMonth, setBillingMonth] = useState(new Date().getMonth() + 1);
  const [billingYear, setBillingYear] = useState(new Date().getFullYear());

  const [message, setMessage] = useState({ type: '', text: '' });
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleWhitelistSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/warden/whitelist', whitelistForm);
      setMessage({ type: 'success', text: 'Student added to list successfully.' });
      setWhitelistForm({ name: '', email: '', room_number: '' });
      fetchWhitelist();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to add student.' });
    }
  };

  const handleResetPassword = async (email) => {
    if (!window.confirm(`Are you sure you want to reset the password for ${email}?`)) return;
    try {
      await api.post(`/warden/reset-student-password/${email}`);
      setMessage({ type: 'success', text: `Password for ${email} has been reset to default.` });
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to reset password.' });
    }
  };

  const fetchHeadcounts = async () => {
    try {
      const res = await api.get(`/warden/headcounts?target_date=${headcountDate}`);
      setHeadcounts(res.data);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to fetch headcounts.' });
    }
  };

  const fetchBillingMatrix = async () => {
    try {
      const res = await api.get(`/warden/billing-matrix?month=${billingMonth}&year=${billingYear}`);
      setBillingMatrix(res.data);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to fetch billing matrix.' });
    }
  };

  const fetchWhitelist = async () => {
    try {
      const res = await api.get('/warden/whitelist');
      setWhitelistEntries(res.data);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to fetch list.' });
    }
  };

  useEffect(() => {
    if (activeTab === 'whitelist') fetchWhitelist();
    if (activeTab === 'headcounts') fetchHeadcounts();
    if (activeTab === 'billing') fetchBillingMatrix();
  }, [activeTab, headcountDate, billingMonth, billingYear]);

  return (
    <div className="container">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Warden Dashboard</h2>
        <button onClick={logout} className="btn" style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
          <LogOut size={20} style={{ marginRight: '8px' }} /> Logout
        </button>
      </header>

      {message.text && (
        <div style={{
          backgroundColor: message.type === 'success' ? 'var(--success-color)' : 'var(--danger-color)',
          padding: '1rem', borderRadius: '8px', marginBottom: '2rem', color: 'white', display: 'flex', alignItems: 'center'
        }}>
          {message.type === 'success' ? <CheckCircle style={{ marginRight: '10px' }} /> : <AlertCircle style={{ marginRight: '10px' }} />}
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
        {['whitelist', 'headcounts', 'billing'].map(tab => (
          <button
            key={tab}
            className="btn"
            style={{
              background: activeTab === tab ? 'var(--primary-color)' : 'rgba(255,255,255,0.1)',
              color: 'white'
            }}
            onClick={() => { setActiveTab(tab); setMessage({ type: '', text: '' }); }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="glass-panel" style={{ padding: '2rem' }}>
        {/* Whitelist Tab */}
        {activeTab === 'whitelist' && (
          <div>
            <h3><Users size={24} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px', color: 'var(--primary-color)' }} /> Inmate Data</h3>
            <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>Details of alloted inmates.</p>

            <form onSubmit={handleWhitelistSubmit} style={{ maxWidth: '500px' }}>
              <div className="input-group">
                <label className="input-label">Student Name</label>
                <input type="text" className="glass-input" value={whitelistForm.name} onChange={e => setWhitelistForm({ ...whitelistForm, name: e.target.value })} required />
              </div>
              <div className="input-group">
                <label className="input-label">Student Email</label>
                <input type="email" className="glass-input" value={whitelistForm.email} onChange={e => setWhitelistForm({ ...whitelistForm, email: e.target.value })} required />
              </div>
              <div className="input-group">
                <label className="input-label">Room Number</label>
                <input type="text" className="glass-input" value={whitelistForm.room_number} onChange={e => setWhitelistForm({ ...whitelistForm, room_number: e.target.value })} required />
              </div>
              <button type="submit" className="btn btn-primary"> Add </button>
            </form>

            <h4 style={{ marginTop: '3rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>Current Inmates</h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '1rem' }}>Name</th>
                    <th style={{ padding: '1rem' }}>Email</th>
                    <th style={{ padding: '1rem' }}>Room</th>
                    <th style={{ padding: '1rem' }}>Reset Password</th>
                  </tr>
                </thead>
                <tbody>
                  {whitelistEntries.map(entry => (
                    <tr key={entry.id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem' }}>{entry.name}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{entry.email}</td>
                      <td style={{ padding: '1rem' }}>{entry.room_number}</td>
                      <td style={{ padding: '1rem' }}>
                        <button
                          onClick={() => handleResetPassword(entry.email)}
                          className="btn"
                          style={{ padding: '4px 8px', fontSize: '0.8rem', background: 'var(--warning-color)', color: 'white' }}
                          title="Reset Password to Default"
                        >
                          <RefreshCw size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Reset Pwd
                        </button>
                      </td>
                    </tr>
                  ))}
                  {whitelistEntries.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No students in list yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Headcounts Tab */}
        {activeTab === 'headcounts' && (
          <div>
            <h3>Daily Count</h3>
            <div className="input-group" style={{ maxWidth: '300px', marginTop: '1rem' }}>
              <label className="input-label">Select Date</label>
              <input type="date" className="glass-input" value={headcountDate} onChange={e => setHeadcountDate(e.target.value)} />
            </div>

            {headcounts && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', marginTop: '2rem' }}>
                <div className="glass-card" style={{ padding: '2rem', flex: 1, textAlign: 'center' }}>
                  <h4 style={{ color: 'var(--text-secondary)' }}>Breakfast</h4>
                  <div style={{ fontSize: '3rem', fontWeight: 'bold' }}>{headcounts.breakfast}</div>
                </div>
                <div className="glass-card" style={{ padding: '2rem', flex: 1, textAlign: 'center' }}>
                  <h4 style={{ color: 'var(--text-secondary)' }}>Lunch</h4>
                  <div style={{ fontSize: '3rem', fontWeight: 'bold' }}>{headcounts.lunch}</div>
                </div>
                <div className="glass-card" style={{ padding: '2rem', flex: 1, textAlign: 'center' }}>
                  <h4 style={{ color: 'var(--text-secondary)' }}>Dinner</h4>
                  <div style={{ fontSize: '3rem', fontWeight: 'bold' }}>{headcounts.dinner}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Billing Tab */}
        {activeTab === 'billing' && billingMatrix && (
          <div>
            <h3>Billing Data</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '1rem', marginBottom: '2rem' }}>
              <div className="input-group" style={{ margin: 0 }}>
                <label className="input-label">Month</label>
                <input type="number" min="1" max="12" className="glass-input" style={{ width: '100px' }} value={billingMonth} onChange={e => setBillingMonth(e.target.value)} />
              </div>
              <div className="input-group" style={{ margin: 0 }}>
                <label className="input-label">Year</label>
                <input type="number" min="2000" max="2100" className="glass-input" style={{ width: '120px' }} value={billingYear} onChange={e => setBillingYear(e.target.value)} />
              </div>
            </div>

            <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ color: 'var(--text-secondary)' }}>Total Hostel Days Accumulated</div>
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{billingMatrix.total_hostel_days} days</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ color: 'var(--text-secondary)' }}>Total Registered Students</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{billingMatrix.student_matrix.length}</div>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '1rem' }}>Name</th>
                    <th style={{ padding: '1rem' }}>Email</th>
                    <th style={{ padding: '1rem' }}>Room</th>
                    <th style={{ padding: '1rem' }}>Days Present</th>
                    <th style={{ padding: '1rem' }}>Total Fines (₹)</th>
                  </tr>
                </thead>
                <tbody>
                  {billingMatrix.student_matrix.map(student => (
                    <tr key={student.student_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem' }}>{student.name}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{student.email}</td>
                      <td style={{ padding: '1rem' }}>{student.room_number}</td>
                      <td style={{ padding: '1rem', fontWeight: 'bold' }}>{student.days_present}</td>
                      <td style={{ padding: '1rem', color: 'var(--danger-color)', fontWeight: 'bold' }}>{student.total_fines}</td>
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
