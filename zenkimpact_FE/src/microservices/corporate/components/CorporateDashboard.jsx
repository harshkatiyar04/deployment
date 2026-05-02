import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../corporate.css';
import { useCorporateData } from '../hooks/useCorporateData';
import { useBrandColor } from '../hooks/useBrandColor';
import CorpPortfolio from './CorpPortfolio';
import CorpCirclePerf from './CorpCirclePerf';
import CorpEmployees from './CorpEmployees';
import CorpCSRAccount from './CorpCSRAccount';
import CorpCertification from './CorpCertification';
import CorpKiaStrategy from './CorpKiaStrategy';
import { ChatProvider } from '../../../contexts/ChatContext';
import MessageList from '../../../components/chat/MessageList';
import MessageInput from '../../../components/chat/MessageInput';

const TABS = [
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'circles', label: 'Circle performance' },
  { id: 'employees', label: 'Employee engagement' },
  { id: 'impact', label: 'Impact certification' },
  { id: 'csr-account', label: 'CSR account' },
  { id: 'kia', label: 'Kia & strategy' },
];

const FY_OPTIONS = ['2025-26', '2024-25'];

const KIA_QUICK_CHIPS = [
  "ZenQ improvement tips",
  "CSR budget analysis",
  "Circle recommendations",
  "Impact report summary",
  "Allocation strategy",
  "Compare circles",
];

