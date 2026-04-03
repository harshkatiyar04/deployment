import { useState } from 'react'
import Layout from '../components/Layout'
import {
  BookOpenIcon,
  MagnifyingGlassIcon,
  AcademicCapIcon,
  SparklesIcon,
  PlayIcon,
  DocumentTextIcon,
  VideoCameraIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'

function Resources() {
  const { activePersona } = usePersona()
  const isPrimary = activePersona.subtype === 'primary'
  const isSecondary = activePersona.subtype === 'secondary'
  const isUniversity = activePersona.subtype === 'university'
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')

  // Primary school resources
  const primaryResources = [
    {
      id: 1,
      title: 'Fun Math Games',
      category: 'Mathematics',
      type: 'game',
      description: 'Play fun games to learn addition, subtraction, and multiplication!',
      icon: '🎮',
      color: 'blue',
      difficulty: 'Easy',
      duration: '15 min',
      completed: true
    },
    {
      id: 2,
      title: 'Story Time - The Magic Forest',
      category: 'Reading',
      type: 'story',
      description: 'Listen to an exciting story about adventures in a magic forest!',
      icon: '📖',
      color: 'green',
      difficulty: 'Easy',
      duration: '20 min',
      completed: false
    },
    {
      id: 3,
      title: 'Science Experiments - Water',
      category: 'Science',
      type: 'video',
      description: 'Learn about water through fun and safe experiments!',
      icon: '🔬',
      color: 'purple',
      difficulty: 'Medium',
      duration: '25 min',
      completed: false
    },
    {
      id: 4,
      title: 'ABC Learning - Letters & Sounds',
      category: 'English',
      type: 'interactive',
      description: 'Learn letters and their sounds with fun activities!',
      icon: '🔤',
      color: 'yellow',
      difficulty: 'Easy',
      duration: '20 min',
      completed: true
    },
    {
      id: 5,
      title: 'Drawing & Coloring - Animals',
      category: 'Arts',
      type: 'activity',
      description: 'Draw and color your favorite animals!',
      icon: '🎨',
      color: 'pink',
      difficulty: 'Easy',
      duration: '30 min',
      completed: false
    },
    {
      id: 6,
      title: 'Counting Numbers - 1 to 100',
      category: 'Mathematics',
      type: 'game',
      description: 'Practice counting from 1 to 100 with fun songs!',
      icon: '🔢',
      color: 'blue',
      difficulty: 'Easy',
      duration: '15 min',
      completed: true
    },
    {
      id: 7,
      title: 'Nature Walk - Plants & Trees',
      category: 'Science',
      type: 'video',
      description: 'Learn about different plants and trees around us!',
      icon: '🌳',
      color: 'green',
      difficulty: 'Easy',
      duration: '20 min',
      completed: false
    },
    {
      id: 8,
      title: 'Rhymes & Songs',
      category: 'English',
      type: 'video',
      description: 'Sing along to fun rhymes and songs!',
      icon: '🎵',
      color: 'yellow',
      difficulty: 'Easy',
      duration: '15 min',
      completed: false
    }
  ]

  // Secondary school resources
  const secondaryResources = [
    {
      id: 1,
      title: 'Advanced Mathematics - Calculus',
      category: 'Mathematics',
      type: 'video',
      description: 'Comprehensive video course covering calculus fundamentals and applications',
      icon: '📐',
      color: 'blue',
      difficulty: 'Advanced',
      duration: '2 hours',
      completed: true
    },
    {
      id: 2,
      title: 'Physics - Mechanics & Thermodynamics',
      category: 'Science',
      type: 'interactive',
      description: 'Interactive simulations and problem-solving exercises',
      icon: '⚛️',
      color: 'green',
      difficulty: 'Advanced',
      duration: '3 hours',
      completed: false
    },
    {
      id: 3,
      title: 'Chemistry Lab Manual',
      category: 'Science',
      type: 'document',
      description: 'Complete lab manual with experiments and safety guidelines',
      icon: '🧪',
      color: 'purple',
      difficulty: 'Medium',
      duration: '4 hours',
      completed: true
    },
    {
      id: 4,
      title: 'English Literature - Analysis Guide',
      category: 'English',
      type: 'document',
      description: 'Guide to analyzing poetry, prose, and drama',
      icon: '📝',
      color: 'yellow',
      difficulty: 'Medium',
      duration: '2 hours',
      completed: false
    },
    {
      id: 5,
      title: 'History - World War II',
      category: 'History',
      type: 'video',
      description: 'Documentary series on World War II with primary sources',
      icon: '📜',
      color: 'orange',
      difficulty: 'Medium',
      duration: '5 hours',
      completed: false
    },
    {
      id: 6,
      title: 'Biology - Cell Structure',
      category: 'Science',
      type: 'interactive',
      description: '3D interactive models of cell structures and functions',
      icon: '🔬',
      color: 'green',
      difficulty: 'Medium',
      duration: '1.5 hours',
      completed: true
    },
    {
      id: 7,
      title: 'Mathematics Practice Problems',
      category: 'Mathematics',
      type: 'document',
      description: 'Collection of practice problems with solutions',
      icon: '📊',
      color: 'blue',
      difficulty: 'Advanced',
      duration: 'Ongoing',
      completed: false
    },
    {
      id: 8,
      title: 'Essay Writing Workshop',
      category: 'English',
      type: 'video',
      description: 'Learn effective essay writing techniques and structure',
      icon: '✍️',
      color: 'yellow',
      difficulty: 'Medium',
      duration: '2 hours',
      completed: false
    }
  ]

  // University resources
  const universityResources = [
    {
      id: 1,
      title: 'Data Structures & Algorithms',
      category: 'Computer Science',
      type: 'course',
      description: 'Comprehensive course covering arrays, trees, graphs, and algorithm design',
      icon: '💻',
      color: 'blue',
      difficulty: 'Advanced',
      duration: '12 weeks',
      completed: true
    },
    {
      id: 2,
      title: 'Machine Learning Fundamentals',
      category: 'Computer Science',
      type: 'course',
      description: 'Introduction to ML concepts, neural networks, and practical applications',
      icon: '🤖',
      color: 'purple',
      difficulty: 'Advanced',
      duration: '10 weeks',
      completed: false
    },
    {
      id: 3,
      title: 'Research Methodology',
      category: 'Research',
      type: 'document',
      description: 'Guide to conducting academic research and writing research papers',
      icon: '📚',
      color: 'green',
      difficulty: 'Advanced',
      duration: '8 weeks',
      completed: true
    },
    {
      id: 4,
      title: 'Linear Algebra - Advanced Topics',
      category: 'Mathematics',
      type: 'video',
      description: 'Advanced linear algebra concepts for engineering and science',
      icon: '📐',
      color: 'blue',
      difficulty: 'Advanced',
      duration: '6 weeks',
      completed: false
    },
    {
      id: 5,
      title: 'Database Systems',
      category: 'Computer Science',
      type: 'course',
      description: 'SQL, NoSQL, database design, and optimization techniques',
      icon: '🗄️',
      color: 'indigo',
      difficulty: 'Advanced',
      duration: '10 weeks',
      completed: true
    },
    {
      id: 6,
      title: 'Software Engineering Practices',
      category: 'Computer Science',
      type: 'course',
      description: 'Agile methodologies, version control, testing, and deployment',
      icon: '⚙️',
      color: 'gray',
      difficulty: 'Advanced',
      duration: '8 weeks',
      completed: false
    },
    {
      id: 7,
      title: 'Academic Writing & Citation',
      category: 'Research',
      type: 'document',
      description: 'APA, MLA, and Chicago citation styles with examples',
      icon: '📝',
      color: 'yellow',
      difficulty: 'Medium',
      duration: '2 weeks',
      completed: true
    },
    {
      id: 8,
      title: 'Statistics & Probability',
      category: 'Mathematics',
      type: 'course',
      description: 'Statistical analysis, hypothesis testing, and probability theory',
      icon: '📊',
      color: 'green',
      difficulty: 'Advanced',
      duration: '10 weeks',
      completed: false
    }
  ]

  const resources = isPrimary ? primaryResources : isSecondary ? secondaryResources : universityResources

  const categories = isPrimary ? [
    { id: 'all', name: 'All', icon: '🌟' },
    { id: 'Mathematics', name: 'Math', icon: '🔢' },
    { id: 'Reading', name: 'Reading', icon: '📖' },
    { id: 'Science', name: 'Science', icon: '🔬' },
    { id: 'English', name: 'English', icon: '🔤' },
    { id: 'Arts', name: 'Arts', icon: '🎨' }
  ] : isSecondary ? [
    { id: 'all', name: 'All', icon: '📚' },
    { id: 'Mathematics', name: 'Mathematics', icon: '📐' },
    { id: 'Science', name: 'Science', icon: '🔬' },
    { id: 'English', name: 'English', icon: '📝' },
    { id: 'History', name: 'History', icon: '📜' }
  ] : [
    { id: 'all', name: 'All', icon: '📚' },
    { id: 'Computer Science', name: 'Computer Science', icon: '💻' },
    { id: 'Mathematics', name: 'Mathematics', icon: '📐' },
    { id: 'Research', name: 'Research', icon: '📊' }
  ]

  const filteredResources = resources.filter(resource => {
    const matchesSearch = resource.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         resource.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || resource.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const getTypeIcon = (type) => {
    const icons = {
      game: PlayIcon,
      story: BookOpenIcon,
      video: VideoCameraIcon,
      interactive: SparklesIcon,
      activity: DocumentTextIcon
    }
    return icons[type] || BookOpenIcon
  }

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-50 border-blue-200 text-blue-700',
      green: 'bg-green-50 border-green-200 text-green-700',
      purple: 'bg-purple-50 border-purple-200 text-purple-700',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
      pink: 'bg-pink-50 border-pink-200 text-pink-700'
    }
    return colors[color] || colors.blue
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className={`mb-6 ${
          isPrimary ? 'bg-gradient-to-r from-green-500 to-blue-500 text-white p-6 rounded-xl' :
          isSecondary ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white p-6 rounded-xl' :
          'bg-gradient-to-r from-indigo-500 to-purple-500 text-white p-6 rounded-xl'
        }`}>
          <h1 className={`text-3xl font-bold ${(isPrimary || isSecondary || isUniversity) ? 'text-white' : 'text-gray-900'} mb-2 flex items-center gap-2`}>
            {(isPrimary || isSecondary) && <span className="text-4xl">📚</span>}
            {isPrimary ? 'Learning Resources' : isSecondary ? 'Study Resources' : 'Learning Resources'}
          </h1>
          <p className={(isPrimary || isSecondary || isUniversity) ? 'text-white/90' : 'text-gray-600'}>
            {isPrimary ? 'Fun and exciting things to learn! 🎉' :
             isSecondary ? 'Access comprehensive study materials and courses' :
             'Browse courses, research materials, and academic resources'}
          </p>
        </div>

        {/* Stats Cards */}
        {(isPrimary || isSecondary || isUniversity) && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className={`rounded-xl bg-white shadow-sm border-2 p-4 text-center ${
              isPrimary ? 'border-blue-200' : isSecondary ? 'border-green-200' : 'border-indigo-200'
            }`}>
              {isPrimary ? <div className="text-3xl mb-2">📚</div> : <BookOpenIcon className="w-8 h-8 mx-auto mb-2 text-blue-600" />}
              <p className="text-sm text-gray-500 mb-1">Total Resources</p>
              <p className="text-2xl font-bold text-gray-900">{resources.length}</p>
            </div>
            <div className={`rounded-xl bg-white shadow-sm border-2 p-4 text-center ${
              isPrimary ? 'border-green-200' : isSecondary ? 'border-blue-200' : 'border-purple-200'
            }`}>
              {isPrimary ? <div className="text-3xl mb-2">✅</div> : <AcademicCapIcon className="w-8 h-8 mx-auto mb-2 text-green-600" />}
              <p className="text-sm text-gray-500 mb-1">Completed</p>
              <p className="text-2xl font-bold text-green-600">
                {resources.filter(r => r.completed).length}
              </p>
            </div>
            <div className={`rounded-xl bg-white shadow-sm border-2 p-4 text-center ${
              isPrimary ? 'border-purple-200' : isSecondary ? 'border-yellow-200' : 'border-blue-200'
            }`}>
              {isPrimary ? <div className="text-3xl mb-2">🎯</div> : <SparklesIcon className="w-8 h-8 mx-auto mb-2 text-purple-600" />}
              <p className="text-sm text-gray-500 mb-1">In Progress</p>
              <p className="text-2xl font-bold text-purple-600">
                {resources.filter(r => !r.completed).length}
              </p>
            </div>
            <div className={`rounded-xl bg-white shadow-sm border-2 p-4 text-center ${
              isPrimary ? 'border-yellow-200' : isSecondary ? 'border-orange-200' : 'border-gray-200'
            }`}>
              {isPrimary ? (
                <>
                  <div className="text-3xl mb-2">⭐</div>
                  <p className="text-sm text-gray-500 mb-1">Your Stars</p>
                  <p className="text-2xl font-bold text-yellow-600">
                    {resources.filter(r => r.completed).length * 5}
                  </p>
                </>
              ) : (
                <>
                  <AcademicCapIcon className="w-8 h-8 mx-auto mb-2 text-yellow-600" />
                  <p className="text-sm text-gray-500 mb-1">Hours Spent</p>
                  <p className="text-2xl font-bold text-yellow-600">
                    {Math.round(resources.filter(r => r.completed).length * 2.5)}
                  </p>
                </>
              )}
            </div>
          </div>
        )}

        {/* Search and Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4 mb-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder={
                  isPrimary ? "Search for fun learning activities..." :
                  isSecondary ? "Search study materials and courses..." :
                  "Search courses, research materials..."
                }
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Category Filters */}
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="text-lg">{category.icon}</span>
                <span className="text-sm font-medium">{category.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Resources Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredResources.map((resource) => {
            const TypeIcon = getTypeIcon(resource.type)
            return (
              <div
                key={resource.id}
                className={`rounded-xl bg-white shadow-sm border-2 p-6 hover:shadow-md transition-all ${
                  resource.completed
                    ? 'border-green-300 bg-green-50/30'
                    : getColorClasses(resource.color)
                }`}
              >
                {resource.completed && (
                  <div className="flex items-center justify-end mb-2">
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full flex items-center gap-1">
                      <span>✅</span> Completed!
                    </span>
                  </div>
                )}

                {isPrimary ? (
                  <div className="text-5xl mb-4 text-center">{resource.icon}</div>
                ) : (
                  <div className={`w-16 h-16 mx-auto mb-4 rounded-lg flex items-center justify-center ${
                    resource.completed ? 'bg-green-100' : 'bg-blue-100'
                  }`}>
                    {isSecondary || isUniversity ? (
                      <TypeIcon className={`w-8 h-8 ${
                        resource.completed ? 'text-green-600' : 'text-blue-600'
                      }`} />
                    ) : (
                      <span className="text-4xl">{resource.icon}</span>
                    )}
                  </div>
                )}

                <h3 className={`text-lg font-bold ${resource.completed ? 'text-gray-900' : 'text-gray-900'} mb-2 text-center`}>
                  {resource.title}
                </h3>

                <p className={`text-sm mb-4 text-center ${resource.completed ? 'text-gray-600' : 'text-gray-600'}`}>
                  {resource.description}
                </p>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Category:</span>
                    <span className="font-medium text-gray-900">{resource.category}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Duration:</span>
                    <span className="font-medium text-gray-900">{resource.duration}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Difficulty:</span>
                    <span className="font-medium text-gray-900">{resource.difficulty}</span>
                  </div>
                </div>

                <button
                  className={`w-full py-3 rounded-lg font-medium transition-colors ${
                    resource.completed
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  {resource.completed
                    ? (isPrimary ? '🎉 Completed! Review Again' : '✅ Completed - Review')
                    : (isPrimary ? '🚀 Start Learning!' : isSecondary ? '📖 Start Studying' : '🎓 Enroll Now')}
                </button>
              </div>
            )
          })}
        </div>

        {filteredResources.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            {isPrimary ? (
              <>
                <div className="text-6xl mb-3">🔍</div>
                <p className="text-gray-500 text-lg">No resources found!</p>
                <p className="text-gray-400 text-sm mt-2">Try searching for something else</p>
              </>
            ) : (
              <>
                <BookOpenIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No resources found matching your criteria</p>
              </>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Resources
