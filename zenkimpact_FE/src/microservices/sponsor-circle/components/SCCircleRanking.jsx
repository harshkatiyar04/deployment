import { RANKINGS } from '../data/placeholders'
import { TrophyIcon } from '@heroicons/react/24/outline'

export default function SCCircleRanking() {
  return (
    <div className="sc-card">
      <div className="sc-card-title">
        <TrophyIcon style={{ width: 16, height: 16 }} />
        ZenQ Circle Ranking
      </div>

      <table className="sc-ranking-table">
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Circle</th>
            <th style={{ width: 70 }}>ZenQ</th>
            <th style={{ width: 100 }}>City</th>
          </tr>
        </thead>
        <tbody>
          {RANKINGS.map((row) => (
            <tr key={row.rank} className={`sc-ranking-row${row.is_mine ? ' mine' : ''}`}>
              <td>
                <div className="sc-rank-cell">
                  {row.is_mine && <div className="sc-mine-accent" />}
                  <span className="sc-rank-num">{row.rank}</span>
                </div>
              </td>
              <td>
                <span style={{ fontWeight: row.is_mine ? 600 : 400 }}>{row.name}</span>
                {row.is_mine && (
                  <span
                    className="sc-badge you"
                    style={{ marginLeft: 8 }}
                  >
                    You
                  </span>
                )}
              </td>
              <td>
                <span className={`sc-ranking-zenq${row.is_mine ? ' mine' : ''}`}>
                  {row.zenq}
                </span>
              </td>
              <td>{row.city}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
