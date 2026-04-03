import { useState } from 'react'
import Layout from '../components/Layout'
import {
  TrophyIcon,
  StarIcon,
  FireIcon,
  CheckCircleIcon,
  ClockIcon,
  UserGroupIcon,
  ChartBarIcon,
  AcademicCapIcon,
  CurrencyDollarIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'

function ImpactLeague() {
  const { isSponsor } = usePersona()
  const [selectedTab, setSelectedTab] = useState('leaderboard') // leaderboard, missions, badges

  // Mock leaderboard data
  const leaderboard = [
    {
      rank: 1,
      circleName: 'The Navigators',
      impactScore: 9210,
      members: 12,
      students: 45,
      contributions: 125000,
      mentoringHours: 340,
      missionsCompleted: 8,
      badge: 'gold',
      change: '+2'
    },
    {
      rank: 2,
      circleName: 'The Catalysts',
      impactScore: 8750,
      members: 15,
      students: 38,
      contributions: 98000,
      mentoringHours: 298,
      missionsCompleted: 7,
      badge: 'silver',
      change: '+1'
    },
    {
      rank: 3,
      circleName: 'The Vanguard',
      impactScore: 8210,
      members: 8,
      students: 32,
      contributions: 89000,
      mentoringHours: 256,
      missionsCompleted: 6,
      badge: 'bronze',
      change: '-2'
    },
    {
      rank: 4,
      circleName: 'Community Impact',
      impactScore: 7890,
      members: 20,
      students: 120,
      contributions: 245000,
      mentoringHours: 420,
      missionsCompleted: 5,
      badge: null,
      change: '+1'
    },
    {
      rank: 5,
      circleName: 'Tech Leaders Circle',
      impactScore: 7650,
      members: 10,
      students: 28,
      contributions: 67000,
      mentoringHours: 189,
      missionsCompleted: 4,
      badge: null,
      change: '-1'
    },
    {
      rank: 6,
      circleName: 'Future Leaders',
      impactScore: 7230,
      members: 18,
      students: 35,
      contributions: 78000,
      mentoringHours: 234,
      missionsCompleted: 4,
      badge: null,
      change: '0'
    }
  ]

  // Mock impact missions
  const impactMissions = [
    {
      id: 1,
      title: 'Fund Coding Course for Student #7B34',
      description: 'Support a university student in completing a full-stack development course',
      targetAmount: 5000,
      currentAmount: 4250,
      progress: 85,
      deadline: '2024-03-15',
      status: 'active',
      circle: 'The Navigators',
      category: 'Education'
    },
    {
      id: 2,
      title: 'Provide Laptops for 5 Students',
      description: 'Equip students with essential learning devices',
      targetAmount: 3000,
      currentAmount: 3000,
      progress: 100,
      deadline: '2024-02-20',
      status: 'completed',
      circle: 'The Catalysts',
      category: 'Equipment'
    },
    {
      id: 3,
      title: 'Mentoring Program for STEM Students',
      description: 'Establish a 6-month mentoring program for 10 STEM students',
      targetAmount: 8000,
      currentAmount: 5200,
      progress: 65,
      deadline: '2024-04-01',
      status: 'active',
      circle: 'The Vanguard',
      category: 'Mentoring'
    },
    {
      id: 4,
      title: 'Scholarship for Rural Student',
      description: 'Full scholarship for one year of university education',
      targetAmount: 12000,
      currentAmount: 8900,
      progress: 74,
      deadline: '2024-03-30',
      status: 'active',
      circle: 'Community Impact',
      category: 'Scholarship'
    },
    {
      id: 5,
      title: 'Textbook Library Setup',
      description: 'Create a digital library of textbooks for 50 students',
      targetAmount: 2500,
      currentAmount: 2500,
      progress: 100,
      deadline: '2024-02-10',
      status: 'completed',
      circle: 'Tech Leaders Circle',
      category: 'Resources'
    }
  ]

  // Mock badges
  const badges = [
    {
      id: 1,
      name: 'First Contribution',
      description: 'Made your first contribution',
      icon: CurrencyDollarIcon,
      earned: true,
      earnedDate: '2023-09-15',
      color: 'blue'
    },
    {
      id: 2,
      name: 'Mentor Master',
      description: 'Completed 100 hours of mentoring',
      icon: ChatBubbleLeftRightIcon,
      earned: true,
      earnedDate: '2024-01-20',
      color: 'purple'
    },
    {
      id: 3,
      name: 'Impact Champion',
      description: 'Top 3 circle in Impact League',
      icon: TrophyIcon,
      earned: true,
      earnedDate: '2024-02-01',
      color: 'gold'
    },
    {
      id: 4,
      name: 'Mission Complete',
      description: 'Completed 5 impact missions',
      icon: CheckCircleIcon,
      earned: true,
      earnedDate: '2024-02-10',
      color: 'green'
    },
    {
      id: 5,
      name: 'Student Success',
      description: 'Helped 10 students achieve academic goals',
      icon: AcademicCapIcon,
      earned: false,
      progress: 7,
      target: 10,
      color: 'orange'
    },
    {
      id: 6,
      name: 'Circle Leader',
      description: 'Lead a circle for 6 months',
      icon: UserGroupIcon,
      earned: false,
      progress: 4,
      target: 6,
      color: 'indigo'
    }
  ]

  // Current user's circle (mock)
  const currentCircle = leaderboard.find(c => c.circleName === 'The Navigators') || leaderboard[0]

  const getBadgeColor = (badge) => {
    const colors = {
      gold: 'bg-yellow-100 text-yellow-700 border-yellow-300',
      silver: 'bg-gray-100 text-gray-700 border-gray-300',
      bronze: 'bg-orange-100 text-orange-700 border-orange-300',
      blue: 'bg-blue-100 text-blue-700 border-blue-300',
      purple: 'bg-purple-100 text-purple-700 border-purple-300',
      green: 'bg-green-100 text-green-700 border-green-300',
      orange: 'bg-orange-100 text-orange-700 border-orange-300',
      indigo: 'bg-indigo-100 text-indigo-700 border-indigo-300'
    }
    return colors[badge] || colors.blue
  }

  const getRankIcon = (rank) => {
    if (rank === 1) return <TrophyIcon className="w-6 h-6 text-yellow-500" />
    if (rank === 2) return <TrophyIcon className="w-6 h-6 text-gray-400" />
    if (rank === 3) return <TrophyIcon className="w-6 h-6 text-orange-500" />
    return <span className="text-lg font-bold text-gray-400">#{rank}</span>
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Impact League</h1>
          <p className="text-gray-600">Compete, collaborate, and celebrate impact</p>
        </div>

        {/* Your Circle Stats */}
        {isSponsor && (
          <div className="rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90 mb-1">Your Circle</p>
                <h2 className="text-2xl font-bold mb-2">{currentCircle.circleName}</h2>
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-sm opacity-90">Impact Score</p>
                    <p className="text-3xl font-bold">{currentCircle.impactScore.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-90">Rank</p>
                    <p className="text-3xl font-bold">#{currentCircle.rank}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-90">Change</p>
                    <p className={`text-xl font-bold ${currentCircle.change.startsWith('+') ? 'text-green-200' : currentCircle.change.startsWith('-') ? 'text-red-200' : ''}`}>
                      {currentCircle.change}
                    </p>
                  </div>
                </div>
              </div>
              <div className="text-right">
                {currentCircle.badge && (
                  <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${getBadgeColor(currentCircle.badge)}`}>
                    <TrophyIcon className="w-5 h-5" />
                    <span className="font-medium capitalize">{currentCircle.badge} Medal</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          <button
            onClick={() => setSelectedTab('leaderboard')}
            className={`px-4 py-2 font-medium transition-colors ${
              selectedTab === 'leaderboard'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Leaderboard
          </button>
          <button
            onClick={() => setSelectedTab('missions')}
            className={`px-4 py-2 font-medium transition-colors ${
              selectedTab === 'missions'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Impact Missions
          </button>
          <button
            onClick={() => setSelectedTab('badges')}
            className={`px-4 py-2 font-medium transition-colors ${
              selectedTab === 'badges'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Badges & Achievements
          </button>
        </div>

        {/* Leaderboard Tab */}
        {selectedTab === 'leaderboard' && (
          <div>
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden mb-6">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Rank
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Circle Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Impact Score
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Members
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Students
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Contributions
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Mentoring Hours
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Missions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {leaderboard.map((circle) => (
                      <tr
                        key={circle.rank}
                        className={`hover:bg-gray-50 ${
                          circle.rank <= 3 ? 'bg-yellow-50/30' : ''
                        }`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {getRankIcon(circle.rank)}
                            {circle.change !== '0' && (
                              <span className={`text-xs ${
                                circle.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {circle.change}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                              <UserGroupIcon className="w-4 h-4 text-blue-600" />
                            </div>
                            <span className="font-medium text-gray-900">{circle.circleName}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-lg font-bold text-gray-900">
                            {circle.impactScore.toLocaleString()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {circle.members}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {circle.students}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          ${circle.contributions.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {circle.mentoringHours}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">
                            {circle.missionsCompleted}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">How Scores Are Calculated</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Mentoring Hours</span>
                    <span className="text-sm font-medium text-gray-900">30 points/hour</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Financial Contributions</span>
                    <span className="text-sm font-medium text-gray-900">50 points/$100</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Impact Missions</span>
                    <span className="text-sm font-medium text-gray-900">500 points/mission</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Student Progress</span>
                    <span className="text-sm font-medium text-gray-900">100 points/improvement</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Impact Missions Tab */}
        {selectedTab === 'missions' && (
          <div className="space-y-4">
            {impactMissions.map((mission) => (
              <div
                key={mission.id}
                className="rounded-xl bg-white shadow-sm border border-gray-200 p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-bold text-gray-900">{mission.title}</h3>
                      <span className={`text-xs px-2 py-1 rounded ${
                        mission.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {mission.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{mission.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Circle: {mission.circle}</span>
                      <span>Category: {mission.category}</span>
                      <span>Deadline: {mission.deadline}</span>
                    </div>
                  </div>
                </div>
                <div className="mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-600">Progress</span>
                    <span className="text-sm font-medium text-gray-900">
                      ${mission.currentAmount.toLocaleString()} / ${mission.targetAmount.toLocaleString()}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        mission.progress === 100 ? 'bg-green-600' : 'bg-blue-600'
                      }`}
                      style={{ width: `${mission.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{mission.progress}% complete</p>
                </div>
                {mission.status === 'active' && (
                  <button className="mt-4 text-sm text-blue-600 hover:text-blue-700 font-medium">
                    Contribute to Mission →
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Badges Tab */}
        {selectedTab === 'badges' && (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {badges.map((badge) => {
                const Icon = badge.icon
                return (
                  <div
                    key={badge.id}
                    className={`rounded-xl border-2 p-6 ${
                      badge.earned
                        ? getBadgeColor(badge.color)
                        : 'bg-gray-50 border-gray-200 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`p-3 rounded-lg ${
                        badge.earned ? 'bg-white' : 'bg-gray-200'
                      }`}>
                        <Icon className={`w-8 h-8 ${
                          badge.earned ? 'text-blue-600' : 'text-gray-400'
                        }`} />
                      </div>
                      <div className="flex-1">
                        <h3 className={`font-bold mb-1 ${
                          badge.earned ? 'text-gray-900' : 'text-gray-500'
                        }`}>
                          {badge.name}
                        </h3>
                        <p className={`text-sm mb-3 ${
                          badge.earned ? 'text-gray-600' : 'text-gray-400'
                        }`}>
                          {badge.description}
                        </p>
                        {badge.earned ? (
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            <CheckCircleIcon className="w-4 h-4 text-green-600" />
                            <span>Earned on {badge.earnedDate}</span>
                          </div>
                        ) : (
                          <div className="text-xs text-gray-500">
                            <p>Progress: {badge.progress}/{badge.target}</p>
                            <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${(badge.progress / badge.target) * 100}%` }}
                              ></div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default ImpactLeague
