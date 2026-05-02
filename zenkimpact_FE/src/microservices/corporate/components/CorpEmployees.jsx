import React, { useState } from 'react';
import { EmpHoursChart } from './CorpCharts';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';

/* ── Badge helpers ─────────────────────────────────────────────────────────── */
const BADGE_CONFIG = {
  gold: { bg: '#FFF8E1', text: '#B26A00', border: '#F6C343', label: '★ Gold' },
  silver: { bg: '#F5F5F5', text: '#5A5A5A', border: '#C0C0C0', label: '★ Silver' },
  bronze: { bg: '#FFF3ED', text: '#8B4513', border: '#CD7F32', label: '★ Bronze' },
};

function VolunteerBadge({ badge }) {
  if (!badge) return null;
  const cfg = BADGE_CONFIG[badge];
  return (
    <span style={{
      fontSize: 13, background: cfg.bg, color: cfg.text,
      border: `1px solid ${cfg.border}`, borderRadius: 6,
      padding: '2px 7px', fontWeight: 700,
    }}>{cfg.label}</span>
  );
}

/* ── Dept Bar Chart ────────────────────────────────────────────────────────── */
function DeptBarChart({ data = [] }) {
  const chartData = data.map(d => ({
    name: d.department,
    active: d.active,
    pct: Math.round((d.active / d.employees) * 100),
    hours: d.hours,
  }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0ee" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#b0b0b0', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 100]} tickFormatter={v => `${v}%`} />
        <YAxis type="category" dataKey="name" tick={{ fill: '#444', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} width={78} />
        <Tooltip
          formatter={(v, n) => n === 'pct' ? [`${v}%`, 'Engagement Rate'] : [v, n]}
          contentStyle={{ background: '#fff', border: '1px solid #e8e8e4', borderRadius: 8, fontSize: 12 }}
        />
        <Bar dataKey="pct" name="pct" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={i === 0 ? '#0CBEAA' : i === 1 ? '#4A72F5' : i === 2 ? '#F6C343' : '#9b8df8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Kia Insight Box ───────────────────────────────────────────────────────── */
function KiaBox({ insight }) {
  if (!insight) return null;
  return (
    <div style={{
      background: 'linear-gradient(135deg, #effaf7 0%, #e8f4ff 100%)',
      border: '1.5px solid #0CBEAA', borderRadius: 14,
      padding: '16px 20px', display: 'flex', gap: 14, alignItems: 'flex-start',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: '50%',
        background: 'linear-gradient(135deg, #0CBEAA, #4A72F5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, color: '#fff',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
          <polyline points="7.5 4.21 12 6.81 16.5 4.21"></polyline>
          <polyline points="7.5 19.79 7.5 14.6 3 12"></polyline>
          <polyline points="21 12 16.5 14.6 16.5 19.79"></polyline>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
          <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 12, fontWeight: 800, color: '#0CBEAA', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>Kia AI — Engagement Recommendation</div>
        <div style={{ fontSize: 13.5, color: '#1e293b', lineHeight: 1.65, fontWeight: 500 }}>{insight}</div>
      </div>
    </div>
  );
}

/* ── Scheme Card ───────────────────────────────────────────────────────────── */
function SchemeIcon({ iconType }) {
  if (iconType === '🤝') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0CBEAA" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
        <circle cx="9" cy="7" r="4"></circle>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
      </svg>
    );
  }
  if (iconType === '🕐') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4A72F5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 6 12 12 16 14"></polyline>
      </svg>
    );
  }
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F6C343" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
      <polyline points="2 17 12 22 22 17"></polyline>
      <polyline points="2 12 12 17 22 12"></polyline>
    </svg>
  );
}

function SchemeCard({ scheme }) {
  return (
    <div style={{
      background: '#fff', border: '1.5px solid #e8e8e4', borderRadius: 14,
      padding: '18px 20px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <SchemeIcon iconType={scheme.icon} />
        <div style={{ fontSize: 14, fontWeight: 800, color: '#1e293b' }}>{scheme.title}</div>
        <span style={{
          marginLeft: 'auto', fontSize: 11, fontWeight: 700, color: '#0CBEAA',
          background: '#effaf7', border: '1px solid #0CBEAA', borderRadius: 20,
          padding: '2px 10px',
        }}>● {scheme.status}</span>
      </div>
      <div style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.65, marginBottom: 12 }}>{scheme.description}</div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 11, color: '#888' }}>
          <span style={{ color: '#1e293b', fontWeight: 800, fontSize: 15 }}>{scheme.participants?.toLocaleString('en-IN')}</span>
          <span style={{ marginLeft: 4 }}>participants</span>
        </div>
        {scheme.total_matched && (
          <div style={{ fontSize: 11, color: '#888' }}>
            <span style={{ color: '#0CBEAA', fontWeight: 800, fontSize: 14 }}>₹{scheme.total_matched.toLocaleString('en-IN')}</span>
            <span style={{ marginLeft: 4 }}>total matched</span>
          </div>
        )}
        {scheme.zenq_uplift && (
          <div style={{ fontSize: 11, color: '#888' }}>
            <span style={{ color: '#4A72F5', fontWeight: 800, fontSize: 14 }}>+{scheme.zenq_uplift} pts</span>
            <span style={{ marginLeft: 4 }}>ZenQ uplift</span>
          </div>
        )}
        {scheme.extra && (
          <div style={{ fontSize: 11, color: '#888', fontStyle: 'italic' }}>{scheme.extra}</div>
        )}
      </div>
    </div>
  );
}

