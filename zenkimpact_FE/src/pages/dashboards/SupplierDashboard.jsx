import { usePersona } from '../../contexts/PersonaContext'
import {
  ShoppingBagIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  UserGroupIcon,
  BuildingStorefrontIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline'

function SupplierDashboard() {
  const { activePersona } = usePersona()
  
  const isServiceProvider = activePersona.subtype === 'service'
  const supplierType = isServiceProvider ? 'Educational Service Provider' : 'Product Supplier'

  const kpiCards = [
    {
      title: isServiceProvider ? 'Active Sessions' : 'Orders This Month',
      value: isServiceProvider ? '24' : '156',
      icon: isServiceProvider ? AcademicCapIcon : ShoppingBagIcon,
      color: 'blue'
    },
    {
      title: 'Revenue',
      value: '$8,450',
      icon: CurrencyDollarIcon,
      color: 'green',
      change: '+18%'
    },
    {
      title: isServiceProvider ? 'Students' : 'Products',
      value: isServiceProvider ? '18' : '45',
      icon: isServiceProvider ? UserGroupIcon : BuildingStorefrontIcon,
      color: 'purple'
    },
    {
      title: 'Rating',
      value: '4.8',
      icon: ChartBarIcon,
      color: 'yellow'
    }
  ]

  return (
    <div>
      {/* Welcome Section */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Supplier Dashboard
        </h1>
        <p className="text-gray-600">Viewing as: {supplierType}</p>
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
              {card.change && <p className="text-xs text-green-600">{card.change} from last month</p>}
            </div>
          )
        })}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {isServiceProvider ? (
          <>
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Upcoming Sessions</h2>
              <div className="space-y-3">
                {[
                  { student: 'Student #7B34', subject: 'Mathematics', time: 'Tomorrow, 3:00 PM' },
                  { student: 'Student #9C56', subject: 'Science', time: 'Friday, 2:00 PM' },
                  { student: 'Student #3A21', subject: 'English', time: 'Monday, 4:00 PM' }
                ].map((session, idx) => (
                  <div key={idx} className="p-3 border border-gray-200 rounded-lg">
                    <p className="text-sm font-medium text-gray-900">{session.subject}</p>
                    <p className="text-xs text-gray-500 mt-1">{session.student} • {session.time}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Session History</h2>
              <div className="space-y-3">
                {[
                  { student: 'Student #7B34', subject: 'Mathematics', date: '2 days ago', rating: 5 },
                  { student: 'Student #9C56', subject: 'Science', date: '5 days ago', rating: 5 },
                  { student: 'Student #3A21', subject: 'English', date: '1 week ago', rating: 4 }
                ].map((session, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{session.subject}</p>
                      <p className="text-xs text-gray-500">{session.student} • {session.date}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      {[...Array(5)].map((_, i) => (
                        <span key={i} className={`text-xs ${i < session.rating ? 'text-yellow-400' : 'text-gray-300'}`}>★</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Orders</h2>
              <div className="space-y-3">
                {[
                  { order: '#ORD-1234', product: 'Laptop', amount: '$450', status: 'Delivered', date: '2 days ago' },
                  { order: '#ORD-1235', product: 'Books Set', amount: '$120', status: 'In Transit', date: '5 days ago' },
                  { order: '#ORD-1236', product: 'Tablet', amount: '$280', status: 'Processing', date: '1 week ago' }
                ].map((order, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{order.product}</p>
                      <p className="text-xs text-gray-500">{order.order} • {order.date}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">{order.amount}</p>
                      <span className={`text-xs px-2 py-1 rounded ${
                        order.status === 'Delivered' ? 'bg-green-100 text-green-700' :
                        order.status === 'In Transit' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {order.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Inventory Status</h2>
              <div className="space-y-4">
                {[
                  { product: 'Laptops', stock: 45, low: false },
                  { product: 'Tablets', stock: 12, low: true },
                  { product: 'Books', stock: 234, low: false }
                ].map((item, idx) => (
                  <div key={idx}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700">{item.product}</span>
                      <span className={`font-medium ${item.low ? 'text-red-600' : 'text-gray-900'}`}>
                        {item.stock} units
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          item.low ? 'bg-red-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min((item.stock / 50) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Performance Metrics */}
      <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <p className="text-2xl font-bold text-gray-900">98%</p>
            <p className="text-sm text-gray-500 mt-1">Satisfaction Rate</p>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <p className="text-2xl font-bold text-gray-900">4.8/5</p>
            <p className="text-sm text-gray-500 mt-1">Average Rating</p>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <p className="text-2xl font-bold text-gray-900">156</p>
            <p className="text-sm text-gray-500 mt-1">{isServiceProvider ? 'Total Sessions' : 'Total Orders'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SupplierDashboard

