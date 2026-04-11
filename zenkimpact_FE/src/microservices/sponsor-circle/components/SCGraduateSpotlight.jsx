import React from 'react'

export default function SCGraduateSpotlight() {
  return (
    <div className="sc-spotlight-section">
      <div className="sc-spotlight-content">
        {/* Graduate Avatar */}
        <div className="sc-spotlight-avatar-wrap">
          <img 
            src="/media/graduate_avatar.png" 
            alt="Ananya D." 
            className="sc-spotlight-avatar"
          />
        </div>

        {/* Large Quote Marks Container */}
        <div className="sc-spotlight-quote-container">
          <div className="sc-spotlight-quote-mark">“</div>
          
          <p className="sc-spotlight-quote-text">
            Your belief in me was the bridge I needed to cross the impossible. Today, I stand as a graduate, but more importantly, I stand as proof that curation and care can change a life forever.
          </p>

          <div className="sc-spotlight-attribution">
            <div className="sc-spotlight-divider"></div>
            <h3 className="sc-spotlight-name">Ananya D.</h3>
            <p className="sc-spotlight-subtitle">B.TECH, COMPUTER SCIENCE CLASS OF 2024</p>
          </div>
        </div>
      </div>
    </div>
  )
}
