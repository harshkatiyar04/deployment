import { useState } from 'react'
import Layout from '../components/Layout'
import {
  MagnifyingGlassIcon,
  ShoppingBagIcon,
  BuildingStorefrontIcon,
  StarIcon,
  PlusIcon,
  MinusIcon,
  XMarkIcon,
  CheckCircleIcon,
  TruckIcon,
  AcademicCapIcon,
  BookOpenIcon,
  DevicePhoneMobileIcon,
  UserGroupIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'

function Marketplace() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [cart, setCart] = useState([])
  const [isCartOpen, setIsCartOpen] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [isProductModalOpen, setIsProductModalOpen] = useState(false)

  // Mock products/services
  const products = [
    {
      id: 1,
      name: 'Full-Stack Web Development Course',
      supplier: 'EduTech Solutions',
      category: 'Courses',
      price: 1200,
      rating: 4.8,
      reviews: 234,
      image: '📚',
      description: 'Comprehensive 12-week course covering HTML, CSS, JavaScript, React, Node.js, and MongoDB',
      duration: '12 weeks',
      level: 'Intermediate',
      students: 1250,
      featured: true
    },
    {
      id: 2,
      name: 'Mathematics Tutoring - Advanced Calculus',
      supplier: 'ABC Tutoring Services',
      category: 'Tutors',
      price: 50,
      rating: 4.9,
      reviews: 89,
      image: '👨‍🏫',
      description: 'One-on-one tutoring sessions with experienced mathematics tutor',
      duration: 'Per hour',
      level: 'Advanced',
      students: 450,
      featured: false
    },
    {
      id: 3,
      name: 'MacBook Air M2 - 13 inch',
      supplier: 'XYZ Supplies Co.',
      category: 'Devices',
      price: 1200,
      rating: 4.7,
      reviews: 156,
      image: '💻',
      description: 'Latest MacBook Air with M2 chip, perfect for students and developers',
      duration: 'One-time purchase',
      level: 'All levels',
      students: 320,
      featured: true
    },
    {
      id: 4,
      name: 'Complete Python Programming Book Set',
      supplier: 'Learning Materials Inc.',
      category: 'Books & Materials',
      price: 85,
      rating: 4.6,
      reviews: 312,
      image: '📖',
      description: 'Set of 3 comprehensive Python programming books for beginners to advanced',
      duration: 'Lifetime access',
      level: 'All levels',
      students: 890,
      featured: false
    },
    {
      id: 5,
      name: 'Data Science Bootcamp',
      supplier: 'Online Academy Pro',
      category: 'Courses',
      price: 2500,
      rating: 4.9,
      reviews: 445,
      image: '📊',
      description: 'Intensive 16-week bootcamp covering Python, SQL, Machine Learning, and Data Visualization',
      duration: '16 weeks',
      level: 'Advanced',
      students: 2100,
      featured: true
    },
    {
      id: 6,
      name: 'Physics Coaching - Weekly Sessions',
      supplier: 'ABC Tutoring Services',
      category: 'Coaching Centres',
      price: 200,
      rating: 4.7,
      reviews: 178,
      image: '🏢',
      description: 'Weekly group coaching sessions for physics students',
      duration: 'Per month',
      level: 'Intermediate',
      students: 280,
      featured: false
    },
    {
      id: 7,
      name: 'iPad Pro 12.9 inch',
      supplier: 'XYZ Supplies Co.',
      category: 'Devices',
      price: 1100,
      rating: 4.8,
      reviews: 267,
      image: '📱',
      description: 'Latest iPad Pro with M2 chip, ideal for note-taking and creative work',
      duration: 'One-time purchase',
      level: 'All levels',
      students: 540,
      featured: false
    },
    {
      id: 8,
      name: 'Public Speaking & Communication Skills',
      supplier: 'Online Academy Pro',
      category: 'Skill-Based Extracurriculars',
      price: 350,
      rating: 4.9,
      reviews: 523,
      image: '🎤',
      description: '8-week program to develop confidence and communication skills',
      duration: '8 weeks',
      level: 'All levels',
      students: 1200,
      featured: true
    },
    {
      id: 9,
      name: 'Chemistry Tutoring - Organic Chemistry',
      supplier: 'ABC Tutoring Services',
      category: 'Tutors',
      price: 60,
      rating: 4.8,
      reviews: 134,
      image: '👩‍🔬',
      description: 'Specialized tutoring for organic chemistry concepts and problem-solving',
      duration: 'Per hour',
      level: 'Advanced',
      students: 320,
      featured: false
    },
    {
      id: 10,
      name: 'SAT/ACT Prep Course',
      supplier: 'EduTech Solutions',
      category: 'Courses',
      price: 800,
      rating: 4.7,
      reviews: 456,
      image: '✏️',
      description: 'Comprehensive test preparation course with practice tests and strategies',
      duration: '10 weeks',
      level: 'High School',
      students: 1800,
      featured: false
    }
  ]

  const categories = [
    { id: 'all', name: 'All Categories', icon: ShoppingBagIcon },
    { id: 'Courses', name: 'Courses', icon: AcademicCapIcon },
    { id: 'Tutors', name: 'Tutors', icon: UserGroupIcon },
    { id: 'Books & Materials', name: 'Books & Materials', icon: BookOpenIcon },
    { id: 'Devices', name: 'Devices', icon: DevicePhoneMobileIcon },
    { id: 'Coaching Centres', name: 'Coaching Centres', icon: BuildingStorefrontIcon },
    { id: 'Skill-Based Extracurriculars', name: 'Extracurriculars', icon: SparklesIcon }
  ]

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.supplier.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || product.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const addToCart = (product) => {
    const existingItem = cart.find(item => item.id === product.id)
    if (existingItem) {
      setCart(cart.map(item =>
        item.id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ))
    } else {
      setCart([...cart, { ...product, quantity: 1 }])
    }
  }

  const removeFromCart = (productId) => {
    setCart(cart.filter(item => item.id !== productId))
  }

  const updateQuantity = (productId, change) => {
    setCart(cart.map(item => {
      if (item.id === productId) {
        const newQuantity = item.quantity + change
        if (newQuantity <= 0) return null
        return { ...item, quantity: newQuantity }
      }
      return item
    }).filter(Boolean))
  }

  const cartTotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0)

  const handleCheckout = () => {
    if (cart.length === 0) return
    alert(`Checkout initiated! Total: $${cartTotal.toLocaleString()}\n\nThis will be processed through the closed-loop payment system.`)
    setCart([])
    setIsCartOpen(false)
  }

  const openProductModal = (product) => {
    setSelectedProduct(product)
    setIsProductModalOpen(true)
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Marketplace</h1>
            <p className="text-gray-600">Browse vetted educational resources and services</p>
          </div>
          <button
            onClick={() => setIsCartOpen(true)}
            className="relative flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            <ShoppingBagIcon className="w-5 h-5" />
            Cart
            {cartCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>

        {/* Search and Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4 mb-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search products, services, or suppliers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Category Filters */}
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => {
              const Icon = category.icon
              return (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    selectedCategory === category.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{category.name}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
            <div
              key={product.id}
              className={`rounded-xl bg-white shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow ${
                product.featured ? 'ring-2 ring-blue-500' : ''
              }`}
            >
              {product.featured && (
                <div className="flex items-center gap-1 mb-2 text-blue-600 text-xs font-medium">
                  <StarIcon className="w-4 h-4 fill-current" />
                  <span>Featured</span>
                </div>
              )}
              
              <div className="text-4xl mb-4">{product.image}</div>
              
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
                  {product.rating} ({product.reviews} reviews)
                </span>
              </div>

              <div className="flex items-center gap-2 mb-3 text-sm text-gray-500">
                <BuildingStorefrontIcon className="w-4 h-4" />
                <span>{product.supplier}</span>
              </div>

              <p className="text-sm text-gray-600 mb-4 line-clamp-2">{product.description}</p>

              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-2xl font-bold text-gray-900">${product.price.toLocaleString()}</p>
                  <p className="text-xs text-gray-500">{product.duration}</p>
                </div>
                <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                  {product.category}
                </span>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => openProductModal(product)}
                  className="flex-1 px-4 py-2 text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  View Details
                </button>
                <button
                  onClick={() => addToCart(product)}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Add to Cart
                </button>
              </div>
            </div>
          ))}
        </div>

        {filteredProducts.length === 0 && (
          <div className="text-center py-12 rounded-xl bg-white shadow-sm border border-gray-200">
            <ShoppingBagIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No products found matching your criteria</p>
          </div>
        )}

        {/* Shopping Cart Sidebar */}
        {isCartOpen && (
          <div className="fixed inset-0 z-50 overflow-hidden">
            <div
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={() => setIsCartOpen(false)}
            ></div>
            <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-xl">
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                  <h2 className="text-xl font-bold text-gray-900">Shopping Cart</h2>
                  <button
                    onClick={() => setIsCartOpen(false)}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                  {cart.length === 0 ? (
                    <div className="text-center py-12">
                      <ShoppingBagIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-500">Your cart is empty</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {cart.map((item) => (
                        <div key={item.id} className="flex gap-4 p-4 border border-gray-200 rounded-lg">
                          <div className="text-3xl">{item.image}</div>
                          <div className="flex-1">
                            <h3 className="font-medium text-gray-900 mb-1">{item.name}</h3>
                            <p className="text-sm text-gray-500 mb-2">{item.supplier}</p>
                            <div className="flex items-center justify-between">
                              <p className="font-bold text-gray-900">${item.price.toLocaleString()}</p>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => updateQuantity(item.id, -1)}
                                  className="p-1 text-gray-600 hover:text-gray-900"
                                >
                                  <MinusIcon className="w-4 h-4" />
                                </button>
                                <span className="w-8 text-center text-sm font-medium">{item.quantity}</span>
                                <button
                                  onClick={() => updateQuantity(item.id, 1)}
                                  className="p-1 text-gray-600 hover:text-gray-900"
                                >
                                  <PlusIcon className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                            <button
                              onClick={() => removeFromCart(item.id)}
                              className="mt-2 text-sm text-red-600 hover:text-red-700"
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {cart.length > 0 && (
                  <div className="border-t border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-lg font-bold text-gray-900">Total</span>
                      <span className="text-2xl font-bold text-gray-900">
                        ${cartTotal.toLocaleString()}
                      </span>
                    </div>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                      <p className="text-xs text-blue-800">
                        <strong>Closed-Loop Payment:</strong> Funds will be routed directly to suppliers through the platform. Complete transparency guaranteed.
                      </p>
                    </div>
                    <button
                      onClick={handleCheckout}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium"
                    >
                      Proceed to Checkout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Product Detail Modal */}
        {isProductModalOpen && selectedProduct && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={() => setIsProductModalOpen(false)}
            ></div>
            <div className="flex min-h-full items-center justify-center p-4">
              <div
                className="relative w-full max-w-2xl rounded-xl bg-white shadow-lg border border-gray-200"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6">
                  <button
                    onClick={() => setIsProductModalOpen(false)}
                    className="absolute top-4 right-4 text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>

                  <div className="flex items-start gap-6 mb-6">
                    <div className="text-6xl">{selectedProduct.image}</div>
                    <div className="flex-1">
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">{selectedProduct.name}</h2>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex items-center">
                          {[...Array(5)].map((_, i) => (
                            <StarIcon
                              key={i}
                              className={`w-5 h-5 ${
                                i < Math.floor(selectedProduct.rating)
                                  ? 'text-yellow-400 fill-current'
                                  : 'text-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-sm text-gray-600">
                          {selectedProduct.rating} ({selectedProduct.reviews} reviews)
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                        <BuildingStorefrontIcon className="w-4 h-4" />
                        <span>{selectedProduct.supplier}</span>
                      </div>
                      <p className="text-3xl font-bold text-gray-900 mb-2">
                        ${selectedProduct.price.toLocaleString()}
                      </p>
                      <span className="text-sm px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        {selectedProduct.category}
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-gray-200 pt-6 mb-6">
                    <h3 className="font-bold text-gray-900 mb-2">Description</h3>
                    <p className="text-gray-600 mb-4">{selectedProduct.description}</p>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-500">Duration</p>
                        <p className="font-medium text-gray-900">{selectedProduct.duration}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Level</p>
                        <p className="font-medium text-gray-900">{selectedProduct.level}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Students Enrolled</p>
                        <p className="font-medium text-gray-900">{selectedProduct.students.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <div className="flex items-start gap-2">
                      <CheckCircleIcon className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-blue-900 mb-1">Vetted Supplier</p>
                        <p className="text-xs text-blue-800">
                          This supplier has been verified and approved by ZenK. All transactions are tracked through our closed-loop payment system for complete transparency.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        addToCart(selectedProduct)
                        setIsProductModalOpen(false)
                      }}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium"
                    >
                      Add to Cart
                    </button>
                    <button
                      onClick={() => setIsProductModalOpen(false)}
                      className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Marketplace
