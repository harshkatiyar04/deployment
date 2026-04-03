import { useState } from 'react'
import Layout from '../components/Layout'
import {
  UserGroupIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  UsersIcon,
  CurrencyDollarIcon,
  TrophyIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

function Circles() {
  const [searchTerm, setSearchTerm] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    leader: '',
    focusArea: '',
    status: 'active',
    initialMembers: ''
  })
  const [errors, setErrors] = useState({})

  // Mock circle data
  const circles = [
    {
      id: 1,
      name: 'The Navigators',
      description: 'Supporting university students in STEM fields',
      members: 12,
      students: 45,
      totalContributions: 125000,
      impactScore: 8.5,
      status: 'active',
      createdDate: '2023-09-15',
      leader: 'Jane Smith'
    },
    {
      id: 2,
      name: 'Tech Leaders Circle',
      description: 'Corporate sponsors supporting tech education',
      members: 8,
      students: 32,
      totalContributions: 98000,
      impactScore: 9.2,
      status: 'active',
      createdDate: '2023-10-20',
      leader: 'Michael Chen'
    },
    {
      id: 3,
      name: 'Future Leaders',
      description: 'Mentoring secondary school students',
      members: 15,
      students: 28,
      totalContributions: 67000,
      impactScore: 7.8,
      status: 'active',
      createdDate: '2024-01-05',
      leader: 'Sarah Johnson'
    },
    {
      id: 4,
      name: 'Community Impact',
      description: 'NGO partners supporting rural education',
      members: 20,
      students: 120,
      totalContributions: 245000,
      impactScore: 9.5,
      status: 'active',
      createdDate: '2023-08-10',
      leader: 'David Brown'
    },
    {
      id: 5,
      name: 'Alumni Network',
      description: 'University alumni giving back',
      members: 25,
      students: 38,
      totalContributions: 89000,
      impactScore: 8.1,
      status: 'pending',
      createdDate: '2024-02-01',
      leader: 'Emily Davis'
    }
  ]

  const filteredCircles = circles.filter(circle =>
    circle.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    circle.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}
    
    if (!formData.name.trim()) {
      newErrors.name = 'Circle name is required'
    }
    
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required'
    } else if (formData.description.trim().length < 10) {
      newErrors.description = 'Description must be at least 10 characters'
    }
    
    if (!formData.leader.trim()) {
      newErrors.leader = 'Circle leader is required'
    }
    
    if (!formData.focusArea.trim()) {
      newErrors.focusArea = 'Focus area is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (validateForm()) {
      // Here you would typically make an API call to create the circle
      console.log('Creating circle:', formData)
      
      // Reset form and close modal
      setFormData({
        name: '',
        description: '',
        leader: '',
        focusArea: '',
        status: 'active',
        initialMembers: ''
      })
      setIsModalOpen(false)
      setErrors({})
      
      // Show success message (you could add a toast notification here)
      alert('Circle created successfully!')
    }
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setFormData({
      name: '',
      description: '',
      leader: '',
      focusArea: '',
      status: 'active',
      initialMembers: ''
    })
    setErrors({})
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Circle Management</h1>
            <p className="text-gray-600">Manage sponsor circles and their activities</p>
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            <PlusIcon className="w-5 h-5" />
            Create Circle
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Circles</p>
            <p className="text-2xl font-bold text-gray-900">{circles.length}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Active Circles</p>
            <p className="text-2xl font-bold text-green-600">
              {circles.filter(c => c.status === 'active').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Members</p>
            <p className="text-2xl font-bold text-blue-600">
              {circles.reduce((sum, c) => sum + c.members, 0)}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Students Supported</p>
            <p className="text-2xl font-bold text-purple-600">
              {circles.reduce((sum, c) => sum + c.students, 0)}
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search circles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Circles Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCircles.map((circle) => (
            <div
              key={circle.id}
              className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <UserGroupIcon className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">{circle.name}</h3>
                    <p className="text-xs text-gray-500">Created {circle.createdDate}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded ${
                  circle.status === 'active' 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {circle.status}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-4">{circle.description}</p>

              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UsersIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Members</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{circle.members}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserGroupIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Students</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{circle.students}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CurrencyDollarIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Contributions</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    ${circle.totalContributions.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrophyIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Impact Score</span>
                  </div>
                  <span className="text-sm font-bold text-blue-600">{circle.impactScore}/10</span>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-3">Circle Leader: {circle.leader}</p>
                <div className="flex items-center gap-2">
                  <button className="flex-1 flex items-center justify-center gap-2 text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-lg text-sm">
                    <EyeIcon className="w-4 h-4" />
                    View
                  </button>
                  <button className="flex items-center justify-center gap-2 text-gray-600 hover:bg-gray-50 px-3 py-2 rounded-lg text-sm">
                    <PencilIcon className="w-4 h-4" />
                  </button>
                  <button className="flex items-center justify-center gap-2 text-red-600 hover:bg-red-50 px-3 py-2 rounded-lg text-sm">
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredCircles.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            <UserGroupIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No circles found matching your search</p>
          </div>
        )}

        {/* Create Circle Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            {/* Backdrop */}
            <div 
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={handleCloseModal}
            ></div>
            
            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
              <div 
                className="relative w-full max-w-2xl rounded-xl bg-white shadow-lg border border-gray-200"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">Create New Circle</h2>
                    <p className="text-sm text-gray-500 mt-1">Add a new sponsor circle to the platform</p>
                  </div>
                  <button
                    onClick={handleCloseModal}
                    className="text-gray-400 hover:text-gray-500 p-2 hover:bg-gray-100 rounded-lg"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>

                {/* Modal Body */}
                <form onSubmit={handleSubmit} className="p-6">
                  <div className="space-y-6">
                    {/* Circle Name */}
                    <div>
                      <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                        Circle Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        id="name"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        placeholder="e.g., The Navigators"
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors.name ? 'border-red-300' : 'border-gray-300'
                        }`}
                      />
                      {errors.name && (
                        <p className="mt-1 text-sm text-red-600">{errors.name}</p>
                      )}
                    </div>

                    {/* Description */}
                    <div>
                      <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                        Description <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleInputChange}
                        rows={4}
                        placeholder="Describe the circle's mission and focus area..."
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors.description ? 'border-red-300' : 'border-gray-300'
                        }`}
                      />
                      {errors.description && (
                        <p className="mt-1 text-sm text-red-600">{errors.description}</p>
                      )}
                      <p className="mt-1 text-xs text-gray-500">Minimum 10 characters</p>
                    </div>

                    {/* Circle Leader */}
                    <div>
                      <label htmlFor="leader" className="block text-sm font-medium text-gray-700 mb-2">
                        Circle Leader <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        id="leader"
                        name="leader"
                        value={formData.leader}
                        onChange={handleInputChange}
                        placeholder="e.g., Jane Smith"
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors.leader ? 'border-red-300' : 'border-gray-300'
                        }`}
                      />
                      {errors.leader && (
                        <p className="mt-1 text-sm text-red-600">{errors.leader}</p>
                      )}
                    </div>

                    {/* Focus Area */}
                    <div>
                      <label htmlFor="focusArea" className="block text-sm font-medium text-gray-700 mb-2">
                        Focus Area <span className="text-red-500">*</span>
                      </label>
                      <select
                        id="focusArea"
                        name="focusArea"
                        value={formData.focusArea}
                        onChange={handleInputChange}
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors.focusArea ? 'border-red-300' : 'border-gray-300'
                        }`}
                      >
                        <option value="">Select focus area</option>
                        <option value="STEM Education">STEM Education</option>
                        <option value="Arts & Humanities">Arts & Humanities</option>
                        <option value="Business & Entrepreneurship">Business & Entrepreneurship</option>
                        <option value="Healthcare & Medicine">Healthcare & Medicine</option>
                        <option value="Rural Education">Rural Education</option>
                        <option value="Primary Education">Primary Education</option>
                        <option value="Secondary Education">Secondary Education</option>
                        <option value="University Education">University Education</option>
                        <option value="Vocational Training">Vocational Training</option>
                        <option value="General Support">General Support</option>
                      </select>
                      {errors.focusArea && (
                        <p className="mt-1 text-sm text-red-600">{errors.focusArea}</p>
                      )}
                    </div>

                    {/* Status */}
                    <div>
                      <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                        Initial Status
                      </label>
                      <select
                        id="status"
                        name="status"
                        value={formData.status}
                        onChange={handleInputChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="active">Active</option>
                        <option value="pending">Pending</option>
                      </select>
                      <p className="mt-1 text-xs text-gray-500">Active circles are immediately visible, pending circles require approval</p>
                    </div>

                    {/* Initial Members (Optional) */}
                    <div>
                      <label htmlFor="initialMembers" className="block text-sm font-medium text-gray-700 mb-2">
                        Initial Members (Optional)
                      </label>
                      <input
                        type="number"
                        id="initialMembers"
                        name="initialMembers"
                        value={formData.initialMembers}
                        onChange={handleInputChange}
                        placeholder="Number of initial members"
                        min="0"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <p className="mt-1 text-xs text-gray-500">You can add members after creating the circle</p>
                    </div>
                  </div>

                  {/* Modal Footer */}
                  <div className="flex items-center justify-end gap-3 mt-8 pt-6 border-t border-gray-200">
                    <button
                      type="button"
                      onClick={handleCloseModal}
                      className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    >
                      Create Circle
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Circles
