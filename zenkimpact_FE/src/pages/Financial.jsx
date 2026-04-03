import { useState } from 'react'
import Layout from '../components/Layout'
import {
  CurrencyDollarIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  MagnifyingGlassIcon,
  ArrowDownTrayIcon,
  ChartBarIcon,
  ShoppingBagIcon,
  UserGroupIcon
} from '@heroicons/react/24/outline'

function Financial() {
  const [filterPeriod, setFilterPeriod] = useState('month')
  const [filterType, setFilterType] = useState('all')

  // Mock financial data
  const transactions = [
    {
      id: 1,
      type: 'Contribution',
      amount: 5000,
      from: 'Corporate Sponsor',
      to: 'The Navigators Circle',
      date: '2024-02-15',
      status: 'completed',
      fee: 250
    },
    {
      id: 2,
      type: 'Marketplace Purchase',
      amount: 1200,
      from: 'Student #7B34',
      to: 'ABC Tutoring Services',
      date: '2024-02-14',
      status: 'completed',
      fee: 60
    },
    {
      id: 3,
      type: 'Contribution',
      amount: 3000,
      from: 'Individual Sponsor',
      to: 'Tech Leaders Circle',
      date: '2024-02-13',
      status: 'completed',
      fee: 150
    },
    {
      id: 4,
      type: 'Marketplace Purchase',
      amount: 850,
      from: 'Student #9K12',
      to: 'EduTech Solutions',
      date: '2024-02-12',
      status: 'pending',
      fee: 42.5
    },
    {
      id: 5,
      type: 'Contribution',
      amount: 10000,
      from: 'NGO Partner',
      to: 'Community Impact Circle',
      date: '2024-02-11',
      status: 'completed',
      fee: 500
    },
    {
      id: 6,
      type: 'Marketplace Purchase',
      amount: 450,
      from: 'Student #5A23',
      to: 'Online Academy Pro',
      date: '2024-02-10',
      status: 'completed',
      fee: 22.5
    }
  ]

  const filteredTransactions = transactions.filter(transaction => {
    const matchesType = filterType === 'all' || transaction.type === filterType
    return matchesType
  })

  const totalContributions = transactions
    .filter(t => t.type === 'Contribution' && t.status === 'completed')
    .reduce((sum, t) => sum + t.amount, 0)

  const totalMarketplace = transactions
    .filter(t => t.type === 'Marketplace Purchase' && t.status === 'completed')
    .reduce((sum, t) => sum + t.amount, 0)

  const totalCommission = transactions
    .filter(t => t.status === 'completed')
    .reduce((sum, t) => sum + t.fee, 0)

  const pendingAmount = transactions
    .filter(t => t.status === 'pending')
    .reduce((sum, t) => sum + t.amount, 0)

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Financial Oversight</h1>
            <p className="text-gray-600">Monitor platform finances and transactions</p>
          </div>
          <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            <ArrowDownTrayIcon className="w-5 h-5" />
            Export Report
          </button>
        </div>

        {/* Financial Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Contributions</p>
              <UserGroupIcon className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">
              ${totalContributions.toLocaleString()}
            </p>
            <p className="text-xs text-green-600 flex items-center gap-1">
              <ArrowUpIcon className="w-3 h-3" />
              +18% from last month
            </p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Marketplace GMV</p>
              <ShoppingBagIcon className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">
              ${totalMarketplace.toLocaleString()}
            </p>
            <p className="text-xs text-green-600 flex items-center gap-1">
              <ArrowUpIcon className="w-3 h-3" />
              +12% from last month
            </p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Platform Commission</p>
              <CurrencyDollarIcon className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">
              ${totalCommission.toLocaleString()}
            </p>
            <p className="text-xs text-green-600 flex items-center gap-1">
              <ArrowUpIcon className="w-3 h-3" />
              +15% from last month
            </p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Pending Transactions</p>
              <ChartBarIcon className="w-5 h-5 text-yellow-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">
              ${pendingAmount.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">
              {transactions.filter(t => t.status === 'pending').length} transactions
            </p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Revenue Breakdown</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Contributions</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">
                    ${totalContributions.toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    {((totalContributions / (totalContributions + totalMarketplace)) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Marketplace</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">
                    ${totalMarketplace.toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    {((totalMarketplace / (totalContributions + totalMarketplace)) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Transaction Status</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Completed</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">
                    {transactions.filter(t => t.status === 'completed').length}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    ${transactions.filter(t => t.status === 'completed').reduce((sum, t) => sum + t.amount, 0).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Pending</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">
                    {transactions.filter(t => t.status === 'pending').length}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    ${pendingAmount.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex gap-2">
              <select
                value={filterPeriod}
                onChange={(e) => setFilterPeriod(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="week">Last Week</option>
                <option value="month">Last Month</option>
                <option value="quarter">Last Quarter</option>
                <option value="year">Last Year</option>
              </select>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value="Contribution">Contributions</option>
                <option value="Marketplace Purchase">Marketplace</option>
              </select>
            </div>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    From
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    To
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Commission
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTransactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {transaction.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-xs px-2 py-1 rounded ${
                        transaction.type === 'Contribution'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-purple-100 text-purple-700'
                      }`}>
                        {transaction.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {transaction.from}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {transaction.to}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                      ${transaction.amount.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                      ${transaction.fee.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-xs px-2 py-1 rounded ${
                        transaction.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {transaction.status.charAt(0).toUpperCase() + transaction.status.slice(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredTransactions.length === 0 && (
            <div className="text-center py-12">
              <CurrencyDollarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No transactions found</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

export default Financial
