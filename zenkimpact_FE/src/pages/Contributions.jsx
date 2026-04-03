import { useState } from 'react'
import Layout from '../components/Layout'
import {
  CurrencyDollarIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  UserGroupIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'

function Contributions() {
  const { isSponsor } = usePersona()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterType, setFilterType] = useState('all')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [formData, setFormData] = useState({
    amount: '',
    circle: '',
    purpose: '',
    studentId: '',
    notes: ''
  })

  // Mock contribution data
  const contributions = [
    {
      id: 1,
      amount: 5000,
      circle: 'The Navigators',
      purpose: 'Tuition Support',
      studentId: 'Student #7B34',
      status: 'completed',
      date: '2024-02-15',
      transactionId: 'TXN-2024-001',
      notes: 'Q1 2024 tuition payment'
    },
    {
      id: 2,
      amount: 1200,
      circle: 'The Navigators',
      purpose: 'Course Materials',
      studentId: 'Student #9K12',
      status: 'completed',
      date: '2024-02-14',
      transactionId: 'TXN-2024-002',
      notes: 'Textbooks and online course access'
    },
    {
      id: 3,
      amount: 3000,
      circle: 'The Catalysts',
      purpose: 'Equipment',
      studentId: 'Student #5A23',
      status: 'pending',
      date: '2024-02-13',
      transactionId: 'TXN-2024-003',
      notes: 'Laptop purchase for student'
    },
    {
      id: 4,
      amount: 2500,
      circle: 'The Navigators',
      purpose: 'Skill Building Program',
      studentId: 'Student #7B34',
      status: 'completed',
      date: '2024-02-10',
      transactionId: 'TXN-2024-004',
      notes: 'Coding bootcamp enrollment'
    },
    {
      id: 5,
      amount: 8000,
      circle: 'Community Impact',
      purpose: 'Scholarship',
      studentId: 'Student #2F89',
      status: 'completed',
      date: '2024-02-08',
      transactionId: 'TXN-2024-005',
      notes: 'Full year scholarship'
    },
    {
      id: 6,
      amount: 1500,
      circle: 'The Navigators',
      purpose: 'Tuition Support',
      studentId: 'Student #8D67',
      status: 'failed',
      date: '2024-02-05',
      transactionId: 'TXN-2024-006',
      notes: 'Payment processing error'
    }
  ]

  const filteredContributions = contributions.filter(contribution => {
    const matchesSearch = contribution.studentId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         contribution.purpose.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         contribution.circle.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'all' || contribution.status === filterStatus
    const matchesType = filterType === 'all' || contribution.purpose === filterType
    return matchesSearch && matchesStatus && matchesType
  })

  const totalContributions = contributions
    .filter(c => c.status === 'completed')
    .reduce((sum, c) => sum + c.amount, 0)

  const pendingAmount = contributions
    .filter(c => c.status === 'pending')
    .reduce((sum, c) => sum + c.amount, 0)

  const getStatusBadge = (status) => {
    const styles = {
      completed: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      failed: 'bg-red-100 text-red-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating contribution:', formData)
    setIsModalOpen(false)
    setFormData({
      amount: '',
      circle: '',
      purpose: '',
      studentId: '',
      notes: ''
    })
    alert('Contribution submitted successfully!')
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Contributions</h1>
            <p className="text-gray-600">Manage your financial contributions and track impact</p>
          </div>
          {isSponsor && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
            >
              <PlusIcon className="w-5 h-5" />
              Make Contribution
            </button>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Contributed</p>
              <CurrencyDollarIcon className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${totalContributions.toLocaleString()}
            </p>
            <p className="text-xs text-green-600 mt-1">All time</p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Pending</p>
              <ClockIcon className="w-5 h-5 text-yellow-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${pendingAmount.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {contributions.filter(c => c.status === 'pending').length} transactions
            </p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Contributions</p>
              <CheckCircleIcon className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {contributions.filter(c => c.status === 'completed').length}
            </p>
            <p className="text-xs text-gray-500 mt-1">Completed</p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">This Month</p>
              <CurrencyDollarIcon className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${contributions
                .filter(c => c.status === 'completed' && c.date.startsWith('2024-02'))
                .reduce((sum, c) => sum + c.amount, 0)
                .toLocaleString()}
            </p>
            <p className="text-xs text-green-600 mt-1">+15% from last month</p>
          </div>
        </div>

        {/* Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by student, circle, or purpose..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
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
                <option value="Tuition Support">Tuition Support</option>
                <option value="Course Materials">Course Materials</option>
                <option value="Equipment">Equipment</option>
                <option value="Skill Building Program">Skill Building Program</option>
                <option value="Scholarship">Scholarship</option>
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Contributions Table */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Circle
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Purpose
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Student
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Transaction ID
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredContributions.map((contribution) => (
                  <tr key={contribution.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {contribution.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-gray-900">
                        ${contribution.amount.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <UserGroupIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900">{contribution.circle}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">{contribution.purpose}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <AcademicCapIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900">{contribution.studentId}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(contribution.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {contribution.transactionId}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredContributions.length === 0 && (
            <div className="text-center py-12">
              <CurrencyDollarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No contributions found matching your criteria</p>
            </div>
          )}
        </div>

        {/* Make Contribution Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={() => setIsModalOpen(false)}
            ></div>
            <div className="flex min-h-full items-center justify-center p-4">
              <div
                className="relative w-full max-w-lg rounded-xl bg-white shadow-lg border border-gray-200"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">Make a Contribution</h2>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Amount ($) <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="number"
                        name="amount"
                        value={formData.amount}
                        onChange={handleInputChange}
                        required
                        min="1"
                        placeholder="Enter amount"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Circle <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="circle"
                        value={formData.circle}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Select circle</option>
                        <option value="The Navigators">The Navigators</option>
                        <option value="The Catalysts">The Catalysts</option>
                        <option value="The Vanguard">The Vanguard</option>
                        <option value="Community Impact">Community Impact</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Purpose <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="purpose"
                        value={formData.purpose}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Select purpose</option>
                        <option value="Tuition Support">Tuition Support</option>
                        <option value="Course Materials">Course Materials</option>
                        <option value="Equipment">Equipment</option>
                        <option value="Skill Building Program">Skill Building Program</option>
                        <option value="Scholarship">Scholarship</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Student ID (Optional)
                      </label>
                      <input
                        type="text"
                        name="studentId"
                        value={formData.studentId}
                        onChange={handleInputChange}
                        placeholder="e.g., Student #7B34"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Notes (Optional)
                      </label>
                      <textarea
                        name="notes"
                        value={formData.notes}
                        onChange={handleInputChange}
                        rows={3}
                        placeholder="Add any additional notes..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="flex gap-3 pt-4">
                      <button
                        type="button"
                        onClick={() => setIsModalOpen(false)}
                        className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                      >
                        Submit Contribution
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Contributions
