import React, { useState } from 'react';
import { useCirclePerformanceLive } from '../hooks/useCirclePerformanceLive';
import CircleSparkline from './CircleSparkline';
import AllocationModal from './AllocationModal';
import CircleChatPanel from './CircleChatPanel';

export default function CorpCirclePerf({ circlesPerf, reallocate, unallocatedBalance }) {
  const [activeModalCircle, setActiveModalCircle] = useState(null);
  const [activeChatCircle, setActiveChatCircle] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Poll for live ZenQ updates
  const liveZenQ = useCirclePerformanceLive(circlesPerf?.circles);

  if (!circlesPerf || !circlesPerf.circles) return (
    <div className="c-skeleton" style={{ height: 400 }} />
  );

  const getApiBase = () => {
    if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
    const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
    if (hostname.includes('vercel.app') || hostname.includes('zenk') || hostname.includes('railway.app')) {
      return 'https://deployment-production-27bd.up.railway.app';
    }
    return 'http://localhost:8000';
  };

  const handleDownload = async (circleName) => {
    setIsDownloading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${getApiBase()}/corporate/impact-report/${encodeURIComponent(circleName)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ZenK_Impact_${circleName.replace(/ /g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert('Failed to generate report');
      }
    } catch (e) {
      console.error(e);
      alert('Error downloading report');
    }
    setIsDownloading(false);
  };

  return (
    <div className="c-circle-perf-module">

      {circlesPerf.circles.map((circle, idx) => {
        // Calculate progress bar
        const currentZenQ = liveZenQ[circle.circle_name] || circle.zenq_score;
        const progressPct = Math.min(100, Math.max(0, currentZenQ));
        const growth = (currentZenQ - (circle.zenq_start || 60)).toFixed(1);

        return (
          <div key={idx} className="c-corp-circle-card">

            {/* Header */}
            <div className="c-card-header-row">
              <div className="c-card-header-left">
                <h2>{circle.circle_name}</h2>
                <span className="c-card-subtitle">SL: {circle.leader} • {circle.city} • {circle.members} members</span>
              </div>
              <div className="c-card-header-right">
                <div className={`c-zenq-badge ${currentZenQ > 75 ? 'c-zenq-high' : 'c-zenq-med'}`}>
                  ZenQ {currentZenQ.toFixed(1)} {growth > 0 ? '↑' : '↓'}
                </div>
                <div className="c-allocation-badge">
                  Your allocation: ₹{circle.allocation_amount?.toLocaleString()} ({circle.allocation_pct}%)
                </div>
                <div className="c-status-pill">{circle.status}</div>
              </div>
            </div>

            {/* Progress Bar Area */}
            <div className="c-progress-section">
              <div className="c-progress-label">
                ZenQ progress this year — started at {circle.zenq_start || 60}
              </div>
              <div className="c-progress-track">
                <div
                  className="c-progress-fill"
                  style={{ width: `${progressPct}%`, backgroundColor: circle.color || '#0CBEAA' }}
                />
              </div>
              <div className="c-progress-stats">
                {currentZenQ.toFixed(1)} / 100 • {growth > 0 ? `+${growth}` : growth} pts growth
              </div>
            </div>

            {/* Sparkline & KPIs Row */}
            <div className="c-metrics-row">
              <div className="c-sparkline-container" title="12-Month ZenQ Trend">
                <div className="c-spark-label">12m Trend</div>
                <CircleSparkline data={circle.monthly_trend} color={circle.color} width={120} height={40} />
              </div>

              <div className="c-kpi-chip">
                <label>STUDENT ZQA</label>
                <div className="c-kpi-val">{circle.student_zqa || 0}% <span>↑</span></div>
              </div>
              <div className="c-kpi-chip">
                <label>PARTICIPATION</label>
                <div className="c-kpi-val">{circle.participation_pct}%</div>
              </div>
              <div className="c-kpi-chip">
                <label>FUND UTILISED</label>
                <div className="c-kpi-val">{circle.fund_utilised_pct || 0}%</div>
              </div>
              <div className="c-kpi-chip">
                <label>RANK NATIONALLY</label>
                <div className="c-kpi-val" style={{ color: circle.color }}>#{circle.rank}</div>
              </div>
            </div>

            {/* Kia Insight Box */}
            {circle.kia_insight && (
              <div className={`c-kia-inline-box ${circle.risk_flag ? 'c-risk-alert' : ''}`}>
                <div className="c-k-avatar">K</div>
                <div className="c-kia-text">
                  {circle.kia_insight}
                </div>
              </div>
            )}

            {/* Action Row */}
            <div className="c-card-actions">
              <button className="c-btn c-btn-primary" onClick={() => setActiveChatCircle(circle)}>
                Join circle chat →
              </button>
              <button className="c-btn c-btn-success" onClick={() => handleDownload(circle.circle_name)} disabled={isDownloading}>
                {isDownloading ? 'Generating PDF...' : 'Download impact report'}
              </button>
              <button className="c-btn c-btn-outline" onClick={() => setActiveModalCircle(circle)}>
                Increase allocation
              </button>
              {circle.risk_flag === "Low Participation" && (
                <button className="c-btn c-btn-outline">Nominate mentor</button>
              )}
            </div>

          </div>
        );
      })}

      {/* Platform Pool Section */}
      <div className="c-platform-pool-card">
        <div className="c-pool-header">
          <h3>ZenK Platform pool — your {circlesPerf.platform_pool_pct || 10}% allocation</h3>
          <p>₹{(circlesPerf.platform_pool_amount || 0).toLocaleString()} ({circlesPerf.platform_pool_pct || 10}% of your total) is pooled with all corporate partners and distributed by AI across all {circlesPerf.total_circles_benefitting || 0} circles. This earns the national average ZenQ of <strong>{circlesPerf.national_avg_zenq || 76.2}</strong>.</p>
        </div>
        <div className="c-pool-metrics">
          <div className="c-pool-kpi">
            <label>YOUR ZENK POOL CONTRIBUTION</label>
            <div className="c-val">₹{(circlesPerf.platform_pool_amount || 0).toLocaleString()}</div>
          </div>
          <div className="c-pool-kpi">
            <label>NATIONAL AVG ZENQ</label>
            <div className="c-val" style={{ color: '#4A72F5' }}>{circlesPerf.national_avg_zenq}</div>
          </div>
          <div className="c-pool-kpi">
            <label>CIRCLES BENEFITTING</label>
            <div className="c-val">{circlesPerf.total_circles_benefitting}</div>
          </div>
        </div>
      </div>

      {activeModalCircle && (
        <AllocationModal
          circle={activeModalCircle}
          available={unallocatedBalance}
          onClose={() => setActiveModalCircle(null)}
          onConfirm={reallocate}
        />
      )}

      {activeChatCircle && (
        <CircleChatPanel
          circle={activeChatCircle}
          onClose={() => setActiveChatCircle(null)}
        />
      )}

    </div>
  );
}
