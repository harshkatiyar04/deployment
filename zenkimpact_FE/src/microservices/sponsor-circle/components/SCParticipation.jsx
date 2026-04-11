import { PARTICIPATION } from '../data/placeholders'

export default function SCParticipation() {
  const { members, circle_avg_pct, leader_name, leader_pct } = PARTICIPATION

  return (
    <div className="sc-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="sc-card-title">Participation — {members.length} Members</div>
        <span style={{ fontSize: 11, color: '#6b7280' }}>Circle avg: {circle_avg_pct}%</span>
      </div>

      {members.map((m) => {
        const isYou = m.badge === 'you'
        const isTop = m.badge === 'top'
        return (
          <div key={m.name} className={`sc-member-row${isYou ? ' you-row' : ''}`}>
            <div className={`sc-member-avatar-sm${isYou ? ' you-av' : ''}`}>{m.initials}</div>
            <div className="sc-member-name">
              {m.name}
              {isTop && <span className="sc-badge top">Top</span>}
              {isYou && <span className="sc-badge you">You</span>}
            </div>
            <div className="sc-bar-track">
              <div
                className={`sc-bar-fill${isYou ? ' orange' : ''}`}
                style={{ width: `${m.participation_pct}%` }}
              />
            </div>
            <div className={`sc-member-pct${isYou ? ' orange' : ' green'}`}>{m.participation_pct}%</div>
          </div>
        )
      })}

      <div className="sc-participation-footer">
        Circle average: {circle_avg_pct}% · Leading member:{' '}
        <a href="#">{leader_name} at {leader_pct}%</a>
      </div>
    </div>
  )
}
