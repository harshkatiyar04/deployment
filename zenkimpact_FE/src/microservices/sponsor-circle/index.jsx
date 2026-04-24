import './sponsor-circle.css'
import { useState, useEffect } from 'react'
import SCLeftNav from './components/SCLeftNav'
import SCMetricCards from './components/SCMetricCards'
import SCBudgetTracker from './components/SCBudgetTracker'
import SCParticipation from './components/SCParticipation'
import SCStudentUpdate from './components/SCStudentUpdate'
import SCTimeOnImpact from './components/SCTimeOnImpact'
import SCCircleRanking from './components/SCCircleRanking'
import SCKiaPanel from './components/SCKiaPanel'
import SCStatementView from './components/SCStatementView'
import SCImpactImprovement from './components/SCImpactImprovement'
import SCChatMainView from './components/SCChatMainView'
import SCSponsorProfile from './components/SCSponsorProfile'
import SCImpactLeague from './components/SCImpactLeague'
import SCSettings from './components/SCSettings'
import EducationalMarketplace from '../shared/EducationalMarketplace'
import { Bars3Icon } from '@heroicons/react/24/outline'

const TABS = ['My Profile', 'My Circle', 'Marketplace', 'Impact League', 'Statement', 'Chat & Kia']

export default function SponsorCircleDashboard() {
  const [activeTab, setActiveTab] = useState('My Profile')
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  // Close menu when tab changes on mobile
  useEffect(() => {
    setIsMenuOpen(false)
  }, [activeTab])

  return (
    <div className="sc-root relative">
      <div className="sc-mobile-header">
        <img 
          src="/assets/zenk-logo.png" 
          alt="ZenK Logo" 
          style={{ height: '24px', objectFit: 'contain' }} 
        />
        <button onClick={() => setIsMenuOpen(true)} className="p-2 text-gray-600 bg-gray-100 rounded-md">
          <Bars3Icon className="w-6 h-6" />
        </button>
      </div>

      {isMenuOpen && <div className="sc-mobile-overlay" onClick={() => setIsMenuOpen(false)}></div>}

      <SCLeftNav activeTab={activeTab} setActiveTab={setActiveTab} isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />

      <main className={`sc-main${(activeTab === 'Chat & Kia' || activeTab === 'Marketplace') ? ' sc-main-chat' : ''}`}>
        <div className="sc-tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              className={`sc-tab${activeTab === tab ? ' active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'My Profile' && (
          <div className="sc-content-pad">
            <SCSponsorProfile />
          </div>
        )}

        {activeTab === 'My Circle' && (
          <div className="sc-content-pad" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <SCMetricCards />
            <SCBudgetTracker />
            <SCParticipation />
            <SCImpactImprovement />
            <div className="sc-half-grid">
              <SCStudentUpdate />
              <SCTimeOnImpact />
            </div>
            <SCCircleRanking />
          </div>
        )}

        {activeTab === 'Impact League' && (
          <div className="sc-content-pad">
            <SCImpactLeague />
          </div>
        )}

        {activeTab === 'Marketplace' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <EducationalMarketplace isLeader={false} />
          </div>
        )}

        {activeTab === 'Chat & Kia' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <SCChatMainView circleId="481eba8f-778d-4618-8f9e-6e6b263d89a0" userRole="sponsor" />
          </div>
        )}

        {activeTab === 'Statement' && (
          <div className="sc-content-pad">
            <SCStatementView />
          </div>
        )}


        {activeTab === 'Settings' && (
          <div className="sc-content-pad">
            <SCSettings />
          </div>
        )}
      </main>

      {!['Chat & Kia', 'My Profile', 'Settings', 'Marketplace'].includes(activeTab) && <SCKiaPanel />}
    </div>
  )
}
