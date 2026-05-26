import React, { useState, useEffect } from 'react';
import { Monitor, Smartphone, Maximize } from 'lucide-react';

export default function ViewToggle() {
  const [view, setView] = useState('responsive'); // 'responsive', 'desktop', 'mobile'

  useEffect(() => {
    const metaViewport = document.querySelector('meta[name="viewport"]');
    
    if (view === 'desktop') {
      // Force desktop on mobile by setting viewport width
      if (metaViewport) metaViewport.setAttribute('content', 'width=1200');
      document.body.classList.remove('force-mobile');
    } else if (view === 'mobile') {
      // Force mobile on desktop via CSS wrapper
      if (metaViewport) metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0');
      document.body.classList.add('force-mobile');
    } else {
      // Default responsive
      if (metaViewport) metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0');
      document.body.classList.remove('force-mobile');
    }
  }, [view]);

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      display: 'flex',
      gap: '0.25rem',
      background: 'rgba(30, 41, 59, 0.9)',
      padding: '0.5rem',
      borderRadius: '2rem',
      border: '1px solid rgba(255,255,255,0.1)',
      boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
      zIndex: 9999,
      backdropFilter: 'blur(10px)'
    }}>
      <button 
        onClick={() => setView('responsive')}
        style={{
          background: view === 'responsive' ? 'var(--primary-color)' : 'transparent',
          border: 'none', color: 'white', padding: '0.5rem', borderRadius: '50%', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}
        title="Responsive View (Default)"
      >
        <Maximize size={18} />
      </button>
      <button 
        onClick={() => setView('desktop')}
        style={{
          background: view === 'desktop' ? 'var(--primary-color)' : 'transparent',
          border: 'none', color: 'white', padding: '0.5rem', borderRadius: '50%', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}
        title="Force Desktop View"
      >
        <Monitor size={18} />
      </button>
      <button 
        onClick={() => setView('mobile')}
        style={{
          background: view === 'mobile' ? 'var(--primary-color)' : 'transparent',
          border: 'none', color: 'white', padding: '0.5rem', borderRadius: '50%', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}
        title="Force Mobile View"
      >
        <Smartphone size={18} />
      </button>
    </div>
  );
}
