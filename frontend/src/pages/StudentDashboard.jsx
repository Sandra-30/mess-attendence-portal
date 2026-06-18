import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar as CalendarIcon, LogOut, Utensils, AlertCircle, ChevronLeft, ChevronRight, Lock, Edit2, X, Check, Key, Bell } from 'lucide-react';
import api from '../api';
import ThemeToggle from '../components/ThemeToggle';

export default function StudentDashboard() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [monthlyAttendance, setMonthlyAttendance] = useState({});
  const [fines, setFines] = useState([]);
  const [monthlyBill, setMonthlyBill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [showPasswordTab, setShowPasswordTab] = useState(false);
  
  const [selectedEditDate, setSelectedEditDate] = useState(null);
  const [studentName, setStudentName] = useState('');
  const [studentRoom, setStudentRoom] = useState('');
  const [studentEmail, setStudentEmail] = useState('');
  
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [holidays, setHolidays] = useState([]);
  
  const [activeTab, setActiveTab] = useState('dashboard');
  const [rosterDate, setRosterDate] = useState(new Date().toISOString().split('T')[0]);
  const [rosterData, setRosterData] = useState([]);
  const [rosterLoading, setRosterLoading] = useState(false);

  const [billingMatrix, setBillingMatrix] = useState(null);
  const [billingMonth, setBillingMonth] = useState(new Date().getMonth() + 1);
  const [billingYear, setBillingYear] = useState(new Date().getFullYear());
  const [billingLoading, setBillingLoading] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    // Extract name from JWT token
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.name) {
          setStudentName(payload.name);
        }
        if (payload.room_number) {
          setStudentRoom(payload.room_number);
        }
        if (payload.sub) {
          setStudentEmail(payload.sub);
        }
      } catch (err) {}
    }
    fetchDashboardData();
    fetchHolidays();
  }, [currentMonth]);

  useEffect(() => {
    if (activeTab === 'attendance') {
      fetchRosterData();
    } else if (activeTab === 'billing') {
      fetchBillingMatrix();
    }
  }, [activeTab, rosterDate, billingMonth, billingYear]);

  const fetchBillingMatrix = async () => {
    setBillingLoading(true);
    try {
      const res = await api.get(`/student/billing-matrix?month=${billingMonth}&year=${billingYear}`);
      const data = res.data;
      if (data && data.student_matrix) {
        data.student_matrix.sort((a, b) => {
          const roomA = String(a.room_number || '');
          const roomB = String(b.room_number || '');
          return roomA.localeCompare(roomB, undefined, { numeric: true, sensitivity: 'base' });
        });
      }
      setBillingMatrix(data);
    } catch (err) {
      setError('Failed to fetch billing matrix.');
    } finally {
      setBillingLoading(false);
    }
  };

  const fetchRosterData = async () => {
    setRosterLoading(true);
    try {
      const res = await api.get(`/student/daily-attendance?target_date=${rosterDate}`);
      setRosterData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRosterLoading(false);
    }
  };

  const fetchHolidays = async () => {
    try {
      const res = await api.get('/student/holidays');
      setHolidays(res.data.map(h => h.date));
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');
    try {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth() + 1;
      
      const [attRes, finesRes, notifRes, billRes] = await Promise.all([
        api.get(`/student/attendance/month/${year}/${month}`),
        api.get('/student/fines'),
        api.get('/student/notifications'),
        api.get(`/student/bill/month/${year}/${month}`)
      ]);
      
      const attMap = {};
      attRes.data.forEach(a => {
        attMap[a.target_date] = a;
      });
      
      setMonthlyAttendance(attMap);
      setFines(finesRes.data);
      setNotifications(notifRes.data);
      setMonthlyBill(billRes.data);
      setSelectedEditDate(null);
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to fetch dashboard data. Please try again later.');
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
      const isHoliday = holidays.includes(dateStr);
      
      let borderColor = '';
      if (isHoliday) borderColor = 'var(--border-color)';
      else if (att && (att.breakfast || att.lunch || att.dinner)) borderColor = 'var(--success-color)';
      else if (isFullyAbsent) borderColor = 'var(--danger-color)';

      cells.push(
        <div 
          key={dateStr} 
          className={`calendar-cell ${isSelected ? 'active' : ''}`}
          style={{ 
            borderColor: borderColor || 'var(--glass-border)', 
            opacity: (isLocked || isHoliday) ? 0.6 : 1,
            background: (isLocked || isHoliday) ? 'rgba(0, 0, 0, 0.3)' : ''
          }}
        >
          <div className="calendar-cell-date" style={{ color: dateStr === todayStr ? 'var(--primary-color)' : ((isLocked || isHoliday) ? 'var(--text-secondary)' : '') }}>
            {isLocked && !isHoliday && <Lock size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }}/>}
            {d}
          </div>
          
          {isHoliday ? (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '10px', fontStyle: 'italic' }}>
              Hostel Closed
            </div>
          ) : (
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
          )}
        </div>
      );
    }
    
    return cells;
  };

  const monthStats = (() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    let cuts = 0;
    
    // Total working days in month (days in month minus holidays in month)
    let holidaysInMonthCount = 0;

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      if (holidays.includes(dateStr)) {
        holidaysInMonthCount++;
        continue; // Skip counting cuts on holidays
      }
      
      const att = monthlyAttendance[dateStr];
      const isFullyAbsent = att && !att.breakfast && !att.lunch && !att.dinner;
      if (isFullyAbsent) {
        cuts++;
      }
    }
    
    return {
      total: daysInMonth - holidaysInMonthCount,
      cuts: cuts,
      present: (daysInMonth - holidaysInMonthCount) - cuts
    };
  })();

  return (
    <div className="container" style={{ paddingBottom: '4rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem', position: 'relative' }}>
        <h2>{studentName ? `Welcome, ${studentName.split(' ')[0]} ${studentRoom ? `(Room: ${studentRoom})` : ''}` : 'Student Dashboard'}</h2>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <ThemeToggle />
          <div style={{ position: 'relative' }}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)} 
              className="btn" 
              style={{ background: 'transparent', color: 'var(--text-secondary)', position: 'relative', padding: '8px' }}
            >
              <Bell size={20} />
              {notifications.filter(n => !n.is_read).length > 0 && (
                <span style={{
                  position: 'absolute', top: '0', right: '0', background: 'var(--danger-color)', color: 'white',
                  borderRadius: '50%', width: '18px', height: '18px', fontSize: '10px', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', fontWeight: 'bold'
                }}>
                  {notifications.filter(n => !n.is_read).length}
                </span>
              )}
            </button>
            {showNotifications && (
              <div className="glass-panel" style={{
                position: 'absolute', top: '100%', right: '0', width: '300px', zIndex: 1000,
                marginTop: '10px', padding: '1rem', maxHeight: '400px', overflowY: 'auto'
              }}>
                <h4 style={{ margin: '0 0 1rem 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>Notifications</h4>
                {notifications.length === 0 ? (
                  <p style={{ color: 'var(--text-secondary)', textAlign: 'center', margin: 0 }}>No notifications</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                    {notifications.map(n => (
                      <div 
                        key={n.id} 
                        onClick={() => !n.is_read && handleReadNotification(n.id)}
                        style={{
                          padding: '0.8rem', borderRadius: '8px', 
                          background: n.is_read ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.15)',
                          cursor: n.is_read ? 'default' : 'pointer',
                          borderLeft: n.is_read ? 'none' : '3px solid var(--primary-color)'
                        }}
                      >
                        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: n.is_read ? 'var(--text-secondary)' : 'white' }}>{n.message}</p>
                        <small style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>{new Date(n.created_at).toLocaleDateString()}</small>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <button onClick={() => setShowPasswordTab(!showPasswordTab)} className="btn" style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            <Key size={20} style={{ marginRight: '8px' }} /> Change Password
          </button>
          <button onClick={logout} className="btn" style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            <LogOut size={20} style={{ marginRight: '8px' }} /> Logout
          </button>
        </div>
      </header>

      <div className="tabs-container" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
        {['dashboard', 'attendance', 'billing'].map(tab => (
          <button
            key={tab}
            className="btn"
            style={{
              background: activeTab === tab ? 'var(--primary-color)' : 'rgba(255,255,255,0.1)',
              color: 'white'
            }}
            onClick={() => { setActiveTab(tab); setError(''); }}
          >
            {tab === 'dashboard' ? 'My Dashboard' : tab === 'attendance' ? 'Daily Attendance' : 'Monthly Bills'}
          </button>
        ))}
      </div>
      
      {activeTab === 'dashboard' && (
        <>
          {/* Monthly Summary Cards */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1, minWidth: '150px' }}>
          <div className="glass-card" style={{ padding: '1.5rem', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Mess Days</h4>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--success-color)' }}>
              {monthStats.present} / {monthStats.total}
            </div>
          </div>
          <div className="glass-card" style={{ padding: '1.5rem', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Mess Cuts</h4>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: monthStats.cuts > 10 ? 'var(--danger-color)' : 'white' }}>
              {monthStats.cuts}
            </div>
          </div>
        </div>

        {monthlyBill && monthlyBill.is_published && (
          <div className="glass-card" style={{ padding: '1.5rem', flex: 2, minWidth: '300px', display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '1.1rem', textAlign: 'center' }}>Mess Bill Details</h4>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem', fontSize: '0.95rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Days Present:</span>
              <span style={{ fontWeight: 'bold' }}>{monthlyBill.days_present} days</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem', fontSize: '0.95rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Per Day Amount:</span>
              <span style={{ fontWeight: 'bold' }}>₹{monthlyBill.per_day_amount.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem', fontSize: '0.95rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Penalties/Fines:</span>
              <span style={{ fontWeight: 'bold', color: 'var(--danger-color)' }}>₹{monthlyBill.penalties.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', fontSize: '0.95rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Rent:</span>
              <span style={{ fontWeight: 'bold' }}>₹310.00</span>
            </div>
            
            <div style={{ height: '1px', background: 'var(--glass-border)', margin: '0.5rem 0 1rem 0' }}></div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>Total Bill:</span>
              <span style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--success-color)' }}>
                ₹{monthlyBill.total_bill.toFixed(2)}
              </span>
            </div>
            
            <div style={{ marginTop: 'auto' }}>
              <a 
                href="https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?saralID=-918004880"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ textAlign: 'center', textDecoration: 'none', display: 'block', width: '100%', padding: '0.75rem', fontWeight: 'bold', fontSize: '1.1rem' }}
              >
                Pay Mess Bill Online
              </a>
            </div>
          </div>
        )}
      </div>

      {monthStats.cuts > 10 && (
        <div className="glass-panel" style={{ 
          padding: '1.5rem', marginBottom: '2rem', border: '1px solid var(--danger-color)', 
          background: 'rgba(255, 59, 48, 0.1)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' 
        }}>
          <AlertCircle size={32} color="var(--danger-color)" style={{ marginBottom: '1rem' }} />
          <h3 style={{ color: 'white', marginBottom: '0.5rem' }}>Maximum Mess Cuts Exceeded</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', maxWidth: '600px' }}>
            You have exceeded the maximum limit of 10 mess cuts for this month ({monthStats.cuts} cuts taken). 
            To avail the financial discount for these extra cuts, you must submit an official request with valid documents to the Warden.
          </p>
          <a 
            href={`https://mail.google.com/mail/?view=cm&fs=1&to=wardenlh@gecskp.ac.in&su=Mess Cut Exception Request - ${studentName} - Room ${studentRoom}&body=Dear Warden,%0D%0A%0D%0AI am requesting an exception for exceeding the 10 mess cut limit for the month of ${currentMonth.toLocaleString('default', { month: 'long' })} ${currentMonth.getFullYear()}. Attached are my supporting documents.%0D%0A%0D%0AThank you,%0D%0A${studentName}&authuser=${studentEmail}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none', background: 'var(--danger-color)' }}
          >
            Email Request to Warden
          </a>
        </div>
      )}

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
              <div className="calendar-grid">
                {renderCalendar()}
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
        
      </>
      )}

      {activeTab === 'attendance' && (
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Daily Attendance Roster</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Select a date to view who is eating in the mess. This maintains complete transparency for all residents.</p>
          
          <div className="input-group" style={{ maxWidth: '300px', marginBottom: '2rem' }}>
            <label className="input-label">Select Date</label>
            <input 
              type="date" 
              className="glass-input" 
              value={rosterDate} 
              onChange={(e) => setRosterDate(e.target.value)} 
            />
          </div>

          {rosterLoading ? (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading roster...</p>
          ) : rosterData.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '1rem' }}>Name</th>
                    <th style={{ padding: '1rem' }}>Room</th>
                    <th style={{ padding: '1rem', textAlign: 'center' }}>Breakfast</th>
                    <th style={{ padding: '1rem', textAlign: 'center' }}>Lunch</th>
                    <th style={{ padding: '1rem', textAlign: 'center' }}>Dinner</th>
                  </tr>
                </thead>
                <tbody>
                  {rosterData.map(student => (
                    <tr key={student.student_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem' }}>{student.name || 'Unknown Student'}</td>
                      <td style={{ padding: '1rem' }}>{student.room_number || 'N/A'}</td>
                      <td style={{ padding: '1rem', textAlign: 'center', color: student.breakfast ? 'var(--success-color)' : 'var(--danger-color)' }}>
                        {student.breakfast ? <Check size={18} /> : <X size={18} />}
                      </td>
                      <td style={{ padding: '1rem', textAlign: 'center', color: student.lunch ? 'var(--success-color)' : 'var(--danger-color)' }}>
                        {student.lunch ? <Check size={18} /> : <X size={18} />}
                      </td>
                      <td style={{ padding: '1rem', textAlign: 'center', color: student.dinner ? 'var(--success-color)' : 'var(--danger-color)' }}>
                        {student.dinner ? <Check size={18} /> : <X size={18} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No data available for this date.</p>
          )}
        </div>
      )}

      {activeTab === 'billing' && (
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Monthly Bills Transparency</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>View the final mess bill calculation for all residents in the hostel.</p>
          
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label className="input-label">Month</label>
              <select className="glass-input" value={billingMonth} onChange={e => setBillingMonth(parseInt(e.target.value))}>
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>{new Date(2000, i).toLocaleString('default', { month: 'long' })}</option>
                ))}
              </select>
            </div>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label className="input-label">Year</label>
              <input type="number" className="glass-input" value={billingYear} onChange={e => setBillingYear(parseInt(e.target.value))} />
            </div>
            
            {billingMatrix && (
              <div style={{ background: 'var(--surface-color)', padding: '0.75rem 1.5rem', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginLeft: 'auto' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Total Students:</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{billingMatrix.student_matrix.length}</span>
                <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 10px' }}></div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Per Day Amount:</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>₹{billingMatrix.per_day_amount.toFixed(2)}</span>
              </div>
            )}
          </div>

          {billingLoading ? (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading billing data...</p>
          ) : billingMatrix && billingMatrix.student_matrix.length > 0 ? (
            <div style={{ overflowX: 'auto', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', background: 'rgba(255,255,255,0.05)' }}>
                    <th style={{ padding: '1rem' }}>Name</th>
                    <th style={{ padding: '1rem' }}>Room</th>
                    <th style={{ padding: '1rem' }}>Days Present</th>
                    <th style={{ padding: '1rem' }}>Total Fines (₹)</th>
                    <th style={{ padding: '1rem' }}>Rent (₹)</th>
                    <th style={{ padding: '1rem' }}>Mess Bill (₹)</th>
                  </tr>
                </thead>
                <tbody>
                  {billingMatrix.student_matrix.map(student => (
                    <tr key={student.student_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem' }}>{student.name}</td>
                      <td style={{ padding: '1rem' }}>{student.room_number}</td>
                      <td style={{ padding: '1rem', fontWeight: 'bold' }}>{student.days_present}</td>
                      <td style={{ padding: '1rem', color: 'var(--danger-color)', fontWeight: 'bold' }}>{student.total_fines}</td>
                      <td style={{ padding: '1rem' }}>310.00</td>
                      <td style={{ padding: '1rem', fontWeight: 'bold' }}>
                        <span style={{ display: 'inline-block', color: student.is_manual_override ? 'var(--warning-color)' : 'inherit' }}>
                          ₹{student.mess_bill ? student.mess_bill.toFixed(2) : '0.00'}
                          {student.is_manual_override && <span style={{ fontSize: '0.7rem', display: 'block' }}>(Overridden)</span>}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
              The bill for this month has not been finalized or published by the warden yet.
            </p>
          )}
        </div>
      )}

    </div>
  );
}
