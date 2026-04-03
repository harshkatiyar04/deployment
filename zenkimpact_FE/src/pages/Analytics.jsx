import { useState } from 'react'
import Layout from '../components/Layout'
import {
  ChartBarIcon,
  UsersIcon,
  UserGroupIcon,
  ShoppingBagIcon,
  CurrencyDollarIcon,
  ArrowDownTrayIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  AcademicCapIcon,
  StarIcon
} from '@heroicons/react/24/outline'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { usePersona } from '../contexts/PersonaContext'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

function Analytics() {
  const { isSupplier, isAdmin, activePersona } = usePersona()
  const isServiceProvider = activePersona.subtype === 'service'
  const [timeRange, setTimeRange] = useState('month')

  // Supplier-specific data
  const supplierRevenueData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Revenue ($)',
        data: [4500, 6200, 5800, 7800, 8900, 10200],
        backgroundColor: 'rgba(99, 102, 241, 0.8)',
        borderRadius: 8
      }
    ]
  }

  const supplierOrdersData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Orders',
        data: [12, 18, 15, 24, 28, 32],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4
      }
    ]
  }

  const productCategoryData = {
    labels: ['Courses', 'Tutors', 'Books', 'Devices', 'Other'],
    datasets: [
      {
        data: [45, 30, 15, 8, 2],
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(249, 115, 22, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(107, 114, 128, 0.8)'
        ]
      }
    ]
  }

  // Mock data for charts
  const userGrowthData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    datasets: [
      {
        label: 'New Users',
        data: [120, 190, 300, 250, 280, 320, 350, 380, 400, 420, 450, 480],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4
      },
      {
        label: 'Active Users',
        data: [800, 950, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000],
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4
      }
    ]
  }

  const revenueData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Revenue ($)',
        data: [12000, 19000, 15000, 25000, 22000, 30000],
        backgroundColor: 'rgba(99, 102, 241, 0.8)',
        borderRadius: 8
      }
    ]
  }

  const userDistributionData = {
    labels: ['Students', 'Sponsors', 'Suppliers', 'Admins'],
    datasets: [
      {
        data: [65, 20, 10, 5],
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(249, 115, 22, 0.8)',
          'rgba(107, 114, 128, 0.8)'
        ]
      }
    ]
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top'
      }
    }
  }

  const supplierMetrics = [
    {
      title: isServiceProvider ? 'Total Sessions' : 'Total Orders',
      value: isServiceProvider ? '156' : '234',
      change: '+12%',
      trend: 'up',
      icon: isServiceProvider ? AcademicCapIcon : ShoppingBagIcon,
      color: 'blue'
    },
    {
      title: 'Total Revenue',
      value: '$43,400',
      change: '+18%',
      trend: 'up',
      icon: CurrencyDollarIcon,
      color: 'green'
    },
    {
      title: isServiceProvider ? 'Active Students' : 'Products Sold',
      value: isServiceProvider ? '45' : '156',
      change: '+8',
      trend: 'up',
      icon: isServiceProvider ? UsersIcon : ShoppingBagIcon,
      color: 'purple'
    },
    {
      title: 'Average Rating',
      value: '4.8',
      change: '+0.2',
      trend: 'up',
      icon: StarIcon,
      color: 'yellow'
    }
  ]

  const adminMetrics = [
    {
      title: 'Total Users',
      value: '2,456',
      change: '+12%',
      trend: 'up',
      icon: UsersIcon,
      color: 'blue'
    },
    {
      title: 'Active Circles',
      value: '128',
      change: '+8',
      trend: 'up',
      icon: UserGroupIcon,
      color: 'green'
    },
    {
      title: 'Marketplace Orders',
      value: '1,234',
      change: '+15%',
      trend: 'up',
      icon: ShoppingBagIcon,
      color: 'purple'
    },
    {
      title: 'Total Revenue',
      value: '$245,680',
      change: '+18%',
      trend: 'up',
      icon: CurrencyDollarIcon,
      color: 'yellow'
    }
  ]

  const metrics = isSupplier ? supplierMetrics : adminMetrics

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {isSupplier ? 'Supplier Analytics' : 'Platform Analytics'}
            </h1>
            <p className="text-gray-600">
              {isSupplier ? 'Track your performance and business metrics' : 'Comprehensive platform metrics and insights'}
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="quarter">Last Quarter</option>
              <option value="year">Last Year</option>
            </select>
            <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
              <ArrowDownTrayIcon className="w-5 h-5" />
              Export
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {metrics.map((metric) => {
            const Icon = metric.icon
            const colorClasses = {
              blue: 'bg-blue-50 text-blue-600',
              green: 'bg-green-50 text-green-600',
              purple: 'bg-purple-50 text-purple-600',
              yellow: 'bg-yellow-50 text-yellow-600'
            }
            return (
              <div
                key={metric.title}
                className="rounded-xl bg-white shadow-sm border border-gray-200 p-6"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-gray-500">{metric.title}</p>
                  <div className={`p-2 rounded-lg ${colorClasses[metric.color]}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-gray-900 mb-1">{metric.value}</p>
                <p className={`text-xs flex items-center gap-1 ${
                  metric.trend === 'up' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {metric.trend === 'up' ? (
                    <ArrowTrendingUpIcon className="w-3 h-3" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-3 h-3" />
                  )}
                  {metric.change} from last period
                </p>
              </div>
            )
          })}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {isSupplier ? (
            <>
              {/* Revenue Chart */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Revenue Trend</h2>
                <div className="h-64">
                  <Bar data={supplierRevenueData} options={chartOptions} />
                </div>
              </div>

              {/* Orders/Sessions Chart */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  {isServiceProvider ? 'Sessions Trend' : 'Orders Trend'}
                </h2>
                <div className="h-64">
                  <Line data={supplierOrdersData} options={chartOptions} />
                </div>
              </div>
            </>
          ) : (
            <>
              {/* User Growth Chart */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">User Growth</h2>
                <div className="h-64">
                  <Line data={userGrowthData} options={chartOptions} />
                </div>
              </div>

              {/* Revenue Chart */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Revenue Trend</h2>
                <div className="h-64">
                  <Bar data={revenueData} options={chartOptions} />
                </div>
              </div>
            </>
          )}
        </div>

        {/* Distribution Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {isSupplier ? (
            <div className="lg:col-span-2 rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Product Category Distribution</h2>
              <div className="h-64">
                <Doughnut
                  data={productCategoryData}
                  options={{
                    ...chartOptions,
                    plugins: {
                      ...chartOptions.plugins,
                      legend: {
                        position: 'bottom'
                      }
                    }
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="lg:col-span-2 rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">User Distribution</h2>
              <div className="h-64">
                <Doughnut
                  data={userDistributionData}
                  options={{
                    ...chartOptions,
                    plugins: {
                      ...chartOptions.plugins,
                      legend: {
                        position: 'bottom'
                      }
                    }
                  }}
                />
              </div>
            </div>
          )}

          {/* Engagement Stats */}
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Engagement Metrics</h2>
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Daily Active Users</p>
                <p className="text-2xl font-bold text-gray-900">1,234</p>
                <p className="text-xs text-green-600 mt-1">+8% from yesterday</p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Weekly Active Users</p>
                <p className="text-2xl font-bold text-gray-900">8,456</p>
                <p className="text-xs text-green-600 mt-1">+12% from last week</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Monthly Active Users</p>
                <p className="text-2xl font-bold text-gray-900">18,234</p>
                <p className="text-xs text-green-600 mt-1">+15% from last month</p>
              </div>
            </div>
          </div>
        </div>

        {/* Additional Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Top Performing Circles</h3>
            <div className="space-y-3">
              {[
                { name: 'Community Impact', score: 9.5, students: 120 },
                { name: 'Tech Leaders', score: 9.2, students: 32 },
                { name: 'The Navigators', score: 8.5, students: 45 }
              ].map((circle, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{circle.name}</p>
                    <p className="text-xs text-gray-500">{circle.students} students</p>
                  </div>
                  <span className="text-sm font-bold text-blue-600">{circle.score}/10</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Top Suppliers</h3>
            <div className="space-y-3">
              {[
                { name: 'EduTech Solutions', orders: 456, revenue: 89200 },
                { name: 'Online Academy Pro', orders: 312, revenue: 67800 },
                { name: 'ABC Tutoring', orders: 234, revenue: 45600 }
              ].map((supplier, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{supplier.name}</p>
                    <p className="text-xs text-gray-500">{supplier.orders} orders</p>
                  </div>
                  <span className="text-sm font-bold text-green-600">${supplier.revenue.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Platform Health</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-600">Uptime</span>
                  <span className="text-sm font-medium text-gray-900">99.9%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-green-600 h-2 rounded-full" style={{ width: '99.9%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-600">Response Time</span>
                  <span className="text-sm font-medium text-gray-900">120ms</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full" style={{ width: '95%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-600">Error Rate</span>
                  <span className="text-sm font-medium text-gray-900">0.01%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-green-600 h-2 rounded-full" style={{ width: '99%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default Analytics
