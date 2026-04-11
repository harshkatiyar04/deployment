import { TIME_IMPACT } from '../data/placeholders'

export default function SCTimeOnImpact() {
  const t = TIME_IMPACT
  const myPct = Math.round((t.my_circle_hrs / t.highest_circle_hrs) * 100)

  return (
    <div className="sc-card" style={{ height: '100%' }}>
      <div className="sc-card-title">
        TIME SPENT ON IMPACT
      </div>

      <div className="sc-time-boxes">
        <div className="sc-time-box">
          <div className="sc-time-box-label">Total — all circles combined</div>
          <div className="sc-time-val green">{t.total_hrs_all_circles} hrs</div>
          <div className="sc-time-sub">Across {t.total_circles_count} circles nationally</div>
        </div>

        <div className="sc-time-box">
          <div className="sc-time-box-label">Highest time — any circle this month</div>
          <div className="sc-time-val orange">{t.highest_circle_hrs} hrs</div>
          <div className="sc-time-sub">{t.highest_circle_name}</div>
        </div>
      </div>

      <div className="sc-progress-label">
        <span>My circle time this month: {t.my_circle_hrs} hrs</span>
        <span style={{ color: '#f08c3b', fontWeight: 600 }}>Top: {t.highest_circle_hrs} hrs</span>
      </div>
      <div className="sc-progress-track">
        <div className="sc-progress-fill" style={{ width: `${myPct}%` }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6b7280', marginTop: 4 }}>
        <span>0 hrs</span>
        <span>Top: {t.highest_circle_hrs} hrs</span>
      </div>
    </div>
  )
}
