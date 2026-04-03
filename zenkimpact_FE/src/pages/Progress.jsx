import { useState } from 'react'
import Layout from '../components/Layout'
import {
  ChartBarIcon,
  TrophyIcon,
  StarIcon,
  AcademicCapIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  CalendarIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'
import { Line, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
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
  Title,
  Tooltip,
  Legend
)

function Progress() {
  const { activePersona } = usePersona()
  const isPrimary = activePersona.subtype === 'primary'
  const isSecondary = activePersona.subtype === 'secondary'
  const isUniversity = activePersona.subtype === 'university'
  const [selectedPeriod, setSelectedPeriod] = useState('month')

  // Primary school progress data
  const primarySubjects = [
    { name: 'Mathematics', progress: 85, color: 'blue', trend: '+5%', stars: 45 },
    { name: 'Science', progress: 78, color: 'green', trend: '+3%', stars: 38 },
    { name: 'English', progress: 92, color: 'purple', trend: '+7%', stars: 52 },
    { name: 'Reading', progress: 88, color: 'yellow', trend: '+4%', stars: 48 }
  ]

  // Secondary school progress data
  const secondarySubjects = [
    { name: 'Mathematics', progress: 88, color: 'blue', trend: '+6%', grade: 'A' },
    { name: 'Physics', progress: 82, color: 'green', trend: '+4%', grade: 'B+' },
    { name: 'Chemistry', progress: 85, color: 'purple', trend: '+5%', grade: 'A-' },
    { name: 'English Literature', progress: 90, color: 'yellow', trend: '+7%', grade: 'A' },
    { name: 'History', progress: 79, color: 'orange', trend: '+3%', grade: 'B' }
  ]

  // University progress data
  const universitySubjects = [
    { name: 'Computer Science', progress: 92, color: 'blue', trend: '+8%', gpa: 3.8 },
    { name: 'Mathematics', progress: 87, color: 'green', trend: '+5%', gpa: 3.7 },
    { name: 'Research Project', progress: 75, color: 'purple', trend: '+10%', gpa: 3.5 },
    { name: 'Elective Courses', progress: 89, color: 'yellow', trend: '+6%', gpa: 3.9 }
  ]

  const subjects = isPrimary ? primarySubjects : isSecondary ? secondarySubjects : universitySubjects

  // Primary achievements
  const primaryAchievements = [
    { id: 1, name: 'Math Master', icon: '⭐', earned: true, date: '2024-02-15', description: 'Completed 10 math lessons!' },
    { id: 2, name: 'Reading Champion', icon: '📚', earned: true, date: '2024-02-10', description: 'Read 5 stories!' },
    { id: 3, name: 'Science Explorer', icon: '🔬', earned: true, date: '2024-02-05', description: 'Completed science experiments!' },
    { id: 4, name: 'Perfect Week', icon: '🎯', earned: false, progress: 4, target: 7, description: 'Complete all activities for a week!' }
  ]

  // Secondary achievements
  const secondaryAchievements = [
    { id: 1, name: 'Academic Excellence', icon: '🏆', earned: true, date: '2024-02-15', description: 'Maintained A average for semester' },
    { id: 2, name: 'Research Project', icon: '📊', earned: true, date: '2024-02-10', description: 'Completed major research project' },
    { id: 3, name: 'Leadership Badge', icon: '👑', earned: true, date: '2024-02-05', description: 'Led group project successfully' },
    { id: 4, name: 'Perfect Score', icon: '💯', earned: false, progress: 3, target: 5, description: 'Achieve perfect scores in 5 subjects' }
  ]

  // University achievements
  const universityAchievements = [
    { id: 1, name: 'Dean\'s List', icon: '🎓', earned: true, date: '2024-02-15', description: 'Maintained GPA above 3.7' },
    { id: 2, name: 'Research Publication', icon: '📝', earned: true, date: '2024-02-10', description: 'Published research paper' },
    { id: 3, name: 'Internship Complete', icon: '💼', earned: true, date: '2024-02-05', description: 'Completed industry internship' },
    { id: 4, name: 'Thesis Milestone', icon: '📚', earned: false, progress: 60, target: 100, description: 'Complete thesis to 100%' }
  ]

  const achievements = isPrimary ? primaryAchievements : isSecondary ? secondaryAchievements : universityAchievements

  const getProgressData = () => {
    if (isPrimary) {
      return {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        datasets: [
          {
            label: 'Math',
            data: [70, 75, 80, 85],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4
          },
          {
            label: 'Science',
            data: [65, 70, 75, 78],
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4
          },
          {
            label: 'English',
            data: [80, 85, 90, 92],
            borderColor: 'rgb(139, 92, 246)',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            tension: 0.4
          }
        ]
      }
    } else if (isSecondary) {
      return {
        labels: ['Semester 1', 'Semester 2', 'Semester 3', 'Semester 4'],
        datasets: [
          {
            label: 'Mathematics',
            data: [82, 85, 87, 88],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4
          },
          {
            label: 'Physics',
            data: [75, 78, 80, 82],
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4
          },
          {
            label: 'Chemistry',
            data: [78, 82, 84, 85],
            borderColor: 'rgb(139, 92, 246)',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            tension: 0.4
          }
        ]
      }
    } else {
      return {
        labels: ['Year 1', 'Year 2', 'Year 3', 'Year 4'],
        datasets: [
          {
            label: 'Computer Science',
            data: [85, 88, 90, 92],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4
          },
          {
            label: 'Mathematics',
            data: [80, 83, 85, 87],
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4
          },
          {
            label: 'Research',
            data: [60, 68, 72, 75],
            borderColor: 'rgb(139, 92, 246)',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            tension: 0.4
          }
        ]
      }
    }
  }

  const progressData = getProgressData()

  const getActivityData = () => {
    if (isPrimary) {
      return {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Activities Completed',
            data: [3, 5, 4, 6, 5, 2, 1],
            backgroundColor: 'rgba(59, 130, 246, 0.8)',
            borderRadius: 8
          }
        ]
      }
    } else if (isSecondary) {
      return {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Study Hours',
            data: [2, 3, 2.5, 4, 3.5, 2, 1],
            backgroundColor: 'rgba(16, 185, 129, 0.8)',
            borderRadius: 8
          }
        ]
      }
    } else {
      return {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Study Hours',
            data: [4, 5, 4.5, 6, 5.5, 3, 2],
            backgroundColor: 'rgba(139, 92, 246, 0.8)',
            borderRadius: 8
          }
        ]
      }
    }
  }

  const activityData = getActivityData()

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top'
      }
    }
  }

  const totalStars = subjects.reduce((sum, s) => sum + s.stars, 0)
  const averageProgress = Math.round(subjects.reduce((sum, s) => sum + s.progress, 0) / subjects.length)

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className={`mb-6 ${
          isPrimary ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white p-6 rounded-xl' :
          isSecondary ? 'bg-gradient-to-r from-green-500 to-blue-500 text-white p-6 rounded-xl' :
          isUniversity ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white p-6 rounded-xl' :
          ''
        }`}>
          <h1 className={`text-3xl font-bold ${
            (isPrimary || isSecondary || isUniversity) ? 'text-white' : 'text-gray-900'
          } mb-2 flex items-center gap-2`}>
            {(isPrimary || isSecondary) && <span className="text-4xl">📊</span>}
            {isPrimary ? 'Your Learning Progress!' :
             isSecondary ? 'Academic Performance' :
             isUniversity ? 'Academic Progress' :
             'Progress'}
          </h1>
          <p className={(isPrimary || isSecondary || isUniversity) ? 'text-white/90' : 'text-gray-600'}>
            {isPrimary ? 'See how much you\'ve learned! Keep going! 🌟' :
             isSecondary ? 'Track your academic performance and achievements' :
             isUniversity ? 'Monitor your academic progress and research milestones' :
             'Track your learning progress and achievements'}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className={`rounded-xl bg-white shadow-sm border-2 ${isPrimary ? 'border-blue-200' : 'border-gray-200'} p-6`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Overall Progress</p>
              {isPrimary ? <span className="text-2xl">📈</span> : <ChartBarIcon className="w-5 h-5 text-blue-600" />}
            </div>
            <p className="text-3xl font-bold text-gray-900">{averageProgress}%</p>
            <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
              <ArrowTrendingUpIcon className="w-3 h-3" />
              Great job!
            </p>
          </div>

          <div className={`rounded-xl bg-white shadow-sm border-2 ${isPrimary ? 'border-yellow-200' : 'border-gray-200'} p-6`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Stars</p>
              {isPrimary ? <span className="text-2xl">⭐</span> : <StarIcon className="w-5 h-5 text-yellow-600" />}
            </div>
            <p className="text-3xl font-bold text-gray-900">{totalStars}</p>
            <p className="text-xs text-gray-500 mt-1">Keep earning more!</p>
          </div>

          <div className={`rounded-xl bg-white shadow-sm border-2 ${isPrimary ? 'border-green-200' : 'border-gray-200'} p-6`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Achievements</p>
              {isPrimary ? <span className="text-2xl">🏆</span> : <TrophyIcon className="w-5 h-5 text-green-600" />}
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {achievements.filter(a => a.earned).length}
            </p>
            <p className="text-xs text-gray-500 mt-1">Earned!</p>
          </div>

          <div className={`rounded-xl bg-white shadow-sm border-2 ${isPrimary ? 'border-purple-200' : 'border-gray-200'} p-6`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Subjects</p>
              {isPrimary ? <span className="text-2xl">📚</span> : <AcademicCapIcon className="w-5 h-5 text-purple-600" />}
            </div>
            <p className="text-3xl font-bold text-gray-900">{subjects.length}</p>
            <p className="text-xs text-gray-500 mt-1">Active</p>
          </div>
        </div>

        {/* Subject Progress */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className={`text-xl font-bold text-gray-900 mb-4 ${(isPrimary || isSecondary) ? 'flex items-center gap-2' : ''}`}>
            {(isPrimary || isSecondary) && <SparklesIcon className="w-6 h-6 text-yellow-500" />}
            {isPrimary ? 'Your Subjects Progress' :
             isSecondary ? 'Subject Performance' :
             isUniversity ? 'Course Progress' :
             'Subject Progress'}
          </h2>
          <div className="space-y-4">
            {subjects.map((subject) => (
              <div key={subject.name}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {isPrimary && <span className="text-2xl">
                      {subject.name === 'Mathematics' ? '🔢' :
                       subject.name === 'Science' ? '🔬' :
                       subject.name === 'English' ? '🔤' : '📖'}
                    </span>}
                    <span className="text-sm font-medium text-gray-900">{subject.name}</span>
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded flex items-center gap-1">
                      <ArrowTrendingUpIcon className="w-3 h-3" />
                      {subject.trend}
                    </span>
                    {isSecondary && subject.grade && (
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded font-medium">
                        Grade: {subject.grade}
                      </span>
                    )}
                    {isUniversity && subject.gpa && (
                      <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded font-medium">
                        GPA: {subject.gpa}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {isPrimary && subject.stars && (
                      <div className="flex items-center gap-1">
                        <span className="text-yellow-500">⭐</span>
                        <span className="text-sm font-medium text-gray-900">{subject.stars}</span>
                      </div>
                    )}
                    <span className="text-sm font-bold text-gray-900">{subject.progress}%</span>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
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

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h2 className={`text-xl font-bold text-gray-900 mb-4 ${isPrimary ? 'flex items-center gap-2' : ''}`}>
              {isPrimary && <span className="text-2xl">📈</span>}
              {isPrimary ? 'Progress Over Time' : 'Progress Trend'}
            </h2>
            <div className="h-64">
              <Line data={progressData} options={chartOptions} />
            </div>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <h2 className={`text-xl font-bold text-gray-900 mb-4 ${(isPrimary || isSecondary) ? 'flex items-center gap-2' : ''}`}>
              {(isPrimary || isSecondary) && <span className="text-2xl">📅</span>}
              {isPrimary ? 'This Week\'s Activities' :
               isSecondary ? 'Weekly Study Hours' :
               isUniversity ? 'Weekly Study Hours' :
               'Weekly Activity'}
            </h2>
            <div className="h-64">
              <Bar data={activityData} options={chartOptions} />
            </div>
          </div>
        </div>

        {/* Achievements */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
          <h2 className={`text-xl font-bold text-gray-900 mb-4 ${(isPrimary || isSecondary) ? 'flex items-center gap-2' : ''}`}>
            {(isPrimary || isSecondary) && <TrophyIcon className="w-6 h-6 text-yellow-500" />}
            {isPrimary ? 'Your Achievements! 🏆' :
             isSecondary ? 'Your Achievements' :
             isUniversity ? 'Academic Achievements' :
             'Achievements'}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                <h3 className={`font-bold mb-1 ${achievement.earned ? 'text-gray-900' : 'text-gray-500'}`}>
                  {achievement.name}
                </h3>
                <p className={`text-xs mb-2 ${achievement.earned ? 'text-gray-600' : 'text-gray-400'}`}>
                  {achievement.description}
                </p>
                {achievement.earned ? (
                  <div className="flex items-center justify-center gap-1 text-xs text-green-600">
                    <CalendarIcon className="w-3 h-3" />
                    <span>Earned {achievement.date}</span>
                  </div>
                ) : (
                  <div className="text-xs text-gray-500">
                    <p>Progress: {achievement.progress}{achievement.target ? `/${achievement.target}` : '%'}</p>
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
      </div>
    </Layout>
  )
}

export default Progress
