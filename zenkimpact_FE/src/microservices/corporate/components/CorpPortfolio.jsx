import React, { useState } from 'react';
import { ZenQGauge, ZenQTrendChart, AllocationDonut } from './CorpCharts';

const fmt = n => `₹${(n || 0).toLocaleString('en-IN')}`;

export default function CorpPortfolio({ profile, zenqOverview, allocations, onReallocate, onNavigate }) {
  const [allocInputs, setAllocInputs] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const [kiaRecState, setKiaRecState] = useState('idle');
  const [kiaRecText, setKiaRecText] = useState('');

  const handleAskKia = async () => {
    setKiaRecState('loading');
    setKiaRecText('');
    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/corporate/kia-recommendation`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch recommendation');
      const data = await res.json();
      setKiaRecText(data.recommendation);
      setKiaRecState('success');
    } catch (err) {
      console.error(err);
      setKiaRecState('error');
    }
  };

  if (!profile || !zenqOverview || !allocations) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {[100, 280, 200].map((h, i) => <div key={i} className="c-skeleton" style={{ height: h }} />)}
      </div>
    );
  }

  const activeCircles = allocations.circles.filter(c => c.status === 'active');

  const handleReallocate = async () => {
    const items = activeCircles
      .filter(c => Number(allocInputs[c.circle_name]) > 0)
      .map(c => ({ circle_name: c.circle_name, amount: Number(allocInputs[c.circle_name]) }));
    if (!items.length) return;
    setSubmitting(true);
    try {
      const res = await onReallocate(items);
      setSuccessMsg(res.message);
      setTimeout(() => setSuccessMsg(''), 5000);
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── ZenQ Card (teal-tinted matching Stitch reference) ──── */}
      <div className="c-card zenq-tinted">
        <div className="c-card-title">Weighted average ZenQ score — {profile.fy_label}</div>
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, flex: 1 }}>
            <ZenQGauge score={zenqOverview.weighted_score} size={130} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: '#444', lineHeight: 1.7, marginBottom: 10 }}>
                <strong>Calculated as</strong> a weighted average of the ZenQ scores of all circles you fund, weighted by your % contribution to each. The 10% ZenK platform allocation earns the national average ZenQ across all 47 circles.
              </div>
              <div className="corp-formula-box">
                <span style={{ color: '#4A72F5', fontWeight: 600 }}>{zenqOverview.formula_breakdown}</span>
              </div>
            </div>
          </div>
          {/* Tier Badge */}
          <div style={{ textAlign: 'center', padding: '12px 24px', minWidth: 120 }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="#F0A500"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#1a1a1a', marginTop: 4 }}>Gold Tier</div>
            <div style={{ fontSize: 11, color: '#888' }}>{zenqOverview.points_to_next} pts to Platinum</div>
          </div>
        </div>
      </div>

      {/* ── ZenQ Trend Chart ───────────────────────────────────── */}
      <div className="c-card">
        <div className="c-card-title">ZenQ Trend — Monthly Weighted Average vs National Average</div>
        <div className="c-legend" style={{ marginBottom: 12 }}>
          <span className="c-legend-item"><span className="c-legend-dot" style={{ background: '#4A72F5' }} />Your Corporate ZenQ</span>
          <span className="c-legend-item"><span className="c-legend-dash" />National Average ZenQ</span>
        </div>
        <ZenQTrendChart data={zenqOverview.trend} />
        <div style={{ fontSize: 12, color: '#888', lineHeight: 1.6, marginTop: 12, padding: '10px 14px', background: '#f9f9f7', borderRadius: 8 }}>
          {zenqOverview.insight}
        </div>
      </div>

      {/* ── Contribution Allocation ─────────────────────────────── */}
      <div className="c-card">
        <div className="c-card-title">Contribution Allocation — {profile.fy_label}</div>
        <div className="corp-alloc-row">
          <AllocationDonut circles={allocations.circles} />
          <div>
            <table className="corp-circle-table">
              <tbody>
                {allocations.circles.map((c, i) => (
                  <tr key={i}>
                    <td style={{ width: 18 }}><span className="c-dot" style={{ background: c.color }} /></td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{c.circle_name}</div>
                      <div style={{ fontSize: 11, color: '#888' }}>{c.leader_city !== '—' ? c.leader_city : 'Available for new circle'}</div>
                    </td>
                    <td style={{ color: '#888', fontWeight: 500 }}>{c.allocation_pct}%</td>
                    <td style={{ fontWeight: 700 }}>{fmt(c.amount)}</td>
                    <td>
                      {c.zenq_score
                        ? <span className="c-zenq-pill active">ZenQ {c.zenq_score}</span>
                        : <span className="c-zenq-pill pending">Pending</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="c-platform-note">
              ZenK Platform allocation (10% included within each circle tranche): ₹10,000 — earns national average ZenQ: 76.2
            </div>
          </div>
        </div>
      </div>

      {/* ── Unallocated Widget ──────────────────────────────────── */}
      {profile.unallocated > 0 && (
        <div className="corp-unalloc-card">
          <div className="c-card-title" style={{ marginBottom: 6 }}>Unallocated balance — allocate to a circle</div>
          <div className="corp-unalloc-amount">{fmt(profile.unallocated)} available</div>

          {activeCircles.map((c, i) => (
            <div className="c-input-row" key={i}>
              <span className="c-dot" style={{ background: c.color, marginRight: 4 }} />
              <span className="c-input-label">
                {c.circle_name}
                <span className="c-zenq-pill active" style={{ marginLeft: 8, fontSize: 10 }}>ZenQ {c.zenq_score}</span>
              </span>
              <input
                className="c-input"
                type="number"
                placeholder="₹ amount"
                min={0}
                max={profile.unallocated}
                value={allocInputs[c.circle_name] || ''}
                onChange={e => setAllocInputs(p => ({ ...p, [c.circle_name]: e.target.value }))}
              />
            </div>
          ))}

          <div className="c-input-row" style={{ color: '#888', cursor: 'pointer' }} onClick={() => onNavigate('circles')}>
            <span style={{ fontSize: 13, flex: 1 }}>+ Add a new circle</span>
            <span style={{ fontSize: 12 }}>Search →</span>
          </div>

          {successMsg && <div className="c-toast">{successMsg}</div>}

          <div className="c-actions">
            <button className="c-btn-primary" onClick={handleReallocate} disabled={submitting}>
              {submitting ? 'Confirming...' : 'Confirm allocation'}
            </button>
            <button className="c-btn-secondary" onClick={handleAskKia} disabled={kiaRecState === 'loading'}>
              Ask Kia to recommend
            </button>
          </div>

          {kiaRecState !== 'idle' && (
            <div style={{ marginTop: 16, padding: 16, backgroundColor: '#f9f9f9', borderRadius: 12, border: '1px solid #e8e8e4' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <img src="/kia-bot-avatar.png" alt="Kia" style={{ width: 24, height: 24, borderRadius: '50%' }} />
                <strong style={{ fontSize: 13, color: '#1a1a1a' }}>Kia AI Copilot</strong>
              </div>
              <div style={{ fontSize: 13, color: '#444', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                {kiaRecState === 'loading' && <span style={{ fontStyle: 'italic', color: '#888' }}>Analyzing your portfolio...</span>}
                {kiaRecState === 'error' && <span style={{ color: 'red' }}>Failed to generate a recommendation. Please try again later.</span>}
                {kiaRecState === 'success' && kiaRecText}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
