import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const NotificationContext = createContext()

export const useNotifications = () => {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return context
}

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isAdminLoggedIn = () => {
    return localStorage.getItem('isAdmin') === 'true'
  }

  const fetchNotifications = useCallback(async () => {
    if (!isAdminLoggedIn()) {
      return
    }

    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/notifications/admin`)
      setNotifications(response.data.notifications || [])
      setUnreadCount(response.data.unread_count || 0)
    } catch (err) {
      console.error('Error fetching notifications:', err)
      setError(err.message)
      setNotifications([])
      setUnreadCount(0)
    } finally {
      setLoading(false)
    }
  }, [])

  const markAsRead = async (notificationId) => {
    try {
      // Update local state optimistically
      setNotifications(prev =>
        prev.map(notif =>
          notif.id === notificationId
            ? { ...notif, is_read: true, read_at: new Date().toISOString() }
            : notif
        )
      )
      setUnreadCount(prev => Math.max(0, prev - 1))

      // Optionally call API to mark as read
      // await axios.patch(`${API_BASE_URL}/notifications/${notificationId}/read`)
    } catch (err) {
      console.error('Error marking notification as read:', err)
      // Revert on error
      fetchNotifications()
    }
  }

  const approveKYC = async (notificationId, signupId, note = 'All documents verified. Approved.') => {
    try {
      // Call API to approve KYC
      await axios.post(
        `${API_BASE_URL}/admin/kyc/${signupId}/decision`,
        {
          decision: 'approved',
          note: note
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )

      // Remove notification from list after approval
      setNotifications(prev => prev.filter(notif => notif.id !== notificationId))
      setUnreadCount(prev => Math.max(0, prev - 1))

      // Refresh notifications
      await fetchNotifications()
    } catch (err) {
      console.error('Error approving KYC:', err)
      throw err
    }
  }

  // Fetch notifications only when admin is logged in (no polling)
  useEffect(() => {
    const handleFetch = () => {
      if (isAdminLoggedIn()) {
        fetchNotifications()
      } else {
        // Clear notifications when admin logs out
        setNotifications([])
        setUnreadCount(0)
      }
    }

    // Initial check - only fetch if admin is logged in
    if (isAdminLoggedIn()) {
      fetchNotifications()
    }

    // Listen for storage changes (when admin logs in/out from another tab)
    const handleStorageChange = (e) => {
      if (e.key === 'isAdmin') {
        handleFetch()
      }
    }

    // Listen for custom event (same-tab login/logout)
    const handleAdminLogin = () => {
      handleFetch()
    }

    const handleAdminLogout = () => {
      setNotifications([])
      setUnreadCount(0)
    }

    window.addEventListener('storage', handleStorageChange)
    window.addEventListener('adminLogin', handleAdminLogin)
    window.addEventListener('adminLogout', handleAdminLogout)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('adminLogin', handleAdminLogin)
      window.removeEventListener('adminLogout', handleAdminLogout)
    }
  }, [fetchNotifications])

  const value = {
    notifications,
    unreadCount,
    loading,
    error,
    fetchNotifications,
    markAsRead,
    approveKYC
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}