/* ── Kia Chat Panel (right sidebar) ─────────────────────────────────────── */
function KiaChatPanel() {
  const [panelWidth, setPanelWidth] = useState(() => {
    const saved = localStorage.getItem('corp_kia_width');
    return saved ? parseInt(saved, 10) : 380;
  });
  const isResizing = useRef(false);

  useEffect(() => {
    localStorage.setItem('corp_kia_width', panelWidth);
  }, [panelWidth]);

  const handleMouseDown = useCallback(() => {
    isResizing.current = true;
    document.body.style.cursor = 'ew-resize';
    const onMove = (e) => {
      if (!isResizing.current) return;
      const w = document.body.clientWidth - e.clientX;
      if (w > 280 && w < 600) setPanelWidth(w);
    };
    const onUp = () => {
      isResizing.current = false;
      document.body.style.cursor = 'auto';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, []);

  return (
    <div className="corp-kia-panel" style={{ width: panelWidth, minWidth: panelWidth }}>
      {/* Resize handle */}
      <div
        style={{ position: 'absolute', left: -3, top: 0, bottom: 0, width: 6, cursor: 'ew-resize', zIndex: 100 }}
        onMouseDown={handleMouseDown}
      />
      {/* Header */}
      <div className="corp-kia-header">
        <div className="corp-kia-dot" />
        <span className="corp-kia-title">Chat & Kia</span>
        <svg style={{ marginLeft: 'auto', color: '#F0A500' }} width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l2.09 6.26L20 9.27l-4.27 3.7 1.64 6.03L12 15.77 6.63 19l1.64-6.03L4 9.27l5.91-1.01L12 2z" />
        </svg>
      </div>

      {/* Kia avatar section */}
      <div className="corp-kia-avatar-section">
        <div className="corp-kia-avatar-circle">
          <img src="/kia-bot-avatar.png" alt="Kia" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Kia AI Copilot</div>
          <div style={{ fontSize: 11, color: '#888' }}>Your CSR strategy assistant</div>
        </div>
      </div>

      {/* Quick chips */}
      <div className="corp-kia-chips">
        {KIA_QUICK_CHIPS.map(chip => (
          <button key={chip} className="corp-kia-chip">{chip}</button>
        ))}
      </div>

      {/* Chat area */}
      <div className="corp-kia-chat-area">
        <ChatProvider circleId="corporate-kia" userRole="corporate">
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', background: '#fff' }}>
            <MessageList userPersona="corporate" />
          </div>
          <div style={{ padding: '10px 12px', borderTop: '1px solid #e8e8e4', background: '#fff' }}>
            <MessageInput userPersona="corporate" />
          </div>
        </ChatProvider>
      </div>
    </div>
  );
}

export default function CorporateDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(() => {
    return sessionStorage.getItem('corp_dashboard_tab') || 'portfolio';
  });

  useEffect(() => {
    sessionStorage.setItem('corp_dashboard_tab', activeTab);
  }, [activeTab]);

  const [fy, setFy] = useState('2025-26');
  const { 
    profile, zenqOverview, allocations, circlesPerf, employees, csrAccount, 
    strategyBrief, peerBenchmarks, goals,
    loading, error, refresh, reallocate 
  } = useCorporateData(fy);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('zenk_token');
    navigate('/login');
  };

  const company = profile?.company_name || 'TCS Foundation';
  const fullName = profile?.company_name || 'Tata Consultancy Services Foundation';
  const initials = profile?.company_initials || 'TCS';

  const getCompanyLogoUrl = (name) => {
    if (!name) return null;
    const lowerName = name.toLowerCase();

    let domain = 'example.com';
    if (lowerName.includes('tata consultancy') || lowerName.includes('tcs')) {
      domain = 'tcs.com';
    } else if (lowerName.includes('hcl')) {
      domain = 'hcltech.com';
    } else if (lowerName.includes('icici')) {
      domain = 'icicibank.com';
    } else {
      const firstWord = lowerName.split(' ')[0].replace(/[^a-z0-9]/g, '');
      domain = `${firstWord}.com`;
    }

    return `https://icon.horse/icon/${domain}`;
  };

  const logoUrl = getCompanyLogoUrl(fullName);
  const currentTheme = useBrandColor(logoUrl);

  if (error) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: '#f4f4f0', flexDirection: 'column', gap: 16,
        fontFamily: 'Inter, sans-serif',
      }}>
        <div style={{ fontSize: 36, color: '#F0A500' }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#1a1a1a' }}>Session expired or unauthorized</div>
        <div style={{ fontSize: 13, color: '#888' }}>{error}</div>
        <button onClick={() => navigate('/login')} style={{
          background: '#4A72F5', color: '#fff', border: 'none', padding: '10px 24px',
          borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontFamily: 'Inter, sans-serif', fontSize: 14,
        }}>Back to Login</button>
      </div>
    );
  }

  const bannerStyle = {
    '--b-start': currentTheme.start,
    '--b-mid': currentTheme.mid,
    '--b-end': currentTheme.end,
    '--b-shadow': currentTheme.shadow
  };

  const handleLogoError = (e) => {
    // If icon.horse fails or returns an empty icon, fallback to ui-avatars
    e.target.onerror = null; // prevent infinite loop
    e.target.src = `https://ui-avatars.com/api/?name=${initials}&background=4A72F5&color=fff&size=128&rounded=true&bold=true`;
  };

  return (
    <div className="corp-root">
      <div className="corp-shell">
        {/* ── Top Header ──────────────────────────────────────────── */}
        <header className="corp-header">
          <div className="corp-logo-wrap">
            <img src="/assets/zenk-logo.png" alt="ZenK" style={{ height: 28, objectFit: 'contain' }} />
            <div className="corp-logo-divider" />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: profile?.brand_color || '#1a1a1a' }}>{company}</div>
              <div className="corp-header-subtitle">Corporate CSR Dashboard</div>
            </div>
          </div>

          <div className="corp-header-spacer" />

          <select className="corp-fy-selector" value={fy} onChange={e => { setFy(e.target.value); refresh(e.target.value); }}>
            {FY_OPTIONS.map(f => <option key={f} value={f}>FY {f}</option>)}
          </select>

          <div className="corp-user-chip" onClick={handleLogout} title="Sign out">
            <div className="corp-avatar">{initials.slice(0, 2)}</div>
            <div>
              <div className="corp-user-name">{profile?.authorized_signatory_name || 'Vikram Patil'}</div>
              <div className="corp-user-role">CSR Lead</div>
            </div>
          </div>
        </header>

        {/* ── Company Banner ───────────────────────────────────────── */}
        <div className="corp-banner" style={bannerStyle}>
          <div className="corp-banner-inner">
            <div className="corp-banner-top">
              <div style={{ position: 'relative' }}>
                <img
                  crossOrigin="anonymous"
                  src={getCompanyLogoUrl(fullName)}
                  alt={initials}
                  className="corp-company-logo"
                  style={{ objectFit: 'contain', backgroundColor: '#fff', borderRadius: '8px' }}
                  onError={handleLogoError}
                />
              </div>
              <div style={{ flex: 1 }}>
                <div className="corp-company-name">
                  {fullName}
                  {profile?.badges?.map((b, i) => (
                    <span key={i} className={`corp-badge ${b.color}`} style={{ marginLeft: 10 }}>
                      {b.color === 'gold' ? (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                      ) : (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                      )}
                      {b.label}
                    </span>
                  ))}
                </div>
                <div className="corp-company-meta">
                  <span>{profile?.corporate_id}</span>
                  <span>{profile?.hq_city}</span>
                  <span>Partner since {profile?.partner_since}</span>
                  <span>{profile?.csr_schedule}</span>
                </div>
              </div>
            </div>

            {/* KPI Strip */}
            {profile && (
              <div className="corp-kpi-strip">
                <div className="corp-kpi-item"><div className="corp-kpi-label">Corporate ZenQ</div><div className="corp-kpi-value blue">{profile.corporate_zenq}</div></div>
                <div className="corp-kpi-item"><div className="corp-kpi-label">Total CSR Deployed</div><div className="corp-kpi-value">₹{(profile.total_csr_deployed || 0).toLocaleString('en-IN')}</div></div>
                <div className="corp-kpi-item"><div className="corp-kpi-label">Circles Funded</div><div className="corp-kpi-value">{profile.circles_funded}</div></div>
                <div className="corp-kpi-item"><div className="corp-kpi-label">Employees Engaged</div><div className="corp-kpi-value">{profile.employees_engaged}</div></div>
                <div className="corp-kpi-item"><div className="corp-kpi-label">Unallocated</div><div className="corp-kpi-value red">₹{(profile.unallocated || 0).toLocaleString('en-IN')}</div></div>
              </div>
            )}
          </div>
        </div>

        {/* ── Tab Bar ──────────────────────────────────────────────── */}
        <nav className="corp-tabs">
          {TABS.map(t => (
            <button key={t.id} className={`corp-tab-btn ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>

        {/* ── Content ──────────────────────────────────────────────── */}
        <div className="corp-content">
          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[80, 320, 240].map((h, i) => <div key={i} className="c-skeleton" style={{ height: h }} />)}
            </div>
          )}

          {!loading && activeTab === 'portfolio' && (
            <CorpPortfolio profile={profile} zenqOverview={zenqOverview} allocations={allocations} onReallocate={reallocate} onNavigate={setActiveTab} />
          )}
          {!loading && activeTab === 'circles' && <CorpCirclePerf circlesPerf={circlesPerf} reallocate={reallocate} unallocatedBalance={profile?.unallocated || 0} />}
          {!loading && activeTab === 'employees' && <CorpEmployees employees={employees} onNavigate={setActiveTab} />}
          {!loading && activeTab === 'csr-account' && <CorpCSRAccount csrAccount={csrAccount} onRefresh={() => refresh(fy)} />}

          {!loading && activeTab === 'impact' && <CorpCertification profile={profile} />}
          {!loading && activeTab === 'kia' && (
            <CorpKiaStrategy 
              profile={profile} 
              strategyBrief={strategyBrief} 
              peerBenchmarks={peerBenchmarks} 
              goals={goals} 
              circlesPerf={circlesPerf}
              onRefresh={() => refresh(fy)} 
            />
          )}
        </div>

        {/* ── Footer ───────────────────────────────────────────────── */}
        <footer className="corp-footer">
          <span>ZENK</span>
          <span>Corporate CSR Dashboard</span>
          <span>{company}</span>
          <span>AI-powered impact platform</span>
        </footer>
      </div>

      {/* ── Kia Chat Sidebar (always visible like sponsor-circle) ──── */}
      <KiaChatPanel />
    </div>
  );
}
