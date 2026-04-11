import { Link, useLocation } from 'react-router-dom'
import { USER_PROFILE } from '../data/placeholders'
import {
  Squares2X2Icon,
  TrophyIcon,
  UserGroupIcon,
  DocumentTextIcon,
  Cog8ToothIcon
} from '@heroicons/react/24/outline'

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/sponsor-circle', icon: Squares2X2Icon },
  { label: 'Impact League', path: '/sponsor-circle/impact-league', icon: TrophyIcon },
  { label: 'My Circle', path: '/sponsor-circle/circle', icon: UserGroupIcon },
  { label: 'Statement', path: '/sponsor-circle/statement', icon: DocumentTextIcon },
  { label: 'Settings', path: '/sponsor-circle/settings', icon: Cog8ToothIcon },
]

export default function SCLeftNav({ activeTab, setActiveTab }) {
  const location = useLocation()

  const handleNavClick = (e, item) => {
    // If it's a dashboard internal tab, intercept the click
    if (item.label === 'Dashboard' || item.label === 'My Circle') {
      e.preventDefault()
      setActiveTab('My Circle')
    } else if (item.label === 'Impact League') {
      e.preventDefault()
      setActiveTab('Impact League')
    } else if (item.label === 'Statement') {
      e.preventDefault()
      setActiveTab('Statement')
    } else if (item.label === 'Settings') {
      e.preventDefault()
      setActiveTab('Settings')
    }
  }

  return (
    <nav className="sc-left-nav">
      <div className="sc-logo">
        <div className="sc-logo-text">
          <span className="sc-logo-zen">ZEN</span>
          <span className="sc-logo-k">K</span>
        </div>
        <span className="sc-role-badge">Sponsor Circle</span>
      </div>

      <div 
        className={`sc-profile ${activeTab === 'My Profile' ? 'active' : ''}`} 
        onClick={() => setActiveTab('My Profile')}
        style={{ cursor: 'pointer', transition: 'all 0.2s', border: activeTab === 'My Profile' ? '1px solid var(--sc-green)' : '1px solid transparent' }}
      >
        <div className="sc-avatar">
          {USER_PROFILE.initials}
          <span className="sc-avatar-dot" />
        </div>
        <div>
          <div className="sc-profile-name">{USER_PROFILE.name}</div>
          <div className="sc-profile-sub">{USER_PROFILE.circle}</div>
        </div>
      </div>

      <div className="sc-nav-items">
        {NAV_ITEMS.map((item) => {
          const IconComponent = item.icon
          const isActive = (item.label === 'Dashboard' && activeTab === 'My Circle') || 
                          (item.label === 'My Circle' && activeTab === 'My Circle') ||
                          (item.label === 'Impact League' && activeTab === 'Impact League') ||
                          (item.label === 'Statement' && activeTab === 'Statement') ||
                          (item.label === 'Settings' && activeTab === 'Settings') ||
                          (location.pathname === item.path)

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={(e) => handleNavClick(e, item)}
              className={`sc-nav-item${isActive ? ' active' : ''}`}
            >
              <IconComponent className="sc-nav-icon" />
              {item.label}
            </Link>
          )
        })}
      </div>



      <div className="sc-nav-back">
        <Link to="/dashboard" className="sc-back-btn">
          ← Main Dashboard
        </Link>
      </div>
    </nav>
  )
}
