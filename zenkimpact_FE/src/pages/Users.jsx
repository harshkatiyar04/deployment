import { useState } from 'react'
import Layout from '../components/Layout'
import {
  UsersIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  UserPlusIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon
} from '@heroicons/react/24/outline'

function Users() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterRole, setFilterRole] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  // Mock user data
  const users = [
    {
      id: 1,
      name: 'John Doe',
      email: 'john.doe@example.com',
      role: 'Student',
      subtype: 'University Student',
      status: 'active',
      joinedDate: '2024-01-15',
      lastActive: '2 hours ago',
      circle: 'The Navigators'
    },
    {
      id: 2,
      name: 'Jane Smith',
      email: 'jane.smith@corp.com',
      role: 'Sponsor',
      subtype: 'Corporate Sponsor',
      status: 'active',
      joinedDate: '2023-11-20',
      lastActive: '1 day ago',
      circle: 'Tech Leaders Circle'
    },
    {
      id: 3,
      name: 'ABC Tutoring',
      email: 'contact@abctutoring.com',
      role: 'Supplier',
      subtype: 'Educational Service Provider',
      status: 'pending',
      joinedDate: '2024-02-01',
      lastActive: 'Never',
      circle: '-'
    },
    {
      id: 4,
      name: 'Sarah Johnson',
      email: 'sarah.j@example.com',
      role: 'Student',
      subtype: 'Secondary School Student',
      status: 'active',
      joinedDate: '2024-01-10',
      lastActive: '5 hours ago',
      circle: 'Future Leaders'
    },
    {
      id: 5,
      name: 'Michael Brown',
      email: 'm.brown@ngo.org',
      role: 'Sponsor',
      subtype: 'NGO Partner',
      status: 'active',
      joinedDate: '2023-09-05',
      lastActive: '3 days ago',
      circle: 'Community Impact'
    },
    {
      id: 6,
      name: 'XYZ Supplies',
      email: 'info@xyzsupplies.com',
      role: 'Supplier',
      subtype: 'Product Supplier',
      status: 'suspended',
      joinedDate: '2023-12-15',
      lastActive: '1 week ago',
      circle: '-'
    }
  ]

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRole = filterRole === 'all' || user.role.toLowerCase() === filterRole
    const matchesStatus = filterStatus === 'all' || user.status === filterStatus
    return matchesSearch && matchesRole && matchesStatus
  })

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      suspended: 'bg-red-100 text-red-700',
      inactive: 'bg-gray-100 text-gray-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status] || styles.inactive}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getRoleBadge = (role) => {
    const styles = {
      Student: 'bg-blue-100 text-blue-700',
      Sponsor: 'bg-purple-100 text-purple-700',
      Supplier: 'bg-orange-100 text-orange-700',
      Admin: 'bg-gray-100 text-gray-700'
    }
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[role] || styles.Admin}`}>
        {role}
      </span>
    )
  }

  return (
    <Layout>
      <div>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">User Management</h1>
            <p className="text-gray-600">Manage all platform users</p>
          </div>
          <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            <UserPlusIcon className="w-5 h-5" />
            Add User
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Users</p>
            <p className="text-2xl font-bold text-gray-900">{users.length}</p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Active Users</p>
            <p className="text-2xl font-bold text-green-600">
              {users.filter(u => u.status === 'active').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Pending Approval</p>
            <p className="text-2xl font-bold text-yellow-600">
              {users.filter(u => u.status === 'pending').length}
            </p>
          </div>
          <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Suspended</p>
            <p className="text-2xl font-bold text-red-600">
              {users.filter(u => u.status === 'suspended').length}
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
                placeholder="Search by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Roles</option>
                <option value="student">Student</option>
                <option value="sponsor">Sponsor</option>
                <option value="supplier">Supplier</option>
                <option value="admin">Admin</option>
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
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Circle
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Active
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                          <UsersIcon className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{user.name}</p>
                          <p className="text-xs text-gray-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        {getRoleBadge(user.role)}
                        <p className="text-xs text-gray-500 mt-1">{user.subtype}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(user.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.circle}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.lastActive}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button className="text-blue-600 hover:text-blue-700" title="View">
                          <EyeIcon className="w-5 h-5" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-700" title="Edit">
                          <PencilIcon className="w-5 h-5" />
                        </button>
                        {user.status === 'pending' && (
                          <button className="text-green-600 hover:text-green-700" title="Approve">
                            <CheckCircleIcon className="w-5 h-5" />
                          </button>
                        )}
                        {user.status === 'active' && (
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
          {filteredUsers.length === 0 && (
            <div className="text-center py-12">
              <UsersIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No users found matching your criteria</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

export default Users
