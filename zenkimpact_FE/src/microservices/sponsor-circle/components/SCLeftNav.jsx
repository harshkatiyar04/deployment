import { Link, useLocation } from 'react-router-dom'
import { USER_PROFILE, LEADER_PROFILE } from '../data/placeholders'
import {
  Squares2X2Icon,
  TrophyIcon,
  UserGroupIcon,
  DocumentTextIcon,
  Cog8ToothIcon,
  CurrencyDollarIcon,
  UsersIcon,
  AcademicCapIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  ShoppingBagIcon,
  BuildingStorefrontIcon
} from '@heroicons/react/24/outline'

const MEMBER_NAV = [
  { label: 'Dashboard', tab: 'My Profile', icon: Squares2X2Icon },
  { label: 'Marketplace', tab: 'Marketplace', icon: ShoppingBagIcon },
  { label: 'Chat & Kia', tab: 'Chat & Kia', icon: ChatBubbleLeftRightIcon },
  { label: 'Impact League', tab: 'Impact League', icon: TrophyIcon },
  { label: 'My Circle', tab: 'My Circle', icon: UserGroupIcon },
  { label: 'Statement', tab: 'Statement', icon: DocumentTextIcon },
  { label: 'Settings', tab: 'Settings', icon: Cog8ToothIcon },
]

const LEADER_NAV = [
  { label: 'Dashboard', tab: 'My Profile', icon: Squares2X2Icon },
  { label: 'Marketplace', tab: 'Marketplace', icon: ShoppingBagIcon },
  { label: 'Vendor Dashboard', tab: 'Vendor Dashboard', icon: BuildingStorefrontIcon },
  { label: 'Chat & Kia', tab: 'Chat & Kia', icon: ChatBubbleLeftRightIcon },
  { label: 'Member Contributions', tab: 'Member Contributions', icon: UsersIcon },
  { label: 'Vendor Payments', tab: 'Vendor Payments', icon: CurrencyDollarIcon },
  { label: 'Impact League', tab: 'Impact League', icon: TrophyIcon },
  { label: 'School Comm', tab: 'School Comm', icon: AcademicCapIcon },
  { label: 'My Circle', tab: 'My Circle', icon: UserGroupIcon },
  { label: 'Statement', tab: 'Statement', icon: DocumentTextIcon },
  { label: 'Settings', tab: 'Settings', icon: Cog8ToothIcon },
]

export default function SCLeftNav({ activeTab, setActiveTab, isLeader = false, isOpen = false, onClose }) {
  const location = useLocation()
  const NAV_ITEMS = isLeader ? LEADER_NAV : MEMBER_NAV
  const profile = isLeader ? LEADER_PROFILE : USER_PROFILE

  const profileTab = 'My Profile'

  return (
    <nav className={`sc-left-nav ${isOpen ? 'open' : ''}`}>
      <button className="sc-mobile-close" onClick={onClose}>
        <XMarkIcon className="w-6 h-6" />
      </button>
      <div className="sc-logo">
        <img 
          src="/assets/zenk-logo.png" 
          alt="ZenK Logo" 
          style={{ height: '32px', objectFit: 'contain', marginBottom: '8px' }} 
        />
        <span className="sc-role-badge" style={isLeader ? { background: '#f59e0b', color: '#0f172a' } : {}}>
          {isLeader ? 'Circle Coordinator' : 'Sponsor Circle'}
        </span>
      </div>

      <div 
        className={`sc-profile ${activeTab === profileTab ? 'active' : ''}`} 
        onClick={() => setActiveTab(profileTab)}
        style={{
          cursor: 'pointer', transition: 'all 0.2s',
          border: activeTab === profileTab
            ? isLeader ? '1px solid #f59e0b' : '1px solid var(--sc-green)'
            : '1px solid transparent',
        }}
      >
        <div className="sc-avatar" style={isLeader ? { background: '#f59e0b', color: '#0f172a' } : {}}>
          {profile.initials}
          <span className="sc-avatar-dot" />
        </div>
        <div>
          <div className="sc-profile-name">
            {profile.name}
            {isLeader && (
              <span style={{
                fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '3px',
                background: '#f59e0b', color: '#0f172a', marginLeft: '6px', verticalAlign: 'middle',
              }}>LEADER</span>
            )}
          </div>
          <div className="sc-profile-sub">{profile.circle}</div>
        </div>
      </div>

      <div className="sc-nav-items">
        {NAV_ITEMS.map((item) => {
          const IconComponent = item.icon
          const isActive = activeTab === item.tab

          return (
            <button
              key={item.tab}
              onClick={() => setActiveTab(item.tab)}
              className={`sc-nav-item${isActive ? ' active' : ''}`}
            >
              <IconComponent className="sc-nav-icon" />
              {item.label}
            </button>
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
