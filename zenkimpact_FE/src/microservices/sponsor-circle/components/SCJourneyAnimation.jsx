import React from 'react'

export default function SCJourneyAnimation() {
  return (
    <div className="sc-journey-card sc-card" style={{ marginBottom: '24px' }}>
      <div className="sc-cinema-header" style={{ marginBottom: '32px', textAlign: 'center' }}>
         <h2 className="sc-cinema-title" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--sc-text)' }}>The Impact Journey</h2>
         <p className="sc-cinema-sub" style={{ fontSize: '14px', color: 'var(--sc-text-muted)' }}>Real-time flow of resources to graduation</p>
      </div>

      <div className="sc-literal-canvas-premium">
        {/* Background Track */}
        <div className="sc-literal-track-premium"></div>

        {/* 1. SPONSORS */}
        <div className="sc-lit-node-premium">
          <div className="sc-lit-avatar-cluster">
            <img src="https://randomuser.me/api/portraits/women/44.jpg" className="sp-av-p" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/men/32.jpg" className="sp-av-p" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/women/68.jpg" className="sp-av-p" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/men/46.jpg" className="sp-av-p" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/women/12.jpg" className="sp-av-p" alt="Sponsor" />
          </div>
          <div className="sc-lit-label-p">5 Sponsors</div>
          
          {/* Coins moving to ZenK */}
          <div className="sc-coin-stream to-zenk">
            <div className="sc-coin">₹</div>
            <div className="sc-coin" style={{ animationDelay: '0.4s' }}>₹</div>
            <div className="sc-coin" style={{ animationDelay: '0.8s' }}>₹</div>
          </div>
        </div>

        {/* 2. ZENK PLATFORM */}
        <div className="sc-lit-node-premium">
          <div className="sc-lit-zenk-hub">
            <span className="sc-lit-z-logo">ZenK</span>
          </div>
          <div className="sc-lit-label-p">Platform</div>

          {/* Coins moving to School */}
          <div className="sc-coin-stream to-school">
            <div className="sc-coin">₹</div>
            <div className="sc-coin" style={{ animationDelay: '0.4s' }}>₹</div>
            <div className="sc-coin" style={{ animationDelay: '0.8s' }}>₹</div>
          </div>
        </div>

        {/* 3. SCHOOL */}
        <div className="sc-lit-node-premium">
          <div className="sc-lit-school-hub">
            <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z" />
            </svg>
          </div>
          <div className="sc-lit-label-p">School</div>

          {/* Education Magic moving to Student */}
          <div className="sc-magic-stream to-student">
            <div className="sc-star">✨</div>
            <div className="sc-star" style={{ animationDelay: '0.5s' }}>📚</div>
            <div className="sc-star" style={{ animationDelay: '1.0s' }}>💡</div>
          </div>
        </div>

        {/* 4. STUDENT -> GRADUATE */}
        <div className="sc-lit-node-premium sc-student-terminal">
          <div className="sc-lit-student-wrapper">
            {/* Base Student Image */}
            <img src="https://randomuser.me/api/portraits/women/35.jpg" className="sc-lit-student-img base-student" alt="Student" />
            {/* Graduate Image fades over it */}
            <img src="https://randomuser.me/api/portraits/women/35.jpg" className="sc-lit-student-img grad-student" alt="Graduate" />
            <div className="sc-grad-hat">🎓</div>
          </div>
          
          <div className="sc-lit-label-p sc-dynamic-label">
            <span className="lbl-student">Student</span>
            <span className="lbl-graduate">Graduate!</span>
          </div>

          <div className="sc-lit-speech-premium">
            Thank You! ❤️
          </div>
        </div>

      </div>
    </div>
  )
}
