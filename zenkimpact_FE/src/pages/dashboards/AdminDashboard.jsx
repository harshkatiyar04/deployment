import {
  UsersIcon,
  UserGroupIcon,
  BuildingStorefrontIcon,
  CurrencyDollarIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'

function AdminDashboard() {
  const kpiCards = [
    {
      title: 'Total Users',
      value: '2,456',
      icon: UsersIcon,
      color: 'blue',
      change: '+12%'
    },
    {
      title: 'Active Circles',
      value: '128',
      icon: UserGroupIcon,
      color: 'green',
      change: '+8'
    },
    {
      title: 'Suppliers',
      value: '45',
      icon: BuildingStorefrontIcon,
      color: 'purple',
      change: '+3'
    },
    {
      title: 'Platform Revenue',
      value: '$45,230',
      icon: CurrencyDollarIcon,
      color: 'yellow',
      change: '+18%'
    }
  ]

  return (
    <div>
      {/* Welcome Section */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Admin Dashboard
        </h1>
        <p className="text-gray-600">Platform Overview & Management</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpiCards.map((card) => {
          const Icon = card.icon
          const colorClasses = {
            blue: 'bg-blue-50 text-blue-600',
            green: 'bg-green-50 text-green-600',
            purple: 'bg-purple-50 text-purple-600',
            yellow: 'bg-yellow-50 text-yellow-600'
          }
          return (
            <div
              key={card.title}
              className="rounded-xl bg-white shadow-sm border border-gray-200 p-6"
            >
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-500">{card.title}</p>
                <div className={`p-2 rounded-lg ${colorClasses[card.color]}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 mb-1">{card.value}</p>
              <p className="text-xs text-green-600">{card.change} from last month</p>
            </div>
          )
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Link
          to="/dashboard/users"
          className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <UsersIcon className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Manage Users</p>
              <p className="text-xs text-gray-500">View all users</p>
            </div>
          </div>
        </Link>
        <Link
          to="/dashboard/circles"
          className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <UserGroupIcon className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Manage Circles</p>
              <p className="text-xs text-gray-500">Sponsor circles</p>
            </div>
          </div>
        </Link>
        <Link
          to="/dashboard/safety"
          className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-50 rounded-lg">
              <ShieldCheckIcon className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Safety Monitor</p>
              <p className="text-xs text-gray-500">3 pending reviews</p>
            </div>
          </div>
        </Link>
        <Link
          to="/dashboard/financial"
          className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <CurrencyDollarIcon className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Financial</p>
              <p className="text-xs text-gray-500">View reports</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Safety Alerts */}
      <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldCheckIcon className="w-6 h-6 text-blue-600" />
            Safety Monitoring
          </h2>
          <Link to="/dashboard/safety" className="text-sm text-blue-600 hover:text-blue-700">View All</Link>
        </div>
        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Content Review Required</p>
              <p className="text-xs text-gray-500">3 messages flagged for review</p>
            </div>
            <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-700 rounded">Pending</span>
          </div>
          <div className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <ShieldCheckIcon className="w-5 h-5 text-green-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">All Systems Operational</p>
              <p className="text-xs text-gray-500">No critical safety incidents</p>
            </div>
            <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">Safe</span>
          </div>
        </div>
      </div>

      {/* Platform Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Recent User Activity</h2>
          <div className="space-y-3">
            {[
              { action: 'New sponsor registered', user: 'Corporate Sponsor', time: '2 hours ago' },
              { action: 'Circle created', user: 'The Navigators', time: '5 hours ago' },
              { action: 'Supplier approved', user: 'ABC Tutoring', time: '1 day ago' },
              { action: 'Impact mission completed', user: 'Student #7B34', time: '2 days ago' }
            ].map((activity, idx) => (
              <div key={idx} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <UsersIcon className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                  <p className="text-xs text-gray-500">{activity.user} • {activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Financial Overview</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div>
                <p className="text-sm text-gray-500">Total Contributions</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">$245,680</p>
              </div>
              <CurrencyDollarIcon className="w-8 h-8 text-green-600" />
            </div>
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div>
                <p className="text-sm text-gray-500">Marketplace GMV</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">$198,450</p>
              </div>
              <ChartBarIcon className="w-8 h-8 text-blue-600" />
            </div>
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div>
                <p className="text-sm text-gray-500">Platform Commission</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">$45,230</p>
              </div>
              <ChartBarIcon className="w-8 h-8 text-purple-600" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard

