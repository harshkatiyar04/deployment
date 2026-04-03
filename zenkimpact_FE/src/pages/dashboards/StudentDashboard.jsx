import { usePersona } from '../../contexts/PersonaContext'
import {
  AcademicCapIcon,
  BookOpenIcon,
  ChartBarIcon,
  TrophyIcon,
  SparklesIcon,
  StarIcon,
  CalendarIcon,
  GiftIcon
} from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'

function StudentDashboard() {
  const { activePersona } = usePersona()
  const isPrimary = activePersona.subtype === 'primary'
  const isSecondary = activePersona.subtype === 'secondary'
  const isUniversity = activePersona.subtype === 'university'
  
  const getStudentType = () => {
    if (activePersona.subtype === 'primary') return 'Primary School Student'
    if (activePersona.subtype === 'secondary') return 'Secondary School Student'
    return 'University Student'
  }

  const kpiCards = [
    {
      title: 'Active Sessions',
      value: '12',
      icon: AcademicCapIcon,
      color: 'blue'
    },
    {
      title: 'Resources Available',
      value: '24',
      icon: BookOpenIcon,
      color: 'green'
    },
    {
      title: 'Progress Score',
      value: '85%',
      icon: ChartBarIcon,
      color: 'purple'
    },
    {
      title: 'Achievements',
      value: '8',
      icon: TrophyIcon,
      color: 'yellow'
    }
  ]

  // Student-specific data based on level
  const primaryAchievements = [
    { id: 1, name: 'Math Star', icon: '⭐', earned: true, date: '2024-02-15' },
    { id: 2, name: 'Reading Champion', icon: '📚', earned: true, date: '2024-02-10' },
    { id: 3, name: 'Science Explorer', icon: '🔬', earned: true, date: '2024-02-05' },
    { id: 4, name: 'Perfect Attendance', icon: '🎯', earned: false, progress: 8, target: 10 }
  ]

  const secondaryAchievements = [
    { id: 1, name: 'Academic Excellence', icon: '🏆', earned: true, date: '2024-02-15' },
    { id: 2, name: 'Research Project', icon: '📊', earned: true, date: '2024-02-10' },
    { id: 3, name: 'Leadership Badge', icon: '👑', earned: true, date: '2024-02-05' },
    { id: 4, name: 'Perfect Score', icon: '💯', earned: false, progress: 3, target: 5 }
  ]

  const universityAchievements = [
    { id: 1, name: 'Dean\'s List', icon: '🎓', earned: true, date: '2024-02-15' },
    { id: 2, name: 'Research Publication', icon: '📝', earned: true, date: '2024-02-10' },
    { id: 3, name: 'Internship Complete', icon: '💼', earned: true, date: '2024-02-05' },
    { id: 4, name: 'Thesis Milestone', icon: '📚', earned: false, progress: 60, target: 100 }
  ]

  const achievements = isPrimary ? primaryAchievements : isSecondary ? secondaryAchievements : universityAchievements

  const primarySessions = [
    { id: 1, subject: 'Mathematics', tutor: 'Ms. Sarah', date: 'Tomorrow', time: '3:00 PM', type: 'fun' },
    { id: 2, subject: 'Reading', tutor: 'Mr. John', date: 'Friday', time: '2:00 PM', type: 'story' }
  ]

  const secondarySessions = [
    { id: 1, subject: 'Advanced Mathematics', tutor: 'Dr. Smith', date: 'Tomorrow', time: '4:00 PM', type: 'tutoring' },
    { id: 2, subject: 'Physics - Mechanics', tutor: 'Prof. Johnson', date: 'Friday', time: '3:00 PM', type: 'tutoring' },
    { id: 3, subject: 'Career Guidance', tutor: 'Ms. Williams', date: 'Next Monday', time: '2:00 PM', type: 'mentoring' }
  ]

  const universitySessions = [
    { id: 1, subject: 'Data Structures & Algorithms', tutor: 'Prof. Chen', date: 'Tomorrow', time: '5:00 PM', type: 'tutoring' },
    { id: 2, subject: 'Research Methodology', tutor: 'Dr. Brown', date: 'Friday', time: '3:00 PM', type: 'mentoring' },
    { id: 3, subject: 'Career Development', tutor: 'Ms. Davis', date: 'Next Monday', time: '2:00 PM', type: 'mentoring' }
  ]

  const upcomingSessions = isPrimary ? primarySessions : isSecondary ? secondarySessions : universitySessions

  const getSubjects = () => {
    if (isPrimary) {
      return [
        { name: 'Mathematics', progress: 85, color: 'blue' },
        { name: 'Science', progress: 78, color: 'green' },
        { name: 'English', progress: 92, color: 'purple' }
      ]
    } else if (isSecondary) {
      return [
        { name: 'Mathematics', progress: 88, color: 'blue' },
        { name: 'Physics', progress: 82, color: 'green' },
        { name: 'Chemistry', progress: 85, color: 'purple' },
        { name: 'English Literature', progress: 90, color: 'yellow' },
        { name: 'History', progress: 79, color: 'orange' }
      ]
    } else {
      return [
        { name: 'Computer Science', progress: 92, color: 'blue' },
        { name: 'Mathematics', progress: 87, color: 'green' },
        { name: 'Research Project', progress: 75, color: 'purple' },
        { name: 'Elective Courses', progress: 89, color: 'yellow' }
      ]
    }
  }

  const subjects = getSubjects()

  return (
    <div>
      {/* Welcome Section */}
      <div className={`mb-6 ${
        isPrimary ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white p-6 rounded-xl' :
        isSecondary ? 'bg-gradient-to-r from-green-500 to-blue-500 text-white p-6 rounded-xl' :
        'bg-gradient-to-r from-indigo-500 to-purple-500 text-white p-6 rounded-xl'
      }`}>
        <h1 className={`text-3xl font-bold ${isPrimary || isSecondary || isUniversity ? 'text-white' : 'text-gray-900'} mb-2`}>
          {isPrimary ? '🌟 Hello! Welcome to Your Learning Space! 🌟' :
           isSecondary ? 'Welcome! Ready to Excel in Your Studies! 🎓' :
           `Welcome, Student #U9012`}
        </h1>
        <p className={isPrimary || isSecondary || isUniversity ? 'text-white/90' : 'text-gray-600'}>
          {isPrimary ? 'You are doing amazing! Keep learning and having fun! 🎉' :
           isSecondary ? 'Track your progress and achieve your academic goals! 📚' :
           `Viewing as: ${getStudentType()}`}
        </p>
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
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 mb-1">{card.title}</p>
                  <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${colorClasses[card.color]}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick Actions */}
      {(isPrimary || isSecondary || isUniversity) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Link
            to="/dashboard/resources"
            className={`rounded-xl bg-white shadow-sm border-2 p-6 hover:shadow-md transition-all hover:scale-105 text-center ${
              isPrimary ? 'border-blue-200' : isSecondary ? 'border-green-200' : 'border-indigo-200'
            }`}
          >
            <div className="text-4xl mb-2">{isPrimary ? '📚' : isSecondary ? '📖' : '📚'}</div>
            <p className="font-bold text-gray-900">Resources</p>
            <p className="text-xs text-gray-500">{isPrimary ? 'Learn & Play' : isSecondary ? 'Study Materials' : 'Learning Resources'}</p>
          </Link>
          <Link
            to="/dashboard/sessions"
            className={`rounded-xl bg-white shadow-sm border-2 p-6 hover:shadow-md transition-all hover:scale-105 text-center ${
              isPrimary ? 'border-green-200' : isSecondary ? 'border-blue-200' : 'border-purple-200'
            }`}
          >
            <div className="text-4xl mb-2">{isPrimary ? '🎓' : isSecondary ? '👨‍🏫' : '🎓'}</div>
            <p className="font-bold text-gray-900">Sessions</p>
            <p className="text-xs text-gray-500">{isPrimary ? 'Meet Teachers' : isSecondary ? 'Tutoring' : 'Mentoring'}</p>
          </Link>
          <Link
            to="/dashboard/progress"
            className={`rounded-xl bg-white shadow-sm border-2 p-6 hover:shadow-md transition-all hover:scale-105 text-center ${
              isPrimary ? 'border-purple-200' : isSecondary ? 'border-yellow-200' : 'border-blue-200'
            }`}
          >
            <div className="text-4xl mb-2">📊</div>
            <p className="font-bold text-gray-900">Progress</p>
            <p className="text-xs text-gray-500">{isPrimary ? 'See Growth' : isSecondary ? 'Track Performance' : 'View Analytics'}</p>
          </Link>
          <Link
            to="/dashboard/marketplace"
            className={`rounded-xl bg-white shadow-sm border-2 p-6 hover:shadow-md transition-all hover:scale-105 text-center ${
              isPrimary ? 'border-yellow-200' : isSecondary ? 'border-orange-200' : 'border-gray-200'
            }`}
          >
            <div className="text-4xl mb-2">🛒</div>
            <p className="font-bold text-gray-900">Marketplace</p>
            <p className="text-xs text-gray-500">{isPrimary ? 'Get Supplies' : isSecondary ? 'Buy Materials' : 'Shop Resources'}</p>
          </Link>
        </div>
      )}

      {/* Recent Activity */}
      <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className={`text-xl font-bold text-gray-900 mb-4 ${(isPrimary || isSecondary) ? 'flex items-center gap-2' : ''}`}>
          {(isPrimary || isSecondary) && <SparklesIcon className="w-6 h-6 text-yellow-500" />}
          {isPrimary ? 'What\'s New!' : isSecondary ? 'Recent Updates' : 'Recent Activity'}
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              {isPrimary ? <span className="text-2xl">🎓</span> : <AcademicCapIcon className="w-5 h-5 text-blue-600" />}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                {isPrimary ? '🎉 New fun learning session scheduled!' :
                 isSecondary ? 'New tutoring session scheduled' :
                 'New mentoring session scheduled'}
              </p>
              <p className="text-xs text-gray-500">
                {isPrimary ? 'Tomorrow at 3:00 PM' : isSecondary ? 'Tomorrow, 4:00 PM' : 'Tomorrow, 5:00 PM'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              {isPrimary ? <span className="text-2xl">📚</span> : <BookOpenIcon className="w-5 h-5 text-green-600" />}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                {isPrimary ? '✨ New fun resources available!' :
                 isSecondary ? 'New study materials added' :
                 'New course materials available'}
              </p>
              <p className="text-xs text-gray-500">
                {isPrimary ? 'Check them out!' : isSecondary ? '1 day ago' : '2 days ago'}
              </p>
            </div>
          </div>
          {(isPrimary || isSecondary) && (
            <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg">
              <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                {isPrimary ? <span className="text-2xl">⭐</span> : <TrophyIcon className="w-5 h-5 text-yellow-600" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {isPrimary ? '🏆 You earned a new achievement!' : '🏆 Achievement unlocked!'}
                </p>
                <p className="text-xs text-gray-500">
                  {isPrimary ? 'Math Star - Great job!' : 'Academic Excellence - Well done!'}
                </p>
              </div>
            </div>
          )}
          {isUniversity && (
            <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Progress report updated</p>
                <p className="text-xs text-gray-500">Your academic performance has improved</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Progress Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            {isPrimary ? 'Learning Progress' : isSecondary ? 'Academic Performance' : 'Course Progress'}
          </h2>
          <div className="space-y-4">
            {subjects.map((subject) => (
              <div key={subject.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">{subject.name}</span>
                  <span className="text-gray-900 font-medium">{subject.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      subject.color === 'blue' ? 'bg-blue-600' :
                      subject.color === 'green' ? 'bg-green-600' :
                      subject.color === 'purple' ? 'bg-purple-600' :
                      subject.color === 'yellow' ? 'bg-yellow-600' :
                      'bg-orange-600'
                    }`}
                    style={{ width: `${subject.progress}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className={`text-xl font-bold text-gray-900 mb-4 ${(isPrimary || isSecondary) ? 'flex items-center gap-2' : ''}`}>
            {(isPrimary || isSecondary) && <CalendarIcon className="w-5 h-5 text-blue-600" />}
            {isPrimary ? 'Upcoming Fun Sessions!' : isSecondary ? 'Upcoming Sessions' : 'Upcoming Sessions'}
          </h2>
          <div className="space-y-3">
            {upcomingSessions.map((session) => (
              <div
                key={session.id}
                className={`p-4 border-2 rounded-lg ${
                  isPrimary
                    ? 'border-blue-100 bg-blue-50'
                    : isSecondary
                    ? 'border-green-100 bg-green-50'
                    : 'border-purple-100 bg-purple-50'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {isPrimary && <span className="text-2xl">{session.type === 'fun' ? '🎮' : '📖'}</span>}
                  <p className="text-sm font-bold text-gray-900">{session.subject}</p>
                </div>
                <p className="text-xs text-gray-600">With {session.tutor}</p>
                <p className="text-xs text-gray-500 mt-1">{session.date} at {session.time}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Achievements Section */}
      {(isPrimary || isSecondary || isUniversity) && (
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mt-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrophyIcon className="w-6 h-6 text-yellow-500" />
            {isPrimary ? 'Your Achievements! 🏆' : isSecondary ? 'Your Achievements' : 'Academic Achievements'}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {achievements.map((achievement) => (
              <div
                key={achievement.id}
                className={`p-4 rounded-lg border-2 text-center ${
                  achievement.earned
                    ? isPrimary ? 'bg-yellow-50 border-yellow-300' :
                      isSecondary ? 'bg-green-50 border-green-300' :
                      'bg-purple-50 border-purple-300'
                    : 'bg-gray-50 border-gray-200 opacity-60'
                }`}
              >
                {isPrimary ? (
                  <div className="text-4xl mb-2">{achievement.icon}</div>
                ) : (
                  <div className={`w-12 h-12 mx-auto mb-2 rounded-full flex items-center justify-center ${
                    achievement.earned
                      ? isSecondary ? 'bg-green-100' : 'bg-purple-100'
                      : 'bg-gray-200'
                  }`}>
                    <TrophyIcon className={`w-6 h-6 ${
                      achievement.earned
                        ? isSecondary ? 'text-green-600' : 'text-purple-600'
                        : 'text-gray-400'
                    }`} />
                  </div>
                )}
                <p className={`text-sm font-bold ${achievement.earned ? 'text-gray-900' : 'text-gray-500'}`}>
                  {achievement.name}
                </p>
                {achievement.earned ? (
                  <p className="text-xs text-gray-500 mt-1">Earned {achievement.date}</p>
                ) : (
                  <div className="mt-2">
                    <p className="text-xs text-gray-500">Progress: {achievement.progress}{achievement.target ? `/${achievement.target}` : '%'}</p>
                    {achievement.target && (
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div
                          className={`h-2 rounded-full ${
                            isSecondary ? 'bg-green-500' : 'bg-purple-500'
                          }`}
                          style={{ width: `${(achievement.progress / achievement.target) * 100}%` }}
                        ></div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default StudentDashboard


