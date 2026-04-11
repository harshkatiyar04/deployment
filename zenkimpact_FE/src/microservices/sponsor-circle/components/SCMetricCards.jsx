import { SUMMARY } from '../data/placeholders'

export default function SCMetricCards() {
  const s = SUMMARY

  const spentPct = Math.round((s.time_this_month_hrs / s.top_group_hrs) * 100)

  return (
    <div className="sc-metrics-row">
      <div className="sc-metric-card">
        <div className="sc-metric-label">My ZenQ Score</div>
        <div className="sc-metric-value green">{s.zenq_score}</div>
        <div className="sc-metric-sub">Out of 100</div>
        <div className="sc-metric-tag">+{s.zenq_change} pts this month</div>
      </div>

      <div className="sc-metric-card">
        <div className="sc-metric-label">Circle Rank</div>
        <div className="sc-metric-value orange">#{s.circle_rank}</div>
        <div className="sc-metric-sub">of {s.total_circles} circles</div>
        <div className="sc-metric-tag">↑ Up from #{s.rank_previous}</div>
      </div>

      <div className="sc-metric-card">
        <div className="sc-metric-label">My Participation</div>
        <div className="sc-metric-value dark">{s.participation_pct}%</div>
        <div className="sc-metric-sub">Circle avg: {s.circle_avg_pct}%</div>
        <div className="sc-metric-tag" style={{ color: '#f08c3b' }}>
          +{s.participation_pct - s.circle_avg_pct}% above avg
        </div>
      </div>

      <div className="sc-metric-card">
        <div className="sc-metric-label">My Time This Month</div>
        <div className="sc-metric-value dark">{s.time_this_month_hrs} hrs</div>
        <div className="sc-metric-sub">Top group: {s.top_group_hrs} hrs</div>
        <div style={{ marginTop: 8, height: 6, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
          <div
            style={{
              width: `${spentPct}%`,
              height: '100%',
              background: '#1e8e6a',
              borderRadius: 999,
            }}
          />
        </div>
      </div>
    </div>
  )
}
