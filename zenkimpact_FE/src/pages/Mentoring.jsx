import { useState } from 'react'
import Layout from '../components/Layout'
import {
  ChatBubbleLeftRightIcon,
  CalendarIcon,
  ClockIcon,
  VideoCameraIcon,
  UserIcon,
  AcademicCapIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'

function Mentoring() {
  const { isSponsor } = usePersona()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [formData, setFormData] = useState({
    studentId: '',
    date: '',
    time: '',
    duration: '60',
    type: 'video',
    topic: '',
    notes: ''
  })

  // Mock mentoring sessions
  const sessions = [
    {
      id: 1,
      studentId: 'Student #7B34',
      studentName: 'Anonymized',
      date: '2024-02-20',
      time: '10:00 AM',
      duration: 60,
      type: 'video',
      topic: 'Career Guidance - Software Engineering',
      status: 'scheduled',
      notes: 'Discussing career paths in tech',
      mentor: 'Jane Smith'
    },
    {
      id: 2,
      studentId: 'Student #9K12',
      studentName: 'Anonymized',
      date: '2024-02-18',
      time: '2:00 PM',
      duration: 45,
      type: 'video',
      topic: 'Academic Support - Mathematics',
      status: 'completed',
      notes: 'Helped with calculus problems',
      mentor: 'Michael Chen',
      feedback: 'Very helpful session'
    },
    {
      id: 3,
      studentId: 'Student #5A23',
      studentName: 'Anonymized',
      date: '2024-02-15',
      time: '11:00 AM',
      duration: 90,
      type: 'in-person',
      topic: 'Life Skills - Time Management',
      status: 'completed',
      notes: 'Workshop on productivity',
      mentor: 'Sarah Johnson',
      feedback: 'Excellent workshop'
    },
    {
      id: 4,
      studentId: 'Student #7B34',
      studentName: 'Anonymized',
      date: '2024-02-12',
      time: '3:00 PM',
      duration: 60,
      type: 'video',
      topic: 'Career Guidance - Resume Building',
      status: 'completed',
      notes: 'Reviewed resume and provided feedback',
      mentor: 'Jane Smith',
      feedback: 'Great feedback received'
    },
    {
      id: 5,
      studentId: 'Student #8D67',
      studentName: 'Anonymized',
      date: '2024-02-25',
      time: '4:00 PM',
      duration: 60,
      type: 'video',
      topic: 'Academic Support - Physics',
      status: 'scheduled',
      notes: 'Upcoming session',
      mentor: 'David Brown'
    },
    {
      id: 6,
      studentId: 'Student #2F89',
      studentName: 'Anonymized',
      date: '2024-02-10',
      time: '1:00 PM',
      duration: 30,
      type: 'phone',
      topic: 'Quick Check-in',
      status: 'cancelled',
      notes: 'Student requested reschedule',
      mentor: 'Emily Davis'
    }
  ]

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = session.studentId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         session.topic.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         session.mentor.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'all' || session.status === filterStatus
    return matchesSearch && matchesStatus
  })

  const stats = {
    total: sessions.length,
    completed: sessions.filter(s => s.status === 'completed').length,
    scheduled: sessions.filter(s => s.status === 'scheduled').length,
    totalHours: sessions
      .filter(s => s.status === 'completed')
      .reduce((sum, s) => sum + s.duration, 0) / 60
  }

  const getStatusBadge = (status) => {
    const styles = {
      scheduled: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      cancelled: 'bg-red-100 text-red-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'video':
        return <VideoCameraIcon className="w-5 h-5 text-blue-600" />
      case 'in-person':
        return <UserIcon className="w-5 h-5 text-green-600" />
      case 'phone':
        return <ChatBubbleLeftRightIcon className="w-5 h-5 text-purple-600" />
      default:
        return <ChatBubbleLeftRightIcon className="w-5 h-5 text-gray-600" />
    }
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
    console.log('Scheduling session:', formData)
    setIsModalOpen(false)
    setFormData({
      studentId: '',
      date: '',
      time: '',
      duration: '60',
      type: 'video',
      topic: '',
      notes: ''
    })
    alert('Session scheduled successfully!')
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Mentoring</h1>
            <p className="text-gray-600">Schedule and manage mentoring sessions</p>
          </div>
          {isSponsor && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
            >
              <PlusIcon className="w-5 h-5" />
              Schedule Session
            </button>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Sessions</p>
              <ChatBubbleLeftRightIcon className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Completed</p>
              <CheckCircleIcon className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.completed}</p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Scheduled</p>
              <ClockIcon className="w-5 h-5 text-yellow-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.scheduled}</p>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Hours</p>
              <ClockIcon className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.totalHours.toFixed(1)}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by student, topic, or mentor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="scheduled">Scheduled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Sessions List */}
        <div className="space-y-4">
          {filteredSessions.map((session) => (
            <div
              key={session.id}
              className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4 flex-1">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    {getTypeIcon(session.type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-bold text-gray-900">{session.topic}</h3>
                      {getStatusBadge(session.status)}
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-2">
                      <div className="flex items-center gap-1">
                        <AcademicCapIcon className="w-4 h-4" />
                        <span>{session.studentId}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <UserIcon className="w-4 h-4" />
                        <span>Mentor: {session.mentor}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CalendarIcon className="w-4 h-4" />
                        <span>{session.date}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <ClockIcon className="w-4 h-4" />
                        <span>{session.time} ({session.duration} min)</span>
                      </div>
                    </div>
                    {session.notes && (
                      <p className="text-sm text-gray-600 mb-2">{session.notes}</p>
                    )}
                    {session.feedback && (
                      <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <p className="text-sm text-green-800">
                          <strong>Feedback:</strong> {session.feedback}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {session.status === 'scheduled' && (
                    <>
                      <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                        Join
                      </button>
                      <button className="text-gray-600 hover:text-gray-700 text-sm font-medium">
                        Reschedule
                      </button>
                    </>
                  )}
                  {session.status === 'completed' && (
                    <button className="text-green-600 hover:text-green-700 text-sm font-medium">
                      View Details
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredSessions.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            <ChatBubbleLeftRightIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No sessions found matching your criteria</p>
          </div>
        )}

        {/* Schedule Session Modal */}
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
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">Schedule Mentoring Session</h2>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Student ID <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="studentId"
                        value={formData.studentId}
                        onChange={handleInputChange}
                        required
                        placeholder="e.g., Student #7B34"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Date <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="date"
                          name="date"
                          value={formData.date}
                          onChange={handleInputChange}
                          required
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Time <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="time"
                          name="time"
                          value={formData.time}
                          onChange={handleInputChange}
                          required
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Duration (minutes) <span className="text-red-500">*</span>
                        </label>
                        <select
                          name="duration"
                          value={formData.duration}
                          onChange={handleInputChange}
                          required
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="30">30 minutes</option>
                          <option value="60">60 minutes</option>
                          <option value="90">90 minutes</option>
                          <option value="120">120 minutes</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Type <span className="text-red-500">*</span>
                        </label>
                        <select
                          name="type"
                          value={formData.type}
                          onChange={handleInputChange}
                          required
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="video">Video Call</option>
                          <option value="in-person">In-Person</option>
                          <option value="phone">Phone Call</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Topic <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="topic"
                        value={formData.topic}
                        onChange={handleInputChange}
                        required
                        placeholder="e.g., Career Guidance - Software Engineering"
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
                        Schedule Session
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

export default Mentoring
