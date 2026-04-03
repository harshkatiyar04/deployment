/**
 * SOSQueue — Admin dashboard interface for reviewing and resolving SOS reports.
 */
import { useEffect, useState } from 'react'
import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function SOSQueue() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchReports = async () => {
    const token = localStorage.getItem('chat_token')
    if (!token) {
      setError('No auth token found. Please log in as admin.')
      setLoading(false)
      return
    }

    try {
      const res = await fetch(`${API_BASE}/chat/sos-reports?token=${encodeURIComponent(token)}`)
      if (!res.ok) throw new Error('Failed to fetch SOS reports')
      const data = await res.json()
      setReports(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const resolveReport = async (reportId) => {
    const token = localStorage.getItem('chat_token')
    try {
      const res = await fetch(
        `${API_BASE}/chat/sos-reports/${reportId}/resolve?token=${encodeURIComponent(token)}`,
        { method: 'PATCH' }
      )
      if (!res.ok) throw new Error('Failed to resolve')
      
      // Optimitic update UI
      setReports((prev) => prev.filter((r) => r.id !== reportId))
    } catch (err) {
      alert(err.message)
    }
  }

  const handleBan = async (report) => {
    const reason = window.prompt(`Enter ban reason for user ${report.sender_nickname}:`, "Policy violation via SOS report")
    if (!reason) return

    const token = localStorage.getItem('chat_token')
    try {
      const res = await fetch(`${API_BASE}/admin/chat/bans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          circle_id: report.circle_id,
          user_id: report.sender_user_id,
          reason: reason,
          reported_message_content: report.message_content
        }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Ban failed')
      }

      alert(`User ${report.sender_nickname} has been banned.`)
      
      // Auto-resolve the report after banning
      await resolveReport(report.id)
    } catch (err) {
      alert(`Error banning user: ${err.message}`)
    }
  }

  if (loading) return <div className="p-8 text-gray-500">Loading SOS Queue...</div>
  if (error) return <div className="p-8 text-red-500">{error}</div>

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-8">
        <ExclamationTriangleIcon className="w-8 h-8 text-red-600" />
        <h1 className="text-2xl font-bold text-gray-900">SOS Review Queue</h1>
        <span className="ml-auto bg-red-100 text-red-800 text-sm font-semibold px-3 py-1 rounded-full">
          {reports.length} pending
        </span>
      </div>

      {reports.length === 0 ? (
        <div className="bg-green-50 rounded-xl p-12 text-center border border-green-100">
          <CheckCircleIcon className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-green-900">All caught up!</h3>
          <p className="text-green-700 mt-1">There are no pending SOS reports to review.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <ul className="divide-y divide-gray-200">
            {reports.map((report) => (
              <li key={report.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        Reported {new Date(report.created_at).toLocaleString()}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">
                        Sender: <span className="font-bold text-gray-900">{report.sender_nickname}</span>
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">
                        Reporter: <span className="font-mono">{report.reporter_persona_id}</span>
                      </span>
                    </div>
                    
                    <div className="bg-gray-100 border-l-4 border-red-400 p-4 rounded-r-md mt-3 mb-4">
                      <p className="text-sm font-medium text-gray-900 mb-1">Reported Message Content:</p>
                      <p className="text-sm text-gray-700 italic break-words whitespace-pre-wrap">
                        "{report.message_content}"
                      </p>
                    </div>
                  </div>

                  <div className="shrink-0 flex flex-col gap-2">
                    <button
                      onClick={() => resolveReport(report.id)}
                      className="bg-red-50 text-red-700 hover:bg-red-100 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-red-200 shadow-sm"
                    >
                      Mark Resolved
                    </button>
                    <button
                      onClick={() => handleBan(report)}
                      className="bg-white border text-red-600 border-red-100 hover:bg-red-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
                    >
                      Ban User
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
