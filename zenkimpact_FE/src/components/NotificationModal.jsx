import { useState, useEffect } from 'react'
import { XMarkIcon, CheckCircleIcon, DocumentTextIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { useNotifications } from '../contexts/NotificationContext'
import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000'

function NotificationModal({ isOpen, onClose }) {
  const { notifications, approveKYC, markAsRead, fetchNotifications, loading } = useNotifications()
  const [selectedNotification, setSelectedNotification] = useState(null)
  const [kycDocument, setKycDocument] = useState(null)
  const [loadingDocument, setLoadingDocument] = useState(false)
  const [approving, setApproving] = useState(false)
  const [approvalNote, setApprovalNote] = useState('')

  useEffect(() => {
    if (isOpen && notifications.length > 0 && !selectedNotification) {
      // Auto-select first notification
      setSelectedNotification(notifications[0])
    }
  }, [isOpen, notifications])

  useEffect(() => {
    if (selectedNotification) {
      loadKycDocument(selectedNotification.related_entity_id)
      // Mark as read when selected
      if (!selectedNotification.is_read) {
        markAsRead(selectedNotification.id)
      }
      // Reset approval note when notification changes
      setApprovalNote('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNotification])

  const loadKycDocument = async (signupId) => {
    setLoadingDocument(true)
    setKycDocument(null)
    try {
      // Fetch KYC documents for the signup
      const response = await axios.get(`${API_BASE_URL}/admin/kyc/${signupId}/documents/view`)
      // Response should be an array of documents
      const documents = Array.isArray(response.data) ? response.data : [response.data]
      setKycDocument({ documents })
    } catch (err) {
      console.error('Error loading KYC document:', err)
      // If API doesn't exist, show placeholder
      setKycDocument({ error: 'Document not available' })
    } finally {
      setLoadingDocument(false)
    }
  }

  const isImageType = (contentType) => {
    return contentType?.startsWith('image/')
  }

  const isPdfType = (contentType) => {
    return contentType === 'application/pdf'
  }

  const getDocumentUrl = (previewUrl) => {
    // If preview_url is already a full URL, use it; otherwise prepend API_BASE_URL
    if (previewUrl?.startsWith('http')) {
      return previewUrl
    }
    return `${API_BASE_URL}${previewUrl}`
  }

  const handleApprove = async () => {
    if (!selectedNotification) return

    setApproving(true)
    try {
      await approveKYC(selectedNotification.id, selectedNotification.related_entity_id, approvalNote || 'All documents verified. Approved.')
      // Remove from selected if approved
      const remainingNotifications = notifications.filter(
        n => n.id !== selectedNotification.id
      )
      if (remainingNotifications.length > 0) {
        setSelectedNotification(remainingNotifications[0])
      } else {
        setSelectedNotification(null)
        onClose()
      }
      // Clear approval note
      setApprovalNote('')
    } catch (err) {
      alert('Error approving KYC: ' + (err.response?.data?.detail || err.message))
    } finally {
      setApproving(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatNotificationType = (type) => {
    if (!type) return ''
    // Replace underscores and hyphens with spaces, then convert to uppercase
    return type.replace(/[_-]/g, ' ').toUpperCase()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Notifications</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchNotifications}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh notifications"
            >
              <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Two-pane layout */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Pane - Notification List */}
          <div className="w-80 border-r border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-sm font-medium text-gray-700">All Notifications</h3>
            </div>
            <div className="flex-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-sm text-gray-500">No notifications</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {notifications.map((notification) => (
                    <button
                      key={notification.id}
                      onClick={() => setSelectedNotification(notification)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                        selectedNotification?.id === notification.id
                          ? 'bg-blue-50 border-l-4 border-blue-600'
                          : ''
                      } ${!notification.is_read ? 'bg-gray-50' : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-red-600 mb-1">
                            {formatNotificationType(notification.notification_type)}
                          </p>
                          <p className="text-sm font-semibold text-gray-900 line-clamp-2">
                            {notification.title}
                          </p>
                          {!notification.is_read && (
                            <span className="inline-block mt-2 w-2 h-2 bg-blue-600 rounded-full"></span>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Pane - Preview */}
          <div className="flex-1 flex flex-col bg-gray-50">
            {selectedNotification ? (
              <>
                {/* Preview Header */}
                <div className="p-4 border-b border-gray-200 bg-white">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-base font-semibold text-gray-900">
                      {selectedNotification.title}
                    </h3>
                    <span className="text-gray-400">|</span>
                    <span className="text-xs font-medium text-red-600">
                      {formatNotificationType(selectedNotification.notification_type)}
                    </span>
                    <span className="text-gray-400">|</span>
                    <span className="text-xs text-gray-500">
                      {formatDate(selectedNotification.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">
                    {selectedNotification.message}
                  </p>
                </div>

                {/* Document Preview Area */}
                <div className="flex-1 overflow-y-auto p-6">
                  {loadingDocument ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p className="text-sm text-gray-500">Loading document...</p>
                      </div>
                    </div>
                  ) : kycDocument?.error ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <DocumentTextIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-sm text-gray-500">{kycDocument.error}</p>
                        <p className="text-xs text-gray-400 mt-2">
                          Document preview will be available here
                        </p>
                      </div>
                    </div>
                  ) : kycDocument?.documents && kycDocument.documents.length > 0 ? (
                    <div className="space-y-4">
                      {kycDocument.documents.map((doc, index) => (
                        <div key={doc.id || index} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                          <div className="mb-4">
                            <h4 className="text-sm font-semibold text-gray-900 mb-1">
                              {doc.original_filename || `Document ${index + 1}`}
                            </h4>
                            <p className="text-xs text-gray-500">
                              {doc.content_type} • {doc.created_at ? formatDate(doc.created_at) : ''}
                            </p>
                          </div>
                          
                          {/* Render based on content type */}
                          {isImageType(doc.content_type) ? (
                            <div className="flex justify-center">
                              <img
                                src={getDocumentUrl(doc.preview_url)}
                                alt={doc.original_filename || 'KYC Document'}
                                className="max-w-full h-auto rounded-lg border border-gray-200"
                                style={{ maxHeight: '600px' }}
                              />
                            </div>
                          ) : isPdfType(doc.content_type) ? (
                            <iframe
                              src={getDocumentUrl(doc.preview_url)}
                              width="100%"
                              height="600px"
                              className="border border-gray-200 rounded-lg"
                              title={doc.original_filename || 'KYC Document Preview'}
                            />
                          ) : (
                            <div className="flex items-center justify-center h-64 border border-gray-200 rounded-lg bg-gray-50">
                              <div className="text-center">
                                <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                                <p className="text-sm text-gray-500 mb-2">{doc.original_filename}</p>
                                <a
                                  href={getDocumentUrl(doc.preview_url)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-600 hover:underline"
                                >
                                  Open Document
                                </a>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <DocumentTextIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-sm text-gray-500">No document available</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Footer */}
                <div className="p-4 border-t border-gray-200 bg-white">
                  <div className="flex items-center gap-2">
                    <textarea
                      value={approvalNote}
                      onChange={(e) => setApprovalNote(e.target.value)}
                      placeholder="Enter approval note..."
                      className="flex-1 min-h-[80px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                      rows={3}
                    />
                    <button
                      onClick={handleApprove}
                      disabled={approving}
                      className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap self-center"
                    >
                      {approving ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Approving...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircleIcon className="w-4 h-4" />
                          <span>Approve</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <DocumentTextIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-sm text-gray-500">Select a notification to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotificationModal

