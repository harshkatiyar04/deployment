import { useState } from 'react'
import Layout from '../components/Layout'
import {
  BuildingStorefrontIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  CheckCircleIcon,
  XCircleIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  ShoppingBagIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline'

function Suppliers() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterType, setFilterType] = useState('all')

  // Mock supplier data
  const suppliers = [
    {
      id: 1,
      name: 'ABC Tutoring Services',
      email: 'contact@abctutoring.com',
      type: 'Educational Service Provider',
      status: 'active',
      products: 15,
      orders: 234,
      revenue: 45600,
      rating: 4.8,
      joinedDate: '2023-10-15',
      contact: 'John Smith'
    },
    {
      id: 2,
      name: 'XYZ Supplies Co.',
      email: 'info@xyzsupplies.com',
      type: 'Product Supplier',
      status: 'suspended',
      products: 8,
      orders: 89,
      revenue: 12300,
      rating: 3.2,
      joinedDate: '2023-11-20',
      contact: 'Jane Doe'
    },
    {
      id: 3,
      name: 'EduTech Solutions',
      email: 'hello@edutech.com',
      type: 'Educational Service Provider',
      status: 'active',
      products: 22,
      orders: 456,
      revenue: 89200,
      rating: 4.9,
      joinedDate: '2023-09-05',
      contact: 'Mike Johnson'
    },
    {
      id: 4,
      name: 'Learning Materials Inc.',
      email: 'sales@learningmaterials.com',
      type: 'Product Supplier',
      status: 'pending',
      products: 0,
      orders: 0,
      revenue: 0,
      rating: 0,
      joinedDate: '2024-02-01',
      contact: 'Sarah Williams'
    },
    {
      id: 5,
      name: 'Online Academy Pro',
      email: 'support@onlineacademy.com',
      type: 'Educational Service Provider',
      status: 'active',
      products: 18,
      orders: 312,
      revenue: 67800,
      rating: 4.6,
      joinedDate: '2023-12-10',
      contact: 'David Brown'
    }
  ]

  const filteredSuppliers = suppliers.filter(supplier => {
    const matchesSearch = supplier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         supplier.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'all' || supplier.status === filterStatus
    const matchesType = filterType === 'all' || 
                       (filterType === 'service' && supplier.type === 'Educational Service Provider') ||
                       (filterType === 'product' && supplier.type === 'Product Supplier')
    return matchesSearch && matchesStatus && matchesType
  })

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      suspended: 'bg-red-100 text-red-700'
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
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Supplier Management</h1>
            <p className="text-gray-600">Manage marketplace suppliers</p>
          </div>
          <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            <PlusIcon className="w-5 h-5" />
            Add Supplier
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Suppliers</p>
            <p className="text-2xl font-bold text-gray-900">{suppliers.length}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Active Suppliers</p>
            <p className="text-2xl font-bold text-green-600">
              {suppliers.filter(s => s.status === 'active').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Pending Approval</p>
            <p className="text-2xl font-bold text-yellow-600">
              {suppliers.filter(s => s.status === 'pending').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Revenue</p>
            <p className="text-2xl font-bold text-blue-600">
              ${suppliers.reduce((sum, s) => sum + s.revenue, 0).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search suppliers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value="service">Service Provider</option>
                <option value="product">Product Supplier</option>
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>
        </div>

        {/* Suppliers Table */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Supplier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Products
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Orders
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Revenue
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rating
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredSuppliers.map((supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                          <BuildingStorefrontIcon className="w-5 h-5 text-orange-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{supplier.name}</p>
                          <p className="text-xs text-gray-500">{supplier.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">{supplier.type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(supplier.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <ShoppingBagIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900">{supplier.products}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {supplier.orders}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      ${supplier.revenue.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {supplier.rating > 0 ? (
                        <div className="flex items-center gap-1">
                          <span className="text-sm font-medium text-gray-900">{supplier.rating}</span>
                          <span className="text-yellow-400">★</span>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button className="text-blue-600 hover:text-blue-700" title="View">
                          <EyeIcon className="w-5 h-5" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-700" title="Edit">
                          <PencilIcon className="w-5 h-5" />
                        </button>
                        {supplier.status === 'pending' && (
                          <button className="text-green-600 hover:text-green-700" title="Approve">
                            <CheckCircleIcon className="w-5 h-5" />
                          </button>
                        )}
                        {supplier.status === 'active' && (
                          <button className="text-red-600 hover:text-red-700" title="Suspend">
                            <XCircleIcon className="w-5 h-5" />
                          </button>
                        )}
                        <button className="text-red-600 hover:text-red-700" title="Delete">
                          <TrashIcon className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredSuppliers.length === 0 && (
            <div className="text-center py-12">
              <BuildingStorefrontIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No suppliers found matching your criteria</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

export default Suppliers
