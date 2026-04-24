import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePersona } from '../contexts/PersonaContext'
import { useNotifications } from '../contexts/NotificationContext'
import NotificationModal from './NotificationModal'
import {
  BellIcon,
  QuestionMarkCircleIcon,
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
  PhoneIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  XMarkIcon,
  AcademicCapIcon,
  BuildingOfficeIcon,
  ShoppingBagIcon,
  ShieldCheckIcon,
  ArrowsRightLeftIcon,
  Bars3Icon
} from '@heroicons/react/24/outline'

function Header({ onMenuToggle }) {
  const navigate = useNavigate()
  const { activePersona, switchPersona, getPersonaLabel } = usePersona()
  const { notifications, unreadCount, markAsRead } = useNotifications()
  const [activeDropdown, setActiveDropdown] = useState(null)
  const [isNotificationModalOpen, setIsNotificationModalOpen] = useState(false)
  const notificationRef = useRef(null)
  const supportRef = useRef(null)
  const helpRef = useRef(null)
  const chatbotRef = useRef(null)
  const profileRef = useRef(null)

  const isAdminLoggedIn = () => {
    return localStorage.getItem('isAdmin') === 'true'
  }

  const dropdownRefs = {
    notification: notificationRef,
    support: supportRef,
    help: helpRef,
    chatbot: chatbotRef,
    profile: profileRef
  }

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (activeDropdown) {
        const activeRef = dropdownRefs[activeDropdown]
        if (activeRef?.current && !activeRef.current.contains(event.target)) {
          setActiveDropdown(null)
        }
      }
    }

    if (activeDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [activeDropdown])

  const toggleDropdown = (dropdown) => {
    setActiveDropdown(activeDropdown === dropdown ? null : dropdown)
  }

  const handleSignOut = () => {
    localStorage.removeItem('isAdmin')
    // Dispatch custom event to notify NotificationContext
    window.dispatchEvent(new Event('adminLogout'))
    navigate('/login')
  }

  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id)
    }
    setIsNotificationModalOpen(true)
    setActiveDropdown(null)
  }

  const handleViewAllNotifications = () => {
    setIsNotificationModalOpen(true)
    setActiveDropdown(null)
  }

  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    })
  }

  const iconButtons = [
    {
      id: 'notification',
      icon: BellIcon,
      label: 'Notifications',
      badge: isAdminLoggedIn() && unreadCount > 0 ? unreadCount : null,
      dropdown: (
        <div className="py-2 min-w-[320px]">
          <div className="px-4 py-2 border-b border-gray-200 flex justify-between items-center">
            <h3 className="font-semibold text-gray-900">Notifications</h3>
            {isAdminLoggedIn() && unreadCount > 0 && (
              <span className="text-xs text-gray-500">{unreadCount} unread</span>
            )}
          </div>
          <div className="max-h-64 overflow-y-auto">
            {!isAdminLoggedIn() ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-gray-500">Login as admin to view notifications</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-gray-500">No notifications</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {notifications.slice(0, 5).map((notification) => (
                  <button
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                      !notification.is_read ? 'bg-blue-50/50' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-500 mb-1">
                          {notification.notification_type}
                        </p>
                        <p className="text-sm font-semibold text-gray-900 line-clamp-1 mb-1">
                          {notification.title}
                        </p>
                        <p className="text-xs text-gray-600 line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {formatDate(notification.created_at)}
                        </p>
                      </div>
                      {!notification.is_read && (
                        <span className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          {isAdminLoggedIn() && notifications.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-200">
              <button
                onClick={handleViewAllNotifications}
                className="text-sm text-blue-600 hover:text-blue-700 w-full text-center"
              >
                View all notifications
              </button>
            </div>
          )}
        </div>
      )
    },
    {
      id: 'support',
      icon: PhoneIcon,
      label: 'Support',
      dropdown: (
        <div className="py-2 min-w-[240px]">
          <div className="px-4 py-2 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Support</h3>
          </div>
          <div className="py-2">
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Contact Support Team
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Submit a Ticket
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Support Documentation
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              System Status
            </a>
          </div>
        </div>
      )
    },
    {
      id: 'help',
      icon: QuestionMarkCircleIcon,
      label: 'Help',
      dropdown: (
        <div className="py-2 min-w-[240px]">
          <div className="px-4 py-2 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Help Center</h3>
          </div>
          <div className="py-2">
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Getting Started Guide
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              FAQs
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Video Tutorials
            </a>
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              User Manual
            </a>
          </div>
        </div>
      )
    },
    {
      id: 'chatbot',
      icon: ChatBubbleLeftRightIcon,
      label: 'Chatbot',
      dropdown: (
        <div className="py-2 min-w-[300px]">
          <div className="px-4 py-2 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">AI Assistant</h3>
          </div>
          <div className="px-4 py-4">
            <div className="bg-blue-50 rounded-lg p-3 mb-3">
              <p className="text-sm text-gray-700">Hello! How can I help you today?</p>
            </div>
            <div className="space-y-2">
              <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded border border-gray-200">
                How do I create a sponsor circle?
              </button>
              <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded border border-gray-200">
                How to track impact missions?
              </button>
              <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded border border-gray-200">
                Marketplace guide
              </button>
            </div>
          </div>
          <div className="px-4 py-2 border-t border-gray-200">
            <button className="text-sm text-blue-600 hover:text-blue-700 w-full text-center">
              Start New Conversation
            </button>
          </div>
        </div>
      )
    },
    {
      id: 'profile',
      icon: UserCircleIcon,
      label: 'Profile',
      dropdown: (
        <div className="py-2 min-w-[280px]">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                <UserIcon className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-900">Admin User</p>
                <p className="text-xs text-gray-500">admin@zenk.com</p>
              </div>
            </div>
          </div>
          
          {/* Current Persona Display */}
          <div className="px-4 py-2 border-b border-gray-200">
            <p className="text-xs text-gray-500 mb-2">Current View</p>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                {getPersonaLabel()}
              </span>
            </div>
          </div>

          {/* Persona Switching */}
          <div className="px-4 py-2 border-b border-gray-200">
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
              <ArrowsRightLeftIcon className="w-3 h-3" />
              Switch Persona View
            </p>
            
            {/* Student Personas */}
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-700 mb-1">Student</p>
              <div className="space-y-1">
                <button
                  onClick={() => {
                    switchPersona('student', 'primary')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'student' && activePersona.subtype === 'primary'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <AcademicCapIcon className="w-4 h-4" />
                  Primary School (6-12)
                </button>
                <button
                  onClick={() => {
                    switchPersona('student', 'secondary')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'student' && activePersona.subtype === 'secondary'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <AcademicCapIcon className="w-4 h-4" />
                  Secondary School (13-18)
                </button>
                <button
                  onClick={() => {
                    switchPersona('student', 'university')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'student' && activePersona.subtype === 'university'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <AcademicCapIcon className="w-4 h-4" />
                  University Student (18+)
                </button>
              </div>
            </div>

            {/* Sponsor Personas */}
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-700 mb-1">Sponsor</p>
              <div className="space-y-1">
                <button
                  onClick={() => {
                    switchPersona('sponsor', 'corporate')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'sponsor' && activePersona.subtype === 'corporate'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <BuildingOfficeIcon className="w-4 h-4" />
                  Corporate Sponsor
                </button>
                <button
                  onClick={() => {
                    switchPersona('sponsor', 'individual')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'sponsor' && activePersona.subtype === 'individual'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <UserIcon className="w-4 h-4" />
                  Individual Sponsor
                </button>
                <button
                  onClick={() => {
                    switchPersona('sponsor', 'ngo')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'sponsor' && activePersona.subtype === 'ngo'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <BuildingOfficeIcon className="w-4 h-4" />
                  NGO Partner
                </button>
              </div>
            </div>

            {/* Supplier Personas */}
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-700 mb-1">Supplier</p>
              <div className="space-y-1">
                <button
                  onClick={() => {
                    switchPersona('supplier', 'service')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'supplier' && activePersona.subtype === 'service'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <AcademicCapIcon className="w-4 h-4" />
                  Service Provider
                </button>
                <button
                  onClick={() => {
                    switchPersona('supplier', 'product')
                    setActiveDropdown(null)
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                    activePersona.type === 'supplier' && activePersona.subtype === 'product'
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <ShoppingBagIcon className="w-4 h-4" />
                  Product Supplier
                </button>
              </div>
            </div>

            {/* Admin */}
            <div>
              <button
                onClick={() => {
                  switchPersona('admin')
                  setActiveDropdown(null)
                }}
                className={`w-full text-left px-3 py-1.5 text-xs rounded flex items-center gap-2 ${
                  activePersona.type === 'admin'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <ShieldCheckIcon className="w-4 h-4" />
                Platform Administrator
              </button>
            </div>
          </div>

          {/* Profile Actions */}
          <div className="border-t border-gray-200 mt-2 pt-2">
            <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2">
              <UserIcon className="w-4 h-4" />
              My Profile
            </a>
            <button
              onClick={handleSignOut}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
            >
              <ArrowRightOnRectangleIcon className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      )
    }
  ]

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
      <div className="px-3 md:px-6 py-2 flex items-center justify-between">
        {/* Left - Hamburger + ZenK Logo */}
        <div className="flex items-center gap-2">
          {/* Hamburger – mobile only */}
          <button
            onClick={onMenuToggle}
            className="md:hidden p-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            aria-label="Toggle menu"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>
          <img 
            src="/assets/zenk-logo.png" 
            alt="ZenK Logo" 
            style={{ height: '32px', objectFit: 'contain' }} 
            className="cursor-pointer"
            onClick={() => navigate('/')}
          />
        </div>

        {/* Right - Icons */}
        <div className="flex items-center gap-1 md:gap-2">
          {iconButtons.map(({ id, icon: Icon, label, badge, dropdown }) => (
            <div key={id} className="relative" ref={dropdownRefs[id]}>
              <button
                onClick={() => toggleDropdown(id)}
                className="relative p-1.5 md:p-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors duration-200"
                aria-label={label}
              >
                <Icon className="w-5 h-5 md:w-6 md:h-6" />
                {badge && (
                  <span className="absolute top-0.5 right-0.5 md:top-1 md:right-1 w-4 h-4 md:w-5 md:h-5 bg-red-500 text-white text-[10px] md:text-xs font-bold rounded-full flex items-center justify-center">
                    {badge}
                  </span>
                )}
              </button>

              {/* Dropdown */}
              {activeDropdown === id && (
                <div className="absolute right-0 mt-2 w-auto max-w-[calc(100vw-24px)] bg-white rounded-xl shadow-lg border border-gray-200 z-50">
                  {dropdown}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Notification Modal */}
      {isAdminLoggedIn() && (
        <NotificationModal
          isOpen={isNotificationModalOpen}
          onClose={() => setIsNotificationModalOpen(false)}
        />
      )}
    </header>
  )
}

export default Header

