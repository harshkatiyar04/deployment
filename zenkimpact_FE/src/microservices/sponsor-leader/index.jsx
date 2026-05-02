import '../sponsor-circle/sponsor-circle.css'
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import SCLeftNav from '../sponsor-circle/components/SCLeftNav'
import SCMetricCards from '../sponsor-circle/components/SCMetricCards'
import SCBudgetTracker from '../sponsor-circle/components/SCBudgetTracker'
import SCParticipation from '../sponsor-circle/components/SCParticipation'
import SCStudentUpdate from '../sponsor-circle/components/SCStudentUpdate'
import SCTimeOnImpact from '../sponsor-circle/components/SCTimeOnImpact'
import SCCircleRanking from '../sponsor-circle/components/SCCircleRanking'
import SCKiaPanel from '../sponsor-circle/components/SCKiaPanel'
import SCStatementView from '../sponsor-circle/components/SCStatementView'
import SCImpactImprovement from '../sponsor-circle/components/SCImpactImprovement'
import SCChatMainView from '../sponsor-circle/components/SCChatMainView'
import SCSponsorProfile from '../sponsor-circle/components/SCSponsorProfile'
import SCImpactLeague from '../sponsor-circle/components/SCImpactLeague'
import SCSettings from '../sponsor-circle/components/SCSettings'
import SCMemberContributions from '../sponsor-circle/components/SCMemberContributions'
import SCVendorPayments from '../sponsor-circle/components/SCVendorPayments'
import SCSchoolComm from './SCSchoolComm'
import EducationalMarketplace from '../shared/EducationalMarketplace'
import VendorDashboardView from '../shared/VendorDashboardView'
import { Bars3Icon } from '@heroicons/react/24/outline'

const TABS = ['My Profile', 'My Circle', 'Marketplace', 'Circle Orders', 'Member Contributions', 'Vendor Payments', 'Impact League', 'School Comm', 'Statement', 'Chat & Kia']

export default function SponsorLeaderDashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'My Profile'
  const setActiveTab = (tab) => setSearchParams({ tab })
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

      <SCLeftNav activeTab={activeTab} setActiveTab={setActiveTab} isLeader={true} isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />

      <main className={`sc-main${(activeTab === 'Chat & Kia' || activeTab === 'School Comm' || activeTab === 'Marketplace' || activeTab === 'Circle Orders') ? ' sc-main-chat' : ''}`}>
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
            <SCSponsorProfile isLeader={true} />
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

        {activeTab === 'Member Contributions' && (
          <div className="sc-content-pad">
            <SCMemberContributions />
          </div>
        )}

        {activeTab === 'Vendor Payments' && (
          <div className="sc-content-pad">
            <SCVendorPayments />
          </div>
        )}

        {activeTab === 'Impact League' && (
          <div className="sc-content-pad">
            <SCImpactLeague />
          </div>
        )}

        {activeTab === 'School Comm' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <SCSchoolComm />
          </div>
        )}

        {activeTab === 'Chat & Kia' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <SCChatMainView circleId="481eba8f-778d-4618-8f9e-6e6b263d89a0" userRole="sponsor_leader" isLeader={true} />
          </div>
        )}

        {activeTab === 'Marketplace' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <EducationalMarketplace isLeader={true} />
          </div>
        )}

        {activeTab === 'Circle Orders' && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <VendorDashboardView />
          </div>
        )}

        {activeTab === 'Statement' && (
          <div className="sc-content-pad">
            <SCStatementView />
          </div>
        )}

        {activeTab === 'Settings' && (
          <div className="sc-content-pad">
            <SCSettings isLeader={true} />
          </div>
        )}
      </main>

      {!['Chat & Kia', 'My Profile', 'Settings', 'School Comm', 'Marketplace', 'Circle Orders'].includes(activeTab) && <SCKiaPanel />}
    </div>
  )
}
