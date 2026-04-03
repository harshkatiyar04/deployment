import { useState } from 'react'
import Layout from '../components/Layout'
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

function Safety() {
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterType, setFilterType] = useState('all')

  // Mock safety incidents
  const incidents = [
    {
      id: 1,
      type: 'Content Review',
      severity: 'medium',
      description: 'Inappropriate language detected in message',
      reportedBy: 'Automated System',
      reportedDate: '2024-02-15 10:30 AM',
      status: 'pending',
      relatedUser: 'User #7B34',
      relatedType: 'Student',
      details: 'Message flagged for review containing potentially inappropriate content'
    },
    {
      id: 2,
      type: 'Content Review',
      severity: 'low',
      description: 'Suspicious activity pattern detected',
      reportedBy: 'Automated System',
      reportedDate: '2024-02-14 3:45 PM',
      status: 'reviewed',
      relatedUser: 'User #9K12',
      relatedType: 'Sponsor',
      details: 'Multiple login attempts from different locations'
    },
    {
      id: 3,
      type: 'User Report',
      severity: 'high',
      description: 'User reported inappropriate behavior',
      reportedBy: 'Student #5A23',
      reportedDate: '2024-02-13 2:15 PM',
      status: 'investigating',
      relatedUser: 'Sponsor #3C45',
      relatedType: 'Sponsor',
      details: 'Student reported receiving inappropriate messages from sponsor'
    },
    {
      id: 4,
      type: 'Content Review',
      severity: 'low',
      description: 'Potential spam message detected',
      reportedBy: 'Automated System',
      reportedDate: '2024-02-12 9:20 AM',
      status: 'resolved',
      relatedUser: 'User #8D67',
      relatedType: 'Supplier',
      details: 'Message flagged as potential spam'
    },
    {
      id: 5,
      type: 'Age Verification',
      severity: 'high',
      description: 'Age verification failed',
      reportedBy: 'Automated System',
      reportedDate: '2024-02-11 11:00 AM',
      status: 'pending',
      relatedUser: 'User #2F89',
      relatedType: 'Student',
      details: 'Student registration age verification failed'
    }
  ]

  const filteredIncidents = incidents.filter(incident => {
    const matchesStatus = filterStatus === 'all' || incident.status === filterStatus
    const matchesType = filterType === 'all' || incident.type === filterType
    return matchesStatus && matchesType
  })

  const getSeverityBadge = (severity) => {
    const styles = {
      high: 'bg-red-100 text-red-700',
      medium: 'bg-yellow-100 text-yellow-700',
      low: 'bg-blue-100 text-blue-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[severity]}`}>
        {severity.charAt(0).toUpperCase() + severity.slice(1)}
      </span>
    )
  }

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-700',
      investigating: 'bg-orange-100 text-orange-700',
      reviewed: 'bg-blue-100 text-blue-700',
      resolved: 'bg-green-100 text-green-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status] || styles.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const stats = {
    total: incidents.length,
    pending: incidents.filter(i => i.status === 'pending').length,
    investigating: incidents.filter(i => i.status === 'investigating').length,
    resolved: incidents.filter(i => i.status === 'resolved').length,
    highSeverity: incidents.filter(i => i.severity === 'high').length
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Safety Monitoring</h1>
          <p className="text-gray-600">Monitor and manage safety incidents and content moderation</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Incidents</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Pending Review</p>
            <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Investigating</p>
            <p className="text-2xl font-bold text-orange-600">{stats.investigating}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Resolved</p>
            <p className="text-2xl font-bold text-green-600">{stats.resolved}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-red-200 p-4 bg-red-50">
            <p className="text-sm text-red-600 mb-1">High Severity</p>
            <p className="text-2xl font-bold text-red-700">{stats.highSeverity}</p>
          </div>
        </div>

        {/* System Status */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <ShieldCheckIcon className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">System Status</h3>
                <p className="text-sm text-gray-500">All safety systems operational</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircleIcon className="w-6 h-6 text-green-600" />
              <span className="text-sm font-medium text-green-600">Operational</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search incidents..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value="Content Review">Content Review</option>
                <option value="User Report">User Report</option>
                <option value="Age Verification">Age Verification</option>
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="investigating">Investigating</option>
                <option value="reviewed">Reviewed</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </div>
        </div>

        {/* Incidents List */}
        <div className="space-y-4">
          {filteredIncidents.map((incident) => (
            <div
              key={incident.id}
              className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    incident.severity === 'high' ? 'bg-red-100' :
                    incident.severity === 'medium' ? 'bg-yellow-100' : 'bg-blue-100'
                  }`}>
                    {incident.type === 'Content Review' ? (
                      <ChatBubbleLeftRightIcon className={`w-6 h-6 ${
                        incident.severity === 'high' ? 'text-red-600' :
                        incident.severity === 'medium' ? 'text-yellow-600' : 'text-blue-600'
                      }`} />
                    ) : (
                      <ExclamationTriangleIcon className={`w-6 h-6 ${
                        incident.severity === 'high' ? 'text-red-600' :
                        incident.severity === 'medium' ? 'text-yellow-600' : 'text-blue-600'
                      }`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-bold text-gray-900">{incident.description}</h3>
                      {getSeverityBadge(incident.severity)}
                      {getStatusBadge(incident.status)}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{incident.details}</p>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <UserIcon className="w-4 h-4" />
                        <span>Related: {incident.relatedUser} ({incident.relatedType})</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <ClockIcon className="w-4 h-4" />
                        <span>{incident.reportedDate}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <UserIcon className="w-4 h-4" />
                        <span>Reported by: {incident.reportedBy}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="text-blue-600 hover:text-blue-700 p-2 hover:bg-blue-50 rounded-lg" title="View Details">
                    <EyeIcon className="w-5 h-5" />
                  </button>
                  {incident.status === 'pending' && (
                    <>
                      <button className="text-green-600 hover:text-green-700 p-2 hover:bg-green-50 rounded-lg" title="Approve">
                        <CheckCircleIcon className="w-5 h-5" />
                      </button>
                      <button className="text-red-600 hover:text-red-700 p-2 hover:bg-red-50 rounded-lg" title="Reject">
                        <XCircleIcon className="w-5 h-5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredIncidents.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            <ShieldCheckIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No incidents found matching your criteria</p>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Safety