/* ── Employee Circle Card ──────────────────────────────────────────────────── */
function EmpCircleCard({ circle, onViewCircle }) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, #f0fffe 0%, #eef3ff 100%)',
      border: '1.5px solid #0CBEAA33', borderRadius: 14,
      padding: '16px 18px',
    }}>
      <div style={{ fontSize: 14, fontWeight: 800, color: '#1e293b', marginBottom: 4 }}>{circle.name}</div>
      <div style={{ fontSize: 11.5, color: '#64748b', marginBottom: 12 }}>
        {circle.employees} TCS employees &nbsp;·&nbsp; Company match ₹{(circle.company_match || 0).toLocaleString('en-IN')}
      </div>
      <div style={{ display: 'flex', gap: 20 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em' }}>ZenQ</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: '#0CBEAA' }}>{circle.zenq}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Rank</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: '#4A72F5' }}>#{circle.rank}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Fund</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: '#1e293b' }}>₹{(circle.fund || 0).toLocaleString('en-IN')}</div>
        </div>
      </div>
      <button
        onClick={() => onViewCircle && onViewCircle(circle.name)}
        style={{
          marginTop: 14, width: '100%', padding: '8px 0',
          background: 'linear-gradient(90deg, #0CBEAA, #4A72F5)',
          color: '#fff', border: 'none', borderRadius: 8, fontSize: 12,
          fontWeight: 700, cursor: 'pointer', fontFamily: 'Inter, sans-serif',
          letterSpacing: '0.03em',
        }}
      >View Circle Performance →</button>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────────────────── */
export default function CorpEmployees({ employees, onNavigate }) {
  const [nominateOpen, setNominateOpen] = useState(false);
  const [launchOpen, setLaunchOpen] = useState(false);
  const [nominateName, setNominateName] = useState('');
  const [nominateDept, setNominateDept] = useState('');
  const [nominateCircle, setNominateCircle] = useState('');

  if (!employees) return <div className="c-skeleton" style={{ height: 400 }} />;

  const volunteers = employees.volunteers?.length ? employees.volunteers : employees.top_contributors || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── KPI Strip ────────────────────────────────────────────────── */}
      <div className="c-metrics-grid">
        {(employees.metrics || []).map((m, i) => (
          <div className="c-metric-card" key={i}>
            <div className="c-metric-value">{m.value}</div>
            <div className="c-metric-label">{m.label}</div>
            <div className={`c-metric-delta ${m.trend}`}>{m.delta}</div>
          </div>
        ))}
      </div>

      {/* ── Row: Volunteers + Employee Circles ──────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Active Volunteers */}
        <div className="c-card">
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
            <div className="c-card-title" style={{ margin: 0, flex: 1 }}>Active volunteers — tutors &amp; mentors</div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {volunteers.map((v, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 14px', borderRadius: 10,
                background: i === 0 ? '#FFFBF0' : '#fafafa',
                border: '1px solid #f0f0ee',
              }}>
                <div style={{
                  width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                  background: `hsl(${(i * 60 + 160) % 360}, 60%, 88%)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 800, color: `hsl(${(i * 60 + 160) % 360}, 50%, 35%)`,
                }}>{v.initials}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {v.name} <VolunteerBadge badge={v.badge} />
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginTop: 1 }}>
                    {v.department} · {v.circle || 'Unassigned'}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#0CBEAA' }}>{v.hours} hrs</div>
                  {v.zenq_contribution && (
                    <div style={{ fontSize: 11, color: '#4A72F5', fontWeight: 600 }}>+{v.zenq_contribution} ZenQ</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => setNominateOpen(true)}
            style={{
              marginTop: 14, width: '100%', padding: '10px 0',
              background: 'none', border: '1.5px dashed #0CBEAA',
              color: '#0CBEAA', borderRadius: 10, fontSize: 13,
              fontWeight: 700, cursor: 'pointer', fontFamily: 'Inter, sans-serif',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.target.style.background = '#effaf7'; }}
            onMouseLeave={e => { e.target.style.background = 'none'; }}
          >+ Nominate new volunteer</button>
        </div>

        {/* Employee-led Circles */}
        <div className="c-card">
          <div className="c-card-title">Employee-led Sponsor Circles</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {(employees.employee_circles || []).map((ec, i) => (
              <EmpCircleCard
                key={i}
                circle={ec}
                onViewCircle={() => onNavigate && onNavigate('circles')}
              />
            ))}
          </div>
          <button
            onClick={() => setLaunchOpen(true)}
            style={{
              marginTop: 14, width: '100%', padding: '10px 0',
              background: 'none', border: '1.5px dashed #4A72F5',
              color: '#4A72F5', borderRadius: 10, fontSize: 13,
              fontWeight: 700, cursor: 'pointer', fontFamily: 'Inter, sans-serif',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.target.style.background = '#eef3ff'; }}
            onMouseLeave={e => { e.target.style.background = 'none'; }}
          >+ Launch new employee circle</button>
        </div>
      </div>

      {/* ── Active Engagement Schemes ────────────────────────────────── */}
      <div className="c-card">
        <div className="c-card-title">Active Engagement Schemes</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {(employees.engagement_schemes || []).map((s, i) => (
            <SchemeCard key={i} scheme={s} />
          ))}
        </div>
      </div>

      {/* ── Row: Department Chart + Monthly Hours ─────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="c-card">
          <div className="c-card-title">Department Engagement Rate</div>
          <div style={{ fontSize: 12, color: '#888', marginBottom: 10 }}>% of employees actively volunteering</div>
          {employees.department_breakdown?.length > 0 && (
            <DeptBarChart data={employees.department_breakdown} />
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 }}>
            {(employees.department_breakdown || []).map((d, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                <div style={{
                  width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                  background: i === 0 ? '#0CBEAA' : i === 1 ? '#4A72F5' : i === 2 ? '#F6C343' : '#9b8df8'
                }} />
                <span style={{ flex: 1, color: '#444', fontWeight: 600 }}>{d.department}</span>
                <span style={{ color: '#888' }}>{d.active}/{d.employees} active</span>
                <span style={{ color: '#0CBEAA', fontWeight: 700 }}>{d.hours}h</span>
              </div>
            ))}
          </div>
        </div>

        <div className="c-card">
          <div className="c-card-title">
            Monthly Volunteer Hours — FY 2025-26
          </div>
          <EmpHoursChart data={employees.monthly_hours} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#4A72F5' }}>
                {employees.monthly_hours?.reduce((s, m) => s + m.hours, 0) || 0}
              </div>
              <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>Total Hours FY</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#0CBEAA' }}>
                {employees.avg_hours_per_employee || 7.0}h
              </div>
              <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>Avg / Employee</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#F6C343' }}>
                +{employees.zenq_lift_from_staff || 0}
              </div>
              <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>ZenQ Lift</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Kia AI Insight ───────────────────────────────────────────── */}
      {employees.kia_insight && <KiaBox insight={employees.kia_insight} />}

      {/* ── Nominate Volunteer Modal ─────────────────────────────────── */}
      {nominateOpen && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setNominateOpen(false)}>
          <div style={{
            background: '#fff', borderRadius: 18, padding: '32px 28px',
            width: 440, boxShadow: '0 24px 64px rgba(0,0,0,0.18)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>Nominate a Volunteer</div>
            <div style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>This employee will be invited to log hours on the ZenK platform and contribute to your Corporate ZenQ score.</div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                ['Employee Name', nominateName, setNominateName, 'e.g. Amit Joshi'],
                ['Department', nominateDept, setNominateDept, 'e.g. Engineering'],
                ['Assign to Circle', nominateCircle, setNominateCircle, 'e.g. Ashoka Rising Circle'],
              ].map(([label, val, setter, ph]) => (
                <div key={label}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#444', marginBottom: 5 }}>{label}</div>
                  <input value={val} onChange={e => setter(e.target.value)} placeholder={ph}
                    style={{
                      width: '100%', padding: '10px 12px', borderRadius: 8,
                      border: '1.5px solid #e2e8f0', fontSize: 13, fontFamily: 'Inter, sans-serif',
                      color: '#1e293b', outline: 'none', boxSizing: 'border-box',
                    }} />
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
              <button onClick={() => setNominateOpen(false)} style={{
                flex: 1, padding: '11px 0', borderRadius: 10, border: '1.5px solid #e2e8f0',
                background: '#fff', color: '#64748b', fontWeight: 700, cursor: 'pointer', fontSize: 13,
              }}>Cancel</button>
              <button onClick={() => {
                alert(`Nomination sent for ${nominateName || 'the employee'}! They will receive an invite via email.`);
                setNominateOpen(false);
                setNominateName(''); setNominateDept(''); setNominateCircle('');
              }} style={{
                flex: 2, padding: '11px 0', borderRadius: 10, border: 'none',
                background: 'linear-gradient(90deg, #0CBEAA, #4A72F5)',
                color: '#fff', fontWeight: 800, cursor: 'pointer', fontSize: 13, fontFamily: 'Inter, sans-serif',
              }}>Send Nomination Invite</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Launch Circle Modal ──────────────────────────────────────── */}
      {launchOpen && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setLaunchOpen(false)}>
          <div style={{
            background: '#fff', borderRadius: 18, padding: '32px 28px',
            width: 460, boxShadow: '0 24px 64px rgba(0,0,0,0.18)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>Launch a New Employee Circle</div>
            <div style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>Your company will seed-fund this circle with ₹60,000. It will count toward your Corporate ZenQ score.</div>

            <div style={{
              background: 'linear-gradient(135deg, #effaf7, #eef3ff)', borderRadius: 12,
              padding: '14px 16px', marginBottom: 20,
            }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: '#0CBEAA', marginBottom: 6 }}>What you get:</div>
              <div style={{ fontSize: 12.5, color: '#1e293b', lineHeight: 1.7, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  '₹60,000 seed grant from TCS Foundation',
                  'Circle added to your Corporate ZenQ score',
                  'Kia AI circle coaching and monitoring',
                  'Quarterly impact reports'
                ].map((text, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <svg style={{ marginTop: 2, flexShrink: 0 }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0CBEAA" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    <span>{text}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setLaunchOpen(false)} style={{
                flex: 1, padding: '11px 0', borderRadius: 10, border: '1.5px solid #e2e8f0',
                background: '#fff', color: '#64748b', fontWeight: 700, cursor: 'pointer', fontSize: 13,
              }}>Cancel</button>
              <button onClick={() => {
                alert('Circle launch request submitted! The ZenK team will contact you within 2 business days to onboard your new circle.');
                setLaunchOpen(false);
              }} style={{
                flex: 2, padding: '11px 0', borderRadius: 10, border: 'none',
                background: 'linear-gradient(90deg, #4A72F5, #9b8df8)',
                color: '#fff', fontWeight: 800, cursor: 'pointer', fontSize: 13, fontFamily: 'Inter, sans-serif',
              }}>Submit Launch Request</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
