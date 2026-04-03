import { useState } from 'react'
import Layout from '../components/Layout'
import {
  BuildingStorefrontIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  StarIcon,
  EyeIcon,
  XMarkIcon,
  AcademicCapIcon,
  BookOpenIcon,
  DevicePhoneMobileIcon,
  UserGroupIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { usePersona } from '../contexts/PersonaContext'

function Catalog() {
  const { activePersona } = usePersona()
  const isServiceProvider = activePersona.subtype === 'service'
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    price: '',
    description: '',
    duration: '',
    level: '',
    image: '📚'
  })

  // Mock catalog data
  const catalog = [
    {
      id: 1,
      name: 'Full-Stack Web Development Course',
      category: 'Courses',
      price: 1200,
      rating: 4.8,
      reviews: 234,
      image: '📚',
      description: 'Comprehensive 12-week course covering HTML, CSS, JavaScript, React, Node.js, and MongoDB',
      duration: '12 weeks',
      level: 'Intermediate',
      students: 1250,
      status: 'active',
      sales: 156
    },
    {
      id: 2,
      name: 'Mathematics Tutoring - Advanced Calculus',
      category: 'Tutors',
      price: 50,
      rating: 4.9,
      reviews: 89,
      image: '👨‍🏫',
      description: 'One-on-one tutoring sessions with experienced mathematics tutor',
      duration: 'Per hour',
      level: 'Advanced',
      students: 450,
      status: 'active',
      sales: 234
    },
    {
      id: 3,
      name: 'Data Science Bootcamp',
      category: 'Courses',
      price: 2500,
      rating: 4.9,
      reviews: 445,
      image: '📊',
      description: 'Intensive 16-week bootcamp covering Python, SQL, Machine Learning, and Data Visualization',
      duration: '16 weeks',
      level: 'Advanced',
      students: 2100,
      status: 'active',
      sales: 89
    },
    {
      id: 4,
      name: 'Public Speaking & Communication Skills',
      category: 'Skill-Based Extracurriculars',
      price: 350,
      rating: 4.9,
      reviews: 523,
      image: '🎤',
      description: '8-week program to develop confidence and communication skills',
      duration: '8 weeks',
      level: 'All levels',
      students: 1200,
      status: 'active',
      sales: 312
    },
    {
      id: 5,
      name: 'Chemistry Tutoring - Organic Chemistry',
      category: 'Tutors',
      price: 60,
      rating: 4.8,
      reviews: 134,
      image: '👩‍🔬',
      description: 'Specialized tutoring for organic chemistry concepts and problem-solving',
      duration: 'Per hour',
      level: 'Advanced',
      students: 320,
      status: 'draft',
      sales: 0
    }
  ]

  const categories = [
    { id: 'all', name: 'All Categories' },
    { id: 'Courses', name: 'Courses' },
    { id: 'Tutors', name: 'Tutors' },
    { id: 'Books & Materials', name: 'Books & Materials' },
    { id: 'Devices', name: 'Devices' },
    { id: 'Coaching Centres', name: 'Coaching Centres' },
    { id: 'Skill-Based Extracurriculars', name: 'Extracurriculars' }
  ]

  const filteredCatalog = catalog.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingProduct) {
      console.log('Updating product:', formData)
      alert('Product updated successfully!')
    } else {
      console.log('Creating product:', formData)
      alert('Product created successfully!')
    }
    setIsModalOpen(false)
    setEditingProduct(null)
    setFormData({
      name: '',
      category: '',
      price: '',
      description: '',
      duration: '',
      level: '',
      image: '📚'
    })
  }

  const handleEdit = (product) => {
    setEditingProduct(product)
    setFormData({
      name: product.name,
      category: product.category,
      price: product.price.toString(),
      description: product.description,
      duration: product.duration,
      level: product.level,
      image: product.image
    })
    setIsModalOpen(true)
  }

  const handleDelete = (productId) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      console.log('Deleting product:', productId)
      alert('Product deleted successfully!')
    }
  }

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      draft: 'bg-yellow-100 text-yellow-700',
      inactive: 'bg-gray-100 text-gray-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Product Catalog</h1>
            <p className="text-gray-600">Manage your products and services</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            <PlusIcon className="w-5 h-5" />
            Add Product
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Products</p>
            <p className="text-2xl font-bold text-gray-900">{catalog.length}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Active Products</p>
            <p className="text-2xl font-bold text-green-600">
              {catalog.filter(p => p.status === 'active').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Sales</p>
            <p className="text-2xl font-bold text-blue-600">
              {catalog.reduce((sum, p) => sum + p.sales, 0)}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Revenue</p>
            <p className="text-2xl font-bold text-purple-600">
              ${catalog.reduce((sum, p) => sum + (p.price * p.sales), 0).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4 mb-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search products..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="text-sm font-medium">{category.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCatalog.map((product) => (
            <div
              key={product.id}
              className="rounded-xl bg-white shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="text-4xl">{product.image}</div>
                {getStatusBadge(product.status)}
              </div>

              <h3 className="text-lg font-bold text-gray-900 mb-2">{product.name}</h3>

              <div className="flex items-center gap-2 mb-2">
                <div className="flex items-center">
                  {[...Array(5)].map((_, i) => (
                    <StarIcon
                      key={i}
                      className={`w-4 h-4 ${
                        i < Math.floor(product.rating)
                          ? 'text-yellow-400 fill-current'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-sm text-gray-600">
                  {product.rating} ({product.reviews})
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-4 line-clamp-2">{product.description}</p>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Price</span>
                  <span className="text-lg font-bold text-gray-900">${product.price.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Sales</span>
                  <span className="text-sm font-medium text-gray-900">{product.sales}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Students</span>
                  <span className="text-sm font-medium text-gray-900">{product.students.toLocaleString()}</span>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-200">
                <button
                  onClick={() => handleEdit(product)}
                  className="flex-1 flex items-center justify-center gap-2 text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-lg text-sm"
                >
                  <PencilIcon className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(product.id)}
                  className="flex items-center justify-center gap-2 text-red-600 hover:bg-red-50 px-3 py-2 rounded-lg text-sm"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {filteredCatalog.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            <BuildingStorefrontIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No products found matching your criteria</p>
          </div>
        )}

        {/* Add/Edit Product Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={() => {
                setIsModalOpen(false)
                setEditingProduct(null)
              }}
            ></div>
            <div className="flex min-h-full items-center justify-center p-4">
              <div
                className="relative w-full max-w-2xl rounded-xl bg-white shadow-lg border border-gray-200"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold text-gray-900">
                      {editingProduct ? 'Edit Product' : 'Add New Product'}
                    </h2>
                    <button
                      onClick={() => {
                        setIsModalOpen(false)
                        setEditingProduct(null)
                      }}
                      className="text-gray-400 hover:text-gray-500"
                    >
                      <XMarkIcon className="w-6 h-6" />
                    </button>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Product Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        required
                        placeholder="Enter product name"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Category <span className="text-red-500">*</span>
                        </label>
                        <select
                          name="category"
                          value={formData.category}
                          onChange={handleInputChange}
                          required
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">Select category</option>
                          <option value="Courses">Courses</option>
                          <option value="Tutors">Tutors</option>
                          <option value="Books & Materials">Books & Materials</option>
                          <option value="Devices">Devices</option>
                          <option value="Coaching Centres">Coaching Centres</option>
                          <option value="Skill-Based Extracurriculars">Extracurriculars</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Price ($) <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          name="price"
                          value={formData.price}
                          onChange={handleInputChange}
                          required
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        name="description"
                        value={formData.description}
                        onChange={handleInputChange}
                        required
                        rows={4}
                        placeholder="Enter product description"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Duration
                        </label>
                        <input
                          type="text"
                          name="duration"
                          value={formData.duration}
                          onChange={handleInputChange}
                          placeholder="e.g., 12 weeks"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Level
                        </label>
                        <input
                          type="text"
                          name="level"
                          value={formData.level}
                          onChange={handleInputChange}
                          placeholder="e.g., Intermediate"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                      <button
                        type="button"
                        onClick={() => {
                          setIsModalOpen(false)
                          setEditingProduct(null)
                        }}
                        className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                      >
                        {editingProduct ? 'Update Product' : 'Create Product'}
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

export default Catalog
