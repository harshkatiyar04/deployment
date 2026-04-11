import './sponsor-circle.css'
import { useState } from 'react'
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

const TABS = ['My Profile', 'My Circle', 'Impact League', 'Statement', 'Chat & Kia']

export default function SponsorCircleDashboard() {
  const [activeTab, setActiveTab] = useState('My Profile')

  return (
    <div className="sc-root">
      <SCLeftNav activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className={`sc-main${activeTab === 'Chat & Kia' ? ' sc-main-chat' : ''}`}>
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
          <div style={{ padding: '0 24px 24px' }}>
            <SCSponsorProfile />
          </div>
        )}

        {activeTab === 'My Circle' && (
          <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
          <div style={{ padding: '0 24px 24px' }}>
            <SCImpactLeague />
          </div>
        )}

        {activeTab === 'Chat & Kia' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <SCChatMainView circleId="481eba8f-778d-4618-8f9e-6e6b263d89a0" userRole="sponsor" />
          </div>
        )}

        {activeTab === 'Statement' && (
          <div style={{ padding: '0 24px 24px' }}>
            <SCStatementView />
          </div>
        )}


        {activeTab === 'Settings' && (
          <div style={{ padding: '0 24px 24px' }}>
            <SCSettings />
          </div>
        )}
      </main>

      {activeTab !== 'Chat & Kia' && activeTab !== 'My Profile' && activeTab !== 'Settings' && <SCKiaPanel />}
    </div>
  )
}
