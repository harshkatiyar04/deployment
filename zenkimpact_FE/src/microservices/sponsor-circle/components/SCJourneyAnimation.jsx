import React from 'react'

export default function SCJourneyAnimation() {
  return (
    <div className="sc-journey-card sc-card" style={{ marginBottom: '24px' }}>
      <div className="sc-cinema-header" style={{ marginBottom: '24px' }}>
         <div className="sc-cinema-title">The Impact Journey</div>
         <div className="sc-cinema-sub">The flow of real impact from sponsors to graduation</div>
      </div>

      <div className="sc-literal-canvas">
        {/* The Connection Track - now extends behind all nodes */}
        <div className="sc-literal-track"></div>

        {/* 1. SPONSORS */}
        <div className="sc-lit-node sc-lit-sponsors">
          <div className="sc-lit-cluster">
            <img src="https://randomuser.me/api/portraits/women/44.jpg" className="sp-av av-1" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/men/32.jpg" className="sp-av av-2" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/women/68.jpg" className="sp-av av-3" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/men/46.jpg" className="sp-av av-4" alt="Sponsor" />
            <img src="https://randomuser.me/api/portraits/women/12.jpg" className="sp-av av-5" alt="Sponsor" />
          </div>
          <div className="sc-lit-label">5 Sponsors</div>
          
          <div className="sc-lit-coin-transfer t1">
            <div className="real-currency">$</div>
            <div className="real-currency" style={{ animationDelay: '0.2s'}}>$</div>
            <div className="real-currency" style={{ animationDelay: '0.4s'}}>$</div>
          </div>
        </div>

        {/* 2. ZENK */}
        <div className="sc-lit-node sc-lit-zenk">
          <div className="sc-lit-zenk-brand">
            <h1 className="sc-lit-brand-text">ZenK</h1>
          </div>
          <div className="sc-lit-label">Platform</div>
          
          <div className="sc-lit-coin-transfer t2">
            <div className="real-currency">$</div>
            <div className="real-currency" style={{ animationDelay: '0.2s'}}>$</div>
            <div className="real-currency" style={{ animationDelay: '0.4s'}}>$</div>
          </div>
        </div>

        {/* 3. STUDENT */}
        <div className="sc-lit-node sc-lit-student-node">
          <img src="/media/custom_student_avatar.png" className="sc-lit-student-av" alt="Student" />
          <div className="sc-lit-label">Student</div>
        </div>

        {/* 4. COLLEGE */}
        <div className="sc-lit-node sc-lit-college">
          <div className="sc-lit-college-icon">
             <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z" />
             </svg>
          </div>
          <div className="sc-lit-label">College</div>
        </div>

        {/* 5. GRADUATE */}
        <div className="sc-lit-node sc-lit-graduate-node">
          <img src="/media/custom_student_avatar.png" className="sc-lit-graduate-av" alt="Graduate" />
          <div className="sc-lit-label">Graduate</div>
          <div className="sc-lit-speech-bubble">
            Thank You! ❤️
          </div>
        </div>

      </div>
    </div>
  )
}
