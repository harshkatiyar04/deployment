import React, { useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Tier Definitions ─────────────────────────────────────────────────────────
const TIERS = [
  {
    id: 'contributor',
    label: 'Contributor',
    range: 'ZenQ 50–64',
    min: 50, max: 64,
    requirements: ['Corporate ZenQ 50+', 'Min 1 circle funded', 'CSR Compliant'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="6" fill="#F1F5F9" />
        <path d="M16 9 L20 15 L26 15 L21 21 L23 27 L16 23 L9 27 L11 21 L6 15 L12 15 Z" fill="#94A3B8" />
      </svg>
    ),
    color: '#64748B', bg: '#F8FAFC', border: '#E2E8F0', activeBorder: '#CBD5E1',
  },
  {
    id: 'active_partner',
    label: 'Active Partner',
    range: 'ZenQ 65–74',
    min: 65, max: 74,
    requirements: ['Corporate ZenQ 65+', 'Min 2 circles', 'Employee engagement'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="6" fill="#E0F2FE" />
        <path d="M16 9 L20 15 L26 15 L21 21 L23 27 L16 23 L9 27 L11 21 L6 15 L12 15 Z" fill="#0EA5E9" />
      </svg>
    ),
    color: '#0284C7', bg: '#F0F9FF', border: '#BAE6FD', activeBorder: '#7DD3FC',
  },
  {
    id: 'impact_leader',
    label: 'Impact Leader',
    range: 'ZenQ 75–85',
    min: 75, max: 85,
    requirements: ['Corporate ZenQ 75+', '5+ circle employees', 'Annual ZenQ report'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="6" fill="#CCFBF1" />
        <path d="M16 9 L20 15 L26 15 L21 21 L23 27 L16 23 L9 27 L11 21 L6 15 L12 15 Z" fill="#0CBEAA" />
      </svg>
    ),
    color: '#0D9488', bg: '#F0FDFA', border: '#99F6E4', activeBorder: '#5EEAD4',
  },
  {
    id: 'zenk_platinum',
    label: 'ZenK Platinum',
    range: 'ZenQ 86+',
    min: 86, max: 100,
    requirements: ['Corporate ZenQ 86+', '5+ circles active', 'Certified Annual Report'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="6" fill="#FEE2E2" />
        <path d="M16 9 L20 15 L26 15 L21 21 L23 27 L16 23 L9 27 L11 21 L6 15 L12 15 Z" fill="#EF4444" />
        <path d="M16 12 L18.5 16 L22 16 L19 19 L20 23 L16 21 L12 23 L13 19 L10 16 L13.5 16 Z" fill="#FFFFFF" />
      </svg>
    ),
    color: '#B91C1C', bg: '#FEF2F2', border: '#FECACA', activeBorder: '#FCA5A5',
  },
];

// ── Download helper (authenticated) ─────────────────────────────────────────
async function downloadFile(endpoint, filename) {
  const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
  try {
    const res = await fetch(`${API}${endpoint}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Download failed: ${err.message}`);
  }
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CorpCertification({ profile }) {
  const [downloading, setDownloading] = useState(null);

  const zenq = profile?.corporate_zenq || 78.4;
  const company = profile?.company_name || 'TCS Foundation';
  const totalCsr = profile?.total_csr_deployed || 100000;
  const circles = profile?.circles_funded || 3;
  const employees = profile?.employees_engaged || 12;
  const tier = profile?.impact_tier || 'Impact Leader';
  const corpId = profile?.corp_id || 'CIN-ZNK-fd0721b9';

  const certNo = `ZNK-CERT-2026-${Math.abs(company.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % 9000 + 1000}`;
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });

  // Determine current tier and next tier
  const currentTierObj = TIERS.find(t => zenq >= t.min && zenq <= t.max) || TIERS[2];
  const nextTierObj = TIERS[TIERS.indexOf(currentTierObj) + 1] || null;
  const ptsToNext = nextTierObj ? Math.max(0, nextTierObj.min - zenq).toFixed(1) : null;
  const monthlyGrowth = 1.7;
  const monthsToNext = ptsToNext ? Math.ceil(ptsToNext / monthlyGrowth) : null;

  const handle = async (endpoint, filename, key) => {
    setDownloading(key);
    await downloadFile(endpoint, filename);
    setDownloading(null);
  };

  const companySlug = company.replace(/\s+/g, '_');

  const ACTIONS = [
    {
      key: 'cert',
      label: 'Download Certificate',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <path d="M9 15l2 2 4-4" />
        </svg>
      ),
      endpoint: '/corporate/impact/certificate',
      filename: `ZenQ_Certificate_${companySlug}_FY2025-26.pdf`,
      style: { background: '#0CBEAA', color: '#FFFFFF', border: '1px solid #0B9E8E' },
    },
    {
      key: 'annual',
      label: 'Annual Report Insert',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
      ),
      endpoint: '/corporate/impact/annual-report',
      filename: `ZenQ_Annual_Report_${companySlug}_FY2025-26.pdf`,
      style: { background: '#0F172A', color: '#FFFFFF', border: '1px solid #0F172A' },
    },
    {
      key: 'brsr',
      label: 'BRSR Compliance PDF',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      ),
      endpoint: '/corporate/impact/brsr-docs',
      filename: `ZenQ_BRSR_Docs_${companySlug}_FY2025-26.pdf`,
      style: { background: '#FFFFFF', color: '#334155', border: '1px solid #E2E8F0' },
    },
    {
      key: 'csv',
      label: 'Export Metrics (CSV)',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      ),
      endpoint: '/corporate/impact/brsr-export',
      filename: `ZenQ_BRSR_Export_${companySlug}_FY2025-26.csv`,
      style: { background: '#FFFFFF', color: '#334155', border: '1px solid #E2E8F0' },
    },
  ];

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", color: '#0F172A', maxWidth: '1200px' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', margin: 0, color: '#0F172A' }}>
            Impact Certification
          </h2>
          <p style={{ margin: '4px 0 0 0', color: '#64748B', fontSize: 14 }}>
            Official CSR compliance documentation and ZenQ tier progression.
          </p>
        </div>
      </div>

      {/* ── Tier Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        {TIERS.map(tier_obj => {
          const isCurrent = tier_obj.id === currentTierObj.id;
          const isPast = TIERS.indexOf(tier_obj) < TIERS.indexOf(currentTierObj);
          return (
            <div key={tier_obj.id} style={{
              position: 'relative',
              background: '#FFFFFF',
              border: `1px solid ${isCurrent ? tier_obj.activeBorder : '#E2E8F0'}`,
              borderRadius: 12,
              padding: '20px 16px',
              opacity: isPast ? 0.7 : 1,
              boxShadow: isCurrent ? '0 4px 12px rgba(15,23,42,0.04)' : 'none',
              overflow: 'hidden'
            }}>
              {isCurrent && (
                <div style={{
                  position: 'absolute', top: 0, left: 0, width: '100%', height: 3,
                  background: tier_obj.color
                }} />
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                {tier_obj.icon}
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: isCurrent ? tier_obj.color : '#334155' }}>
                    {tier_obj.label}
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 500, color: '#94A3B8' }}>
                    {tier_obj.range}
                  </div>
                </div>
              </div>

              <div style={{ fontSize: 12, color: '#475569', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {tier_obj.requirements.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <span style={{ color: isCurrent ? tier_obj.color : '#CBD5E1', fontSize: 13, lineHeight: 1.2 }}>
                      {isPast || isCurrent ? '✓' : '○'}
                    </span>
                    <span style={{ color: isCurrent ? '#0F172A' : '#64748B', fontWeight: isCurrent ? 500 : 400 }}>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Certificate Pane ── */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: 16,
        overflow: 'hidden',
        border: '2px solid #F59E0B',
        boxShadow: '0 8px 30px rgba(245, 158, 11, 0.1)',
        marginBottom: 24,
        position: 'relative',
        padding: '32px 40px',
      }}>
        {/* Watermark */}
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%) rotate(-15deg)',
          fontSize: '120px',
          fontWeight: 900,
          color: 'rgba(0, 0, 0, 0.02)',
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
          zIndex: 0,
        }}>
          ZENK CERTIFIED
        </div>

        {/* Content wrapper to stay above watermark */}
        <div style={{ position: 'relative', zIndex: 1 }}>

          {/* Header Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 40 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <img src="/assets/zenk-logo.png" alt="ZenK" style={{ height: 36, objectFit: 'contain' }} />
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>ZenK Impact Platforms</div>
              <div style={{ fontSize: 12, color: '#64748B', marginBottom: 2 }}>Certificate No: {certNo}</div>
              <div style={{ fontSize: 12, color: '#64748B', marginBottom: 2 }}>Issued: {today}</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Valid until: 31 March 2027</div>
            </div>
          </div>

          {/* Title Row */}
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <h2 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 28, fontWeight: 700, color: '#0F172A', margin: '0 0 12px 0' }}>ZenQ Impact Certificate</h2>
            <div style={{ fontSize: 14, color: '#475569' }}>
              This certifies that <strong style={{ fontWeight: 600, color: profile?.brand_color || '#0F172A' }}>{company}</strong> has achieved verified social impact through the ZenK platform during FY 2025–26
            </div>
          </div>

          {/* Score Block (Blue Background) */}
          <div style={{
            background: 'linear-gradient(180deg, #F0F9FF 0%, #E0F2FE 100%)',
            border: '1px solid #BAE6FD',
            borderRadius: 12,
            padding: '24px',
            textAlign: 'center',
            marginBottom: 24,
          }}>
            <div style={{ fontFamily: "'Outfit', sans-serif", fontSize: 64, fontWeight: 700, color: '#0284C7', lineHeight: 1, marginBottom: 8 }}>
              {zenq}
            </div>
            <div style={{ fontSize: 14, fontWeight: 500, color: '#0369A1', marginBottom: 8 }}>
              Corporate ZenQ Weighted Average Score — FY 2025–26
            </div>
            <div style={{ fontSize: 12, color: '#0284C7' }}>
              AI-verified · Auditable · Tamper-evident · Blockchain-anchored hash: {`3f8a2c...d91b`}
            </div>
          </div>

          {/* Grid Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>₹{totalCsr.toLocaleString('en-IN')}</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Total CSR deployed</div>
            </div>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>{circles} circles</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Sponsor circles funded</div>
            </div>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>{employees} employees</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Volunteer contributors</div>
            </div>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>2 students</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Education journeys supported</div>
            </div>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>+35%</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>ZenQ growth rate (YoY)</div>
            </div>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>{currentTierObj.label}</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Impact certification level</div>
            </div>
          </div>

          {/* Badges Row */}
          <div style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 32 }}>
            {['SDG 4 — Quality Education', 'SDG 10 — Reduced Inequalities', 'SDG 17 — Partnerships', 'Schedule VII Item (ii) — CSR Compliant', '80G Deductible'].map(b => (
              <span key={b} style={{
                background: 'transparent', color: profile?.brand_color || '#0369A1', fontSize: 12, fontWeight: 500,
                padding: '8px 16px', borderRadius: 100, border: `1px solid ${profile?.brand_color || '#BAE6FD'}22`,
              }}>{b}</span>
            ))}
          </div>

          {/* Footer Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#0F172A', marginBottom: 4 }}>AI-verified and digitally signed</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>Verifiable at <span style={{ color: profile?.brand_color || '#0369A1', fontWeight: 500 }}>zenk.in/verify/{certNo}</span></div>
            </div>
            <div style={{ width: 56, height: 56, border: '1px solid #E2E8F0', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#94A3B8', background: '#F8FAFC' }}>
              QR<br />code
            </div>
          </div>

        </div>
      </div>

      {/* ── Action Buttons ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16 }}>
        {ACTIONS.map(action => (
          <button
            key={action.key}
            onClick={() => handle(action.endpoint, action.filename, action.key)}
            disabled={downloading === action.key}
            style={{
              ...action.style,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              padding: '14px 16px', borderRadius: 8,
              fontFamily: "'Inter', sans-serif", fontSize: 13, fontWeight: 600,
              cursor: downloading === action.key ? 'wait' : 'pointer',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              opacity: downloading && downloading !== action.key ? 0.5 : 1,
              transform: downloading === action.key ? 'scale(0.98)' : 'scale(1)',
              boxShadow: action.key === 'cert' ? '0 4px 12px rgba(12,190,170,0.15)' : 'none',
            }}
            onMouseEnter={e => { if (downloading !== action.key) e.currentTarget.style.transform = 'translateY(-1px)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = downloading === action.key ? 'scale(0.98)' : 'scale(1)'; }}
          >
            {downloading === action.key ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: 'spin 1s linear infinite' }}>
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            ) : action.icon}
            {downloading === action.key ? 'Generating…' : action.label}
          </button>
        ))}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
