export default function SCImpactImprovement() {
  const data = [
    { month: 'January', us: 38, top: 61 },
    { month: 'February', us: 52, top: 68 },
    { month: 'March', us: 62, top: 74 },
  ]
  const maxVal = 80;

  return (
    <div className="sc-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div className="sc-card-title" style={{ marginBottom: 0 }}>IMPACT IMPROVEMENT — LAST 3 MONTHS</div>
        <span style={{ fontSize: '18px', color: '#d1d5db', cursor: 'pointer', lineHeight: 1, marginTop: '-10px' }}>...</span>
      </div>

      <div style={{ display: 'flex', gap: '24px', marginBottom: '24px', fontSize: '13px', color: '#3e4943' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', background: '#1e8e6a', borderRadius: '3px' }} />
          <span>Ashoka Rising (us)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', background: '#f08c3b', borderRadius: '3px' }} />
          <span>Highest group nationally</span>
        </div>
      </div>

      <div style={{ display: 'flex', height: '240px', position: 'relative', marginTop: '10px' }}>
        <div style={{ width: '40px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: '13px', color: '#9ca3af', paddingBottom: '30px', position: 'relative', zIndex: 2 }}>
          <span>+80</span>
          <span>+60</span>
          <span>+40</span>
          <span>+20</span>
          <span>0</span>
        </div>

        <div style={{ position: 'absolute', left: '-25px', top: '50%', transform: 'translateY(-50%) rotate(-90deg)', fontSize: '13px', color: '#9ca3af', letterSpacing: '0.5px' }}>
          Impact points gained
        </div>

        <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: '30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
             {[...Array(5)].map((_, i) => (
                <div key={i} style={{ borderBottom: '1px solid #f3f4f6', height: '1px', width: '100%' }} />
             ))}
          </div>

          <div style={{ flex: 1, display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', paddingBottom: '30px', position: 'relative', zIndex: 1, paddingLeft: '10px', paddingRight: '10px' }}>
            {data.map((d, i) => (
               <div key={i} style={{ display: 'flex', gap: '14px', height: '100%', alignItems: 'flex-end', width: '25%', justifyContent: 'center' }}>
                  <div style={{ width: '45%', height: `${(d.us / maxVal) * 100}%`, background: '#1e8e6a', borderRadius: '4px 4px 0 0', position: 'relative' }}>
                    <span style={{ position: 'absolute', top: '-22px', width: '100%', textAlign: 'center', fontSize: '13px', fontWeight: 600, color: '#1e8e6a' }}>+{d.us}</span>
                  </div>
                  <div style={{ width: '45%', height: `${(d.top / maxVal) * 100}%`, background: '#f08c3b', borderRadius: '4px 4px 0 0', position: 'relative' }}>
                    <span style={{ position: 'absolute', top: '-22px', width: '100%', textAlign: 'center', fontSize: '13px', fontWeight: 600, color: '#f08c3b' }}>+{d.top}</span>
                  </div>
               </div>
            ))}
          </div>

          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '30px', display: 'flex', justifyContent: 'space-around', paddingLeft: '10px', paddingRight: '10px', alignItems: 'center' }}>
            {data.map((d, i) => (
               <div key={i} style={{ width: '25%', textAlign: 'center', fontSize: '14px', color: '#6b7280' }}>{d.month}</div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--sc-cream)', borderRadius: '8px', padding: '16px', marginTop: '20px', fontSize: '13px', color: '#3e4943', lineHeight: '1.5' }}>
        Our circle improved by <strong style={{ color: '#1e8e6a' }}>+24 points</strong> over 3 months (Jan +38 → Mar +62). The gap to the leading group has narrowed from 23 pts in January to <strong>12 pts in March</strong> — closing steadily.
      </div>
    </div>
  )
}
