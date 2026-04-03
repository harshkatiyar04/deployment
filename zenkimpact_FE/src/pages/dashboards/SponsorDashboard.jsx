import { usePersona } from '../../contexts/PersonaContext'
import {
  CurrencyDollarIcon,
  UserGroupIcon,
  TrophyIcon,
  ChartBarIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline'

function SponsorDashboard() {
  const { activePersona } = usePersona()
  
  const getSponsorType = () => {
    if (activePersona.subtype === 'corporate') return 'Corporate Sponsor'
    if (activePersona.subtype === 'ngo') return 'NGO Partner'
    return 'Individual Sponsor'
  }

  const kpiCards = [
    {
      title: 'Total Contributions',
      value: '$12,450',
      icon: CurrencyDollarIcon,
      color: 'green',
      change: '+12%'
    },
    {
      title: 'Active Circles',
      value: '3',
      icon: UserGroupIcon,
      color: 'blue',
      change: '+1'
    },
    {
      title: 'Impact Score',
      value: '9,210',
      icon: TrophyIcon,
      color: 'yellow',
      change: '+245'
    },
    {
      title: 'Students Supported',
      value: '8',
      icon: AcademicCapIcon,
      color: 'purple',
      change: '+2'
    }
  ]

  return (
    <div>
      {/* Welcome Section */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Sponsor Dashboard
        </h1>
        <p className="text-gray-600">Viewing as: {getSponsorType()}</p>
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

      {/* Impact League Leaderboard */}
      <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Impact League</h2>
          <button className="text-sm text-blue-600 hover:text-blue-700">View Full Leaderboard</button>
        </div>
        <div className="space-y-3">
          {[
            { name: 'The Navigators', score: 9850, rank: 1 },
            { name: 'The Catalysts', score: 9420, rank: 2 },
            { name: 'Your Circle', score: 9210, rank: 3, highlight: true },
            { name: 'Future Founders', score: 8950, rank: 4 }
          ].map((circle) => (
            <div
              key={circle.rank}
              className={`flex items-center justify-between p-3 rounded-lg ${
                circle.highlight ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                  circle.rank === 1 ? 'bg-yellow-100 text-yellow-700' :
                  circle.rank === 2 ? 'bg-gray-100 text-gray-700' :
                  circle.rank === 3 ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {circle.rank}
                </span>
                <span className="font-medium text-gray-900">{circle.name}</span>
              </div>
              <span className="font-bold text-gray-900">{circle.score.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active Impact Missions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Active Impact Missions</h2>
          <div className="space-y-3">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-gray-900">Fund Coding Course</p>
                <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">Active</span>
              </div>
              <p className="text-xs text-gray-500 mb-2">Student ID #7B34</p>
              <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: '85%' }}></div>
              </div>
              <p className="text-xs text-gray-600">85% Funded</p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-gray-900">Provide Laptop</p>
                <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-700 rounded">In Progress</span>
              </div>
              <p className="text-xs text-gray-500 mb-2">Student ID #9C56</p>
              <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                <div className="bg-green-600 h-2 rounded-full" style={{ width: '60%' }}></div>
              </div>
              <p className="text-xs text-gray-600">60% Funded</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Contributions</h2>
          <div className="space-y-3">
            {[
              { amount: '$500', purpose: 'Tutoring Session', date: '2 days ago', student: 'Student #7B34' },
              { amount: '$300', purpose: 'Course Materials', date: '5 days ago', student: 'Student #9C56' },
              { amount: '$200', purpose: 'Device Support', date: '1 week ago', student: 'Student #3A21' }
            ].map((contribution, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{contribution.amount}</p>
                  <p className="text-xs text-gray-500">{contribution.purpose}</p>
                  <p className="text-xs text-gray-400">{contribution.student} • {contribution.date}</p>
                </div>
                <ChartBarIcon className="w-5 h-5 text-gray-400" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SponsorDashboard

