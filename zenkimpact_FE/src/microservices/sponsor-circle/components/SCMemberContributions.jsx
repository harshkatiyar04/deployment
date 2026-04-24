import { MEMBER_CONTRIBUTIONS, TRANSACTION_HISTORY } from '../data/placeholders'

const fmt = (n) => '₹' + n.toLocaleString('en-IN')

const BADGE_STYLES = {
  leader: { bg: '#00694c', color: '#fff', text: 'Coordinator' },
  csr: { bg: '#f08c3b', color: '#fff', text: 'CSR' },
}

export default function SCMemberContributions() {
  const totalCollected = MEMBER_CONTRIBUTIONS.reduce((s, m) => s + m.totalContributed, 0)
  const sponsorDeposits = MEMBER_CONTRIBUTIONS.filter(m => m.badge !== 'csr').reduce((s, m) => s + m.totalContributed, 0)
  const csrAmount = MEMBER_CONTRIBUTIONS.filter(m => m.badge === 'csr').reduce((s, m) => s + m.totalContributed, 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Fund Summary Card */}
      <div className="sc-card">
        <div className="sc-card-title">Fund Collection Overview</div>
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>Funded so far</span>
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--sc-green-dark)', lineHeight: 1 }}>83%</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>60% activation</span>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>{fmt(totalCollected)} collected<br/><span style={{ fontSize: '11px', color: 'var(--sc-text-muted)', fontWeight: 400 }}>of ₹1,50,000 annual budget</span></span>
          </div>
          <div className="sc-progress-bar" style={{ marginTop: '8px', height: '10px' }}>
            <div className="sc-progress-fill sc-progress-green" style={{ width: '83%' }}></div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--sc-text-muted)', marginTop: '4px' }}>
            <span>₹0</span>
            <span>{fmt(90000)} / activated</span>
            <span>₹1,50,000</span>
          </div>
        </div>

        {/* Breakdown boxes */}
        <div className="sc-fund-boxes" style={{ display: 'grid', gap: '12px', marginTop: '20px' }}>
          <div style={{ background: 'var(--sc-cream)', padding: '14px', borderRadius: '10px', border: '1px solid var(--sc-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--sc-green)' }}></div>
              <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>Sponsor deposits</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--sc-text-dark)' }}>{fmt(sponsorDeposits)}</div>
          </div>
          <div style={{ background: 'var(--sc-cream)', padding: '14px', borderRadius: '10px', border: '1px solid var(--sc-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f08c3b' }}></div>
              <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>CSR — TCS</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--sc-text-dark)' }}>{fmt(csrAmount)}</div>
          </div>
          <div style={{ background: 'var(--sc-cream)', padding: '14px', borderRadius: '10px', border: '1px solid var(--sc-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#6366f1' }}></div>
              <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>Interest earned</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--sc-text-dark)' }}>{fmt(4000)}</div>
          </div>
        </div>
      </div>

      {/* CIRCLE MEMBERS Grid */}
      <div className="sc-card">
        <div className="sc-card-title" style={{ marginBottom: '16px' }}>CIRCLE MEMBERS ({MEMBER_CONTRIBUTIONS.length})</div>
        <div className="sc-members-grid" style={{ display: 'grid', gap: '12px' }}>
          {MEMBER_CONTRIBUTIONS.map((m, i) => {
            const badgeInfo = BADGE_STYLES[m.badge]
            return (
              <div key={i} style={{
                background: i === 0 ? 'linear-gradient(135deg, #0a2e1f, #134e3a)' : 'var(--sc-cream)',
                border: i === 0 ? '2px solid var(--sc-green)' : '1px solid var(--sc-border)',
                borderRadius: '12px',
                padding: '16px',
                color: i === 0 ? '#fff' : 'var(--sc-text-dark)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '50%',
                    background: i === 0 ? 'var(--sc-green)' : '#e8f5f0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '12px', fontWeight: 700,
                    color: i === 0 ? '#fff' : 'var(--sc-green-dark)',
                  }}>{m.initials}</div>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {m.name}
                      {badgeInfo && (
                        <span style={{ fontSize: '9px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: badgeInfo.bg, color: badgeInfo.color }}>{badgeInfo.text}</span>
                      )}
                    </div>
                    <div style={{ fontSize: '11px', opacity: 0.7 }}>{m.role}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '10px', opacity: 0.6, marginBottom: '2px' }}>ZEQ</div>
                    <div className="sc-progress-bar" style={{ width: '80px', height: '4px' }}>
                      <div className="sc-progress-fill sc-progress-green" style={{ width: `${m.zenq * 100}%` }}></div>
                    </div>
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 700, color: i === 0 ? '#5eead4' : 'var(--sc-green)' }}>{m.zenq.toFixed(2)}</div>
                </div>
                <div style={{ fontSize: '11px', marginTop: '8px', opacity: 0.7 }}>
                  Total: {fmt(m.totalContributed)} • This month: {fmt(m.thisMonth)}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* TRANSACTION HISTORY */}
      <div className="sc-card sc-txn-card">
        <div className="sc-card-title" style={{ marginBottom: '16px' }}>TRANSACTION HISTORY</div>
        <div className="sc-txn-wrapper" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sc-txn-row-header" style={{ display: 'grid', gap: '12px', padding: '8px 0', borderBottom: '1px solid var(--sc-border)', fontSize: '11px', fontWeight: 700, color: 'var(--sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            <span>Date</span>
            <span>Contributor</span>
            <span>Type</span>
            <span style={{ textAlign: 'right' }}>Amount</span>
          </div>
          {TRANSACTION_HISTORY.map((txn, i) => (
            <div key={i} className="sc-txn-row-item" style={{ display: 'grid', gap: '12px', padding: '12px 0', borderBottom: i < TRANSACTION_HISTORY.length - 1 ? '1px solid var(--sc-border)' : 'none', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--sc-text-muted)' }}>{txn.date}</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>{txn.contributor}</span>
              <span>
                <span style={{ fontSize: '11px', fontWeight: 600, padding: '3px 8px', borderRadius: '4px', background: txn.typeColor, color: '#1a1a1a' }}>{txn.type}</span>
              </span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--sc-green)', textAlign: 'right' }}>+{fmt(txn.amount)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
