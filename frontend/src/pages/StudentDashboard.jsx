import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar as CalendarIcon, LogOut, Utensils, AlertCircle, ChevronLeft, ChevronRight, Lock, Edit2, X, Check, Key } from 'lucide-react';
import api from '../api';

export default function StudentDashboard() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [monthlyAttendance, setMonthlyAttendance] = useState({});
  const [fines, setFines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [showPasswordTab, setShowPasswordTab] = useState(false);
  
  const [selectedEditDate, setSelectedEditDate] = useState(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardData();
  }, [currentMonth]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');
    try {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth() + 1;
      
      const [attRes, finesRes] = await Promise.all([
        api.get(`/student/attendance/month/${year}/${month}`),
        api.get('/student/fines')
      ]);
      
      const attMap = {};
      attRes.data.forEach(a => {
        attMap[a.target_date] = a;
      });
      
      setMonthlyAttendance(attMap);
      setFines(finesRes.data);
      setSelectedEditDate(null);
    } catch (err) {
      if (err.response?.status === 401) {
        navigate('/login');
      } else {
        setError('Failed to fetch data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickMark = async (dateStr, isPresent) => {
    try {
      const newAtt = {
        breakfast: isPresent,
        lunch: isPresent,
        dinner: isPresent
      };
      const res = await api.post(`/student/attendance/${dateStr}`, newAtt);
      setMonthlyAttendance(prev => ({ ...prev, [dateStr]: res.data }));
      if (selectedEditDate === dateStr) setSelectedEditDate(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update attendance');
    }
  };

  const handleMealToggle = async (dateStr, mealType) => {
    const currentAtt = monthlyAttendance[dateStr] || { breakfast: false, lunch: false, dinner: false, is_locked: false };
    if (currentAtt.is_locked) return;
    
    const newAtt = {
      breakfast: currentAtt.breakfast,
      lunch: currentAtt.lunch,
      dinner: currentAtt.dinner,
      [mealType]: !currentAtt[mealType]
    };
    
    try {
      const res = await api.post(`/student/attendance/${dateStr}`, newAtt);
      setMonthlyAttendance(prev => ({ ...prev, [dateStr]: res.data }));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update attendance');
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordMessage('');
    try {
      await api.post('/student/change-password', { 
        old_password: oldPassword, 
        new_password: newPassword 
      });
      setPasswordMessage('Password updated successfully!');
      setOldPassword('');
      setNewPassword('');
    } catch (err) {
      setPasswordMessage(err.response?.data?.detail || 'Failed to update password');
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const nextMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  const prevMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));

  const totalFines = fines.reduce((acc, f) => acc + f.amount, 0);

  const renderCalendar = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDay = new Date(year, month, 1).getDay();
    
    const cells = [];
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    days.forEach(d => cells.push(<div key={`header-${d}`} className="calendar-header">{d}</div>));
    
    for (let i = 0; i < firstDay; i++) {
      cells.push(<div key={`empty-${i}`} className="calendar-cell" style={{ border: 'none', background: 'transparent' }}></div>);
    }
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = new Date(today.getTime() - (today.getTimezoneOffset() * 60000)).toISOString().split('T')[0];

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const att = monthlyAttendance[dateStr];
      
      const targetDate = new Date(year, month, d);
      targetDate.setHours(0, 0, 0, 0);
      const diffDays = Math.ceil((targetDate - today) / (1000 * 60 * 60 * 24));
      const isLocked = (att && att.is_locked) || (diffDays <= 2);
      
      const isSelected = selectedEditDate === dateStr;
      
      const isFullyPresent = att && att.breakfast && att.lunch && att.dinner;
      const isFullyAbsent = att && !att.breakfast && !att.lunch && !att.dinner;
      
      let borderColor = '';
      if (att && (att.breakfast || att.lunch || att.dinner)) borderColor = 'var(--success-color)';
      else if (isFullyAbsent) borderColor = 'var(--danger-color)';

      cells.push(
        <div 
          key={dateStr} 
          className={`calendar-cell ${isSelected ? 'active' : ''}`}
          style={{ 
            borderColor: borderColor || 'var(--glass-border)', 
            opacity: isLocked ? 0.6 : 1,
            background: isLocked ? 'rgba(0, 0, 0, 0.3)' : ''
          }}
        >
          <div className="calendar-cell-date" style={{ color: dateStr === todayStr ? 'var(--primary-color)' : (isLocked ? 'var(--text-secondary)' : '') }}>
            {isLocked && <Lock size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }}/>}
            {d}
          </div>
          
          <div className="calendar-btn-group">
            <button 
              className={`cal-btn absent ${isFullyAbsent ? 'selected' : ''}`}
              onClick={() => handleQuickMark(dateStr, false)}
              disabled={isLocked}
              title="Absent all day"
            ><X size={14} /></button>
            <button 
              className={`cal-btn present ${isFullyPresent ? 'selected' : ''}`}
              onClick={() => handleQuickMark(dateStr, true)}
              disabled={isLocked}
              title="Present all day"
            ><Check size={14} /></button>
            <button 
              className={`cal-btn edit ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedEditDate(isSelected ? null : dateStr)}
              title={isLocked ? "View lock status" : "Edit meals"}
            ><Edit2 size={14} /></button>
          </div>
        </div>
      );
    }
    
    return cells;
  };

  return (
    <div className="container" style={{ paddingBottom: '4rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Student Dashboard</h2>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button onClick={() => setShowPasswordTab(!showPasswordTab)} className="btn" style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            <Key size={20} style={{ marginRight: '8px' }} /> Change Password
          </button>
          <button onClick={logout} className="btn" style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            <LogOut size={20} style={{ marginRight: '8px' }} /> Logout
          </button>
        </div>
      </header>
      
      {showPasswordTab && (
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', animation: 'fadeIn 0.3s ease' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3>Change Password</h3>
            <button onClick={() => setShowPasswordTab(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <X size={24} />
            </button>
          </div>
          
          {passwordMessage && (
            <p style={{ color: passwordMessage.includes('success') ? 'var(--success-color)' : 'var(--danger-color)', marginBottom: '1rem', fontWeight: 'bold' }}>
              {passwordMessage}
            </p>
          )}
          <form onSubmit={handleChangePassword} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="input-group" style={{ marginBottom: 0, flex: 1, minWidth: '200px' }}>
              <label className="input-label">Old Password</label>
              <input 
                type="password" 
                className="glass-input" 
                placeholder="Current Password" 
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required 
              />
            </div>
            <div className="input-group" style={{ marginBottom: 0, flex: 1, minWidth: '200px' }}>
              <label className="input-label">New Password</label>
              <input 
                type="password" 
                className="glass-input" 
                placeholder="New Password" 
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required 
              />
            </div>
            <button type="submit" className="btn btn-primary" style={{ padding: '0.75rem 2rem' }}>Update</button>
          </form>
        </div>
      )}
      
      {error && (
        <div style={{ backgroundColor: 'var(--danger-color)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem', color: 'white', display: 'flex', alignItems: 'center' }}>
          <AlertCircle style={{ marginRight: '10px' }} /> {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
        
        {/* Calendar Card */}
        <div className="glass-panel" style={{ padding: '2rem', gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <CalendarIcon style={{ marginRight: '10px', color: 'var(--primary-color)' }} />
              <h3>Meal Calendar</h3>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <button onClick={prevMonth} className="btn" style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)' }}><ChevronLeft size={20}/></button>
              <span style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                {currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}
              </span>
              <button onClick={nextMonth} className="btn" style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)' }}><ChevronRight size={20}/></button>
            </div>
          </div>
          
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem' }}>Loading calendar...</div>
          ) : (
            <>
              <div className="calendar-wrapper">
                <div className="calendar-grid">
                  {renderCalendar()}
                </div>
              </div>
              
              {/* Inline Edit Panel */}
              {selectedEditDate && (
                <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: '1px solid var(--primary-color)' }}>
                  <h4 style={{ marginBottom: '1rem' }}>Editing Meals for: <span style={{ color: 'var(--primary-color)' }}>{selectedEditDate}</span></h4>
                  
                  {(() => {
                    const [y, m, d] = selectedEditDate.split('-');
                    const target = new Date(y, m - 1, d);
                    const todayDate = new Date();
                    todayDate.setHours(0, 0, 0, 0);
                    const diff = Math.ceil((target - todayDate) / (1000 * 60 * 60 * 24));
                    const isDateLocked = (monthlyAttendance[selectedEditDate]?.is_locked) || (diff <= 2);
                    
                    if (isDateLocked) {
                      const cutoff = new Date(todayDate);
                      cutoff.setDate(todayDate.getDate() + 3);
                      const cutoffStr = cutoff.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
                      return <p style={{ color: 'var(--danger-color)', fontWeight: 'bold' }}>You cannot edit dates before {cutoffStr}.</p>;
                    }
                    
                    return (
                      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        {['breakfast', 'lunch', 'dinner'].map((meal) => {
                          const currentAtt = monthlyAttendance[selectedEditDate] || {};
                          return (
                            <label 
                              key={meal} 
                              className="glass-card"
                              style={{ 
                                display: 'flex', alignItems: 'center', padding: '1rem', cursor: 'pointer', flex: 1, minWidth: '150px',
                                border: currentAtt[meal] ? '1px solid var(--primary-color)' : ''
                              }}
                            >
                              <input 
                                type="checkbox" 
                                checked={currentAtt[meal] || false}
                                onChange={() => handleMealToggle(selectedEditDate, meal)}
                                style={{ width: '20px', height: '20px', marginRight: '15px' }}
                              />
                              <span style={{ textTransform: 'capitalize', fontSize: '1.1rem' }}>{meal}</span>
                            </label>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              )}
            </>
          )}
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Fines Card */}
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3>Pending Fines</h3>
              <span style={{ background: 'var(--danger-color)', color: 'white', padding: '4px 12px', borderRadius: '20px', fontWeight: 'bold' }}>
                ₹{totalFines}
              </span>
            </div>
            
            {fines.length > 0 ? (
              <ul style={{ listStyle: 'none', maxHeight: '200px', overflowY: 'auto' }}>
                {fines.map(fine => (
                  <li key={fine.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem 0', borderBottom: '1px solid var(--glass-border)' }}>
                    <span>{fine.date}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{fine.description}</span>
                    <span style={{ color: 'var(--danger-color)', fontWeight: 'bold' }}>₹{fine.amount}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>No fines! Great job marking attendance on time.</p>
            )}
          </div>

        </div>
        
      </div>
    </div>
  );
}
