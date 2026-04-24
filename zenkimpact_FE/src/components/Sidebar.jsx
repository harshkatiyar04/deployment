import { NavLink } from 'react-router-dom'
import { usePersona } from '../contexts/PersonaContext'
import {
  HomeIcon,
  UserGroupIcon,
  TrophyIcon,
  ShoppingBagIcon,
  AcademicCapIcon,
  CurrencyDollarIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  UsersIcon,
  BuildingStorefrontIcon,
  ShieldCheckIcon,
  BookOpenIcon,
  DevicePhoneMobileIcon,
  SparklesIcon,
  RectangleGroupIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

function Sidebar({ isOpen, onClose }) {
  const { activePersona, isStudent, isSponsor, isSupplier, isAdmin } = usePersona()

  // Student Navigation Items
  const studentNavItems = [
    { path: '/dashboard/home', icon: HomeIcon, label: 'Home' },
    { path: '/dashboard', icon: SparklesIcon, label: 'Dashboard' },
    { path: '/dashboard/resources', icon: BookOpenIcon, label: 'Resources' },
    { path: '/dashboard/sessions', icon: ChatBubbleLeftRightIcon, label: 'Sessions' },
    { path: '/dashboard/progress', icon: ChartBarIcon, label: 'Progress' },
    { path: '/dashboard/marketplace', icon: ShoppingBagIcon, label: 'Marketplace' },
    { path: '/dashboard/chat-bans', icon: ShieldCheckIcon, label: 'Chat Bans' },
    { path: '/chat-demo', icon: ChatBubbleLeftRightIcon, label: 'Chat Demo' }
  ]

  // Sponsor Navigation Items
  const sponsorNavItems = [
    { path: '/dashboard/home', icon: HomeIcon, label: 'Home' },
    { path: '/dashboard', icon: SparklesIcon, label: 'Dashboard' },
    { path: '/sponsor-circle', icon: RectangleGroupIcon, label: 'Circle Dashboard' },
    { path: '/sponsor-leader', icon: ShieldCheckIcon, label: 'Leader Dashboard' },
    { path: '/dashboard/circles', icon: UserGroupIcon, label: 'Sponsor Circles' },
    { path: '/dashboard/impact-league', icon: TrophyIcon, label: 'Impact League' },
    { path: '/dashboard/contributions', icon: CurrencyDollarIcon, label: 'Contributions' },
    { path: '/dashboard/mentoring', icon: ChatBubbleLeftRightIcon, label: 'Mentoring' },
    { path: '/dashboard/marketplace', icon: ShoppingBagIcon, label: 'Marketplace' },
    { path: '/dashboard/vendor-dashboard', icon: BuildingStorefrontIcon, label: 'Vendor Dashboard' },
    { path: '/dashboard/analytics', icon: ChartBarIcon, label: 'Analytics' },
    { path: '/dashboard/chat-bans', icon: ShieldCheckIcon, label: 'Chat Bans' },
    { path: '/chat-demo', icon: ChatBubbleLeftRightIcon, label: 'Chat Demo' }
  ]

  // Supplier Navigation Items
  const supplierNavItems = [
    { path: '/dashboard/home', icon: HomeIcon, label: 'Home' },
    { path: '/dashboard', icon: SparklesIcon, label: 'Dashboard' },
    { path: '/dashboard/vendor-portal', icon: BuildingStorefrontIcon, label: 'Vendor Portal' },
    { path: '/dashboard/catalog', icon: BuildingStorefrontIcon, label: 'Catalog' },
    { path: '/dashboard/vendor-dashboard', icon: BuildingStorefrontIcon, label: 'Vendor Dashboard' },
    { path: '/dashboard/orders', icon: ShoppingBagIcon, label: 'Orders' },
    { path: '/dashboard/sessions', icon: ChatBubbleLeftRightIcon, label: 'Sessions' },
    { path: '/dashboard/analytics', icon: ChartBarIcon, label: 'Analytics' },
    { path: '/dashboard/chat-bans', icon: ShieldCheckIcon, label: 'Chat Bans' },
    { path: '/chat-demo', icon: ChatBubbleLeftRightIcon, label: 'Chat Demo' }
  ]

  // Admin Navigation Items
  const adminNavItems = [
    { path: '/dashboard/home', icon: HomeIcon, label: 'Home' },
    { path: '/dashboard', icon: SparklesIcon, label: 'Dashboard' },
    { path: '/dashboard/users', icon: UsersIcon, label: 'Users' },
    { path: '/dashboard/circles', icon: UserGroupIcon, label: 'Circles' },
    { path: '/dashboard/suppliers', icon: BuildingStorefrontIcon, label: 'Suppliers' },
    { path: '/dashboard/safety', icon: ShieldCheckIcon, label: 'Safety' },
    { path: '/dashboard/financial', icon: CurrencyDollarIcon, label: 'Financial' },
    { path: '/dashboard/chat-bans', icon: ShieldCheckIcon, label: 'Chat Bans' },
    { path: '/dashboard/report-queue', icon: ChatBubbleLeftRightIcon, label: 'Report Queue' },
    { path: '/dashboard/analytics', icon: ChartBarIcon, label: 'Analytics' },
    { path: '/chat-demo', icon: ChatBubbleLeftRightIcon, label: 'Chat Demo' }
  ]

  const getNavItems = () => {
    if (isStudent) return studentNavItems
    if (isSponsor) return sponsorNavItems
    if (isSupplier) return supplierNavItems
    if (isAdmin) return adminNavItems
    return sponsorNavItems // Default
  }

  const navItems = getNavItems()

  const navContent = (
    <div className="p-4">
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                `flex gap-3 items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-gray-700 hover:bg-gray-50'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )

  return (
    <>
      {/* ── Desktop Sidebar (unchanged — always visible at md+) ──────── */}
      <aside className="hidden md:block w-64 bg-white border-r border-gray-200 h-full overflow-y-auto flex-shrink-0">
        {navContent}
      </aside>

      {/* ── Mobile Drawer (only renders below md) ────────────────────── */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

          {/* Drawer Panel */}
          <div className="relative w-72 max-w-[80vw] bg-white h-full shadow-2xl overflow-y-auto animate-slide-in-left z-10">
            {/* Close button */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Menu</h2>
              <button
                onClick={onClose}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            {navContent}
          </div>
        </div>
      )}
    </>
  )
}

export default Sidebar
