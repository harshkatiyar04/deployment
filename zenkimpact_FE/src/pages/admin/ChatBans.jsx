import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { ShieldExclamationIcon, TrashIcon, UserMinusIcon, ExclamationTriangleIcon, CheckCircleIcon, ClipboardDocumentListIcon, Squares2X2Icon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import Layout from '../../components/Layout'
import PersonaAvatar from '../../components/chat/PersonaAvatar'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const TABS = [
  { key: 'all', label: 'All Data', icon: Squares2X2Icon },
  { key: 'reports', label: 'Reports', icon: ExclamationTriangleIcon },
  { key: 'ai', label: 'System Flagged', icon: ShieldExclamationIcon },
  { key: 'ban', label: 'Issue Ban', icon: UserMinusIcon },
  { key: 'auth', label: 'Auth Logs', icon: ShieldCheckIcon },
  { key: 'history', label: 'Ban History', icon: TrashIcon },
  { key: 'audit', label: 'Audit Trail', icon: ClipboardDocumentListIcon },
]

/* ── Inline styles for tab buttons (organic, not Tailwind-heavy) ────── */
const tabBtnStyle = (isActive) => ({
  fontFamily: 'inherit',
  fontSize: '14px',
  background: isActive ? '#0d9488' : '#f1f3f5',
  color: isActive ? '#fff' : '#495057',
  padding: '0.55em 1.1em',
  paddingLeft: '0.8em',
  display: 'flex',
  alignItems: 'center',
  gap: '0.5em',
  border: 'none',
  borderRadius: '14px',
  overflow: 'hidden',
  transition: 'all 0.2s',
  cursor: 'pointer',
  fontWeight: 600,
  boxShadow: isActive ? '0 4px 14px rgba(13, 148, 136, 0.3)' : 'none',
})

export default function ChatBans() {
  const [activeTab, setActiveTab] = useState('all')
  const [bans, setBans] = useState([])
  const [reports, setReports] = useState([])
  const [warned, setWarned] = useState([])
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [authLogs, setAuthLogs] = useState([])

  const [circleId, setCircleId] = useState('')
  const [userId, setUserId] = useState('')
  const [reason, setReason] = useState('')
  const [submitError, setSubmitError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isUuid = (str) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str)
  const isEmail = (str) => str.includes('@')
  const token = localStorage.getItem('chat_token')

  /* ── Fetchers ────────────────────────────────────────────────────────── */
  const fetchBans = useCallback(async () => {
    try { const res = await axios.get(`${API_BASE}/admin/chat/bans`, { headers: { Authorization: `Bearer ${token}` } }); setBans(res.data.bans) }
    catch (err) { setError('Failed to load bans. ' + (err.response?.data?.detail || err.message)) }
  }, [token])

  const fetchReports = useCallback(async () => {
    try { const res = await axios.get(`${API_BASE}/chat/sos-reports?token=${encodeURIComponent(token)}`); setReports(res.data) }
    catch (err) { console.error('Failed to load reports', err) }
  }, [token])

  const fetchActivity = useCallback(async () => {
    try { const res = await axios.get(`${API_BASE}/admin/chat/activity`, { headers: { Authorization: `Bearer ${token}` } }); setActivity(res.data) }
    catch (err) { console.error('Failed to load activity log', err) }
  }, [token])

  const fetchWarned = useCallback(async () => {
    try { const res = await axios.get(`${API_BASE}/admin/chat/warned-messages`, { headers: { Authorization: `Bearer ${token}` } }); setWarned(res.data) }
    catch (err) { console.error('Failed to load warned messages', err) }
  }, [token])

  const fetchAuthLogs = useCallback(async () => {
    try { const res = await axios.get(`${API_BASE}/admin/chat/auth-logs`, { headers: { Authorization: `Bearer ${token}` } }); setAuthLogs(res.data) }
    catch (err) { console.error('Failed to load auth logs', err) }
  }, [token])

  const fetchData = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchBans(), fetchReports(), fetchActivity(), fetchWarned(), fetchAuthLogs()])
    setLoading(false)
  }, [fetchBans, fetchReports, fetchActivity, fetchWarned, fetchAuthLogs])

  useEffect(() => { if (token) fetchData(); else setLoading(false) }, [token, fetchData])

  /* ── Actions ─────────────────────────────────────────────────────────── */
  const handleBan = async (e) => {
    e.preventDefault(); setSubmitError(null)
    if (!isUuid(circleId)) { setSubmitError('Invalid Circle ID. Must be a valid UUID.'); return }
    if (!isUuid(userId) && !isEmail(userId)) { setSubmitError('Invalid User ID. Must be UUID or Email.'); return }
    setIsSubmitting(true)
    try {
      await axios.post(`${API_BASE}/admin/chat/bans`, { circle_id: circleId, user_identifier: userId, reason }, { headers: { Authorization: `Bearer ${token}` } })
      setCircleId(''); setUserId(''); setReason(''); fetchBans()
    } catch (err) { setSubmitError(err.response?.data?.detail || err.message) }
    finally { setIsSubmitting(false) }
  }

  const handleRevoke = async (banId) => {
    if (!window.confirm('Revoke this ban?')) return
    try { await axios.delete(`${API_BASE}/admin/chat/bans/${banId}`, { headers: { Authorization: `Bearer ${token}` } }); fetchBans() }
    catch (err) { alert('Failed: ' + err.message) }
  }

  const resolveReport = async (reportId) => {
    try {
      const res = await fetch(`${API_BASE}/chat/sos-reports/${reportId}/resolve?token=${encodeURIComponent(token)}`, { method: 'PATCH' })
      if (!res.ok) throw new Error('Failed to resolve')
      setReports(prev => prev.filter(r => r.id !== reportId))
    } catch (err) { alert(err.message) }
  }

  const handleReportBan = async (report) => {
    const banReason = window.prompt(`Ban reason for ${report.sender_nickname || report.persona_nickname}:`, "Policy violation")
    if (!banReason) return
    try {
      await axios.post(`${API_BASE}/admin/chat/bans`, {
        circle_id: report.circle_id, user_identifier: report.sender_user_id, reason: banReason,
        reported_message_content: report.message_content || report.content_text
      }, { headers: { Authorization: `Bearer ${token}` } })
      alert(`User banned successfully.`)
      if (report.hasOwnProperty('reporter_persona_id')) await resolveReport(report.id)
      fetchBans()
    } catch (err) { alert(`Error: ${err.message}`) }
  }

  /* ── Guards ──────────────────────────────────────────────────────────── */
  if (loading) return <div className="p-12 text-center text-gray-500 animate-pulse">Loading moderation dashboard...</div>
  if (!token) return (
    <div className="p-10 text-center max-w-2xl mx-auto mt-20 bg-white rounded-2xl shadow-xl border border-gray-100">
      <ShieldExclamationIcon className="w-16 h-16 text-red-500 mx-auto mb-4" />
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Moderation Token Required</h2>
      <p className="text-gray-600 mb-8">Please log in via Chat Demo to authenticate.</p>
      <a href="/chat-demo" className="bg-[#00d084] text-white px-6 py-3 rounded-xl font-bold hover:bg-[#01a76c] transition-all">Go to Chat Demo</a>
    </div>
  )

  /* ── Tab badge counts ────────────────────────────────────────────────── */
  const badges = { reports: reports.length, ai: warned.length, ban: null, auth: authLogs.filter(l => l.status !== 'SUCCESS').length, history: bans.length, audit: activity.length }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto pb-12">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div style={{
          background: 'linear-gradient(135deg, #00d084 0%, #01a76c 100%)',
          borderRadius: '16px',
          padding: '20px 20px',
          marginBottom: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldExclamationIcon style={{ width: 28, height: 28, color: '#ccfbf1' }} />
              Safety & Content Moderation
            </h1>
            <p style={{ color: '#ccfbf1', marginTop: '6px', fontSize: '13px' }}>Central hub for reviewing reports and managing chat access.</p>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(8px)',
            padding: '8px 16px', borderRadius: '12px', fontSize: '13px',
            fontWeight: 600, color: '#bbf7d0', alignSelf: 'flex-start',
          }}>
            <div style={{ width: 8, height: 8, background: '#4ade80', borderRadius: '50%' }} />
            AI Shield Active
          </div>
        </div>

        {/* ── Tab Bar ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '28px', overflowX: 'auto', WebkitOverflowScrolling: 'touch', paddingBottom: '4px' }}>
          {TABS.map(tab => {
            const isActive = activeTab === tab.key
            const count = badges[tab.key]
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={tabBtnStyle(isActive)}
                onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#dee2e6'; e.currentTarget.style.transform = 'scale(1.03)' } }}
                onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = '#f1f3f5'; e.currentTarget.style.transform = 'scale(1)' } }}
                onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.95)' }}
                onMouseUp={e => { e.currentTarget.style.transform = 'scale(1)' }}
              >
                <tab.icon style={{ width: 18, height: 18, flexShrink: 0 }} />
                <span style={{ whiteSpace: 'nowrap' }}>{tab.label}</span>
                {count > 0 && (
                  <span style={{
                    fontSize: '11px', fontWeight: 700, padding: '1px 7px',
                    borderRadius: '8px', marginLeft: '2px',
                    background: isActive ? 'rgba(255,255,255,0.25)' : '#e9ecef',
                    color: isActive ? '#fff' : '#495057',
                  }}>{count}</span>
                )}
              </button>
            )
          })}
        </div>

        {/* ── Panel Content ───────────────────────────────────────────── */}
        <div style={{ background: '#fff', border: '1px solid #e9ecef', borderRadius: '16px', minHeight: 400 }}>

          {/* ── REPORTS ────────────────────────────────────────────────── */}
          {(activeTab === 'reports' || activeTab === 'all') && (
            <div style={{ borderBottom: activeTab === 'all' ? '12px solid #f8f9fa' : 'none' }}>
              {activeTab === 'all' && (
                <div style={{ padding: '24px 24px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: 700, color: '#0f766e' }}>
                  <ExclamationTriangleIcon style={{ width: 18, height: 18, color: '#f59e0b' }} />
                  Pending Incident Reports
                </div>
              )}
              <div className="p-6">
                {reports.length === 0 ? (
                  <div className="text-center py-16">
                    <CheckCircleIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium text-lg">No pending reports to review.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {reports.map(report => (
                      <div key={report.id} className="border border-orange-100 rounded-xl overflow-hidden hover:shadow-md transition-all flex flex-col">
                        <div className="p-5 flex-1">
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <p className="text-[10px] font-bold text-orange-600 uppercase tracking-widest">{new Date(report.created_at).toLocaleString()}</p>
                              <h4 className="font-bold text-gray-900 mt-1">Sender: <span className="text-[#00d084]">{report.sender_nickname}</span></h4>
                            </div>
                            <div className="text-right">
                              <p className="text-[10px] font-bold text-gray-400 uppercase">Reported By</p>
                              <p className="text-xs font-semibold text-gray-700 italic">{report.reporter_nickname || 'Anonymous'}</p>
                            </div>
                          </div>
                          <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                            <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Message Evidence</p>
                            {report.message_content && <p className="text-sm text-gray-800 italic break-words">"{report.message_content}"</p>}
                            {report.media_url && (
                              <div className="mt-3 pt-3 border-t border-gray-200/50">
                                {/\.(jpg|jpeg|png|webp)$/i.test(report.media_url) ? (
                                  <img src={report.media_url.startsWith('/') ? `${API_BASE}${report.media_url}` : report.media_url} alt="reported" className="max-w-full rounded-lg border border-gray-200 shadow-sm cursor-pointer" onClick={() => window.open(report.media_url.startsWith('/') ? `${API_BASE}${report.media_url}` : report.media_url, '_blank')} />
                                ) : (
                                  <a href={report.media_url.startsWith('/') ? `${API_BASE}${report.media_url}` : report.media_url} target="_blank" rel="noreferrer" className="text-[#00d084] font-bold text-xs">📎 View Attachment</a>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="bg-orange-50/50 p-4 border-t border-orange-100 flex gap-3">
                          <button onClick={() => handleReportBan(report)} className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm font-bold py-2 rounded-xl transition-colors">Ban Sender</button>
                          <button onClick={() => resolveReport(report.id)} className="flex-1 bg-white hover:bg-gray-100 text-gray-700 border border-gray-200 text-sm font-bold py-2 rounded-xl transition-colors">Dismiss</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>)}

          {/* ── AI FLAGGED ─────────────────────────────────────────────── */}
          {(activeTab === 'ai' || activeTab === 'all') && (
            <div style={{ borderBottom: activeTab === 'all' ? '12px solid #f8f9fa' : 'none' }}>
              {activeTab === 'all' && (
                <div style={{ padding: '24px 24px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: 700, color: '#0f766e' }}>
                  <ShieldExclamationIcon style={{ width: 18, height: 18, color: '#8b5cf6' }} />
                  AI Meta-Protection Flags
                </div>
              )}
              <div className="p-6">
                {warned.length === 0 ? (
                  <div className="text-center py-16">
                    <ShieldExclamationIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">No flagged messages recently.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {warned.map(msg => (
                      <div key={msg.id} className="border border-purple-100 rounded-xl overflow-hidden flex flex-col">
                        <div className="p-4 flex-1">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <p className="font-bold text-gray-900">{msg.persona_nickname}</p>
                              <p className="text-[10px] font-mono text-gray-400">{msg.gamified_persona_id.split('-')[0]}</p>
                            </div>
                            <div className="text-right">
                              <span className="bg-purple-100 text-purple-800 border border-purple-200 text-[10px] px-2 py-0.5 rounded uppercase font-bold">{msg.shield_reason?.replace(/_/g, ' ') || 'Flagged'}</span>
                              <p className="text-[10px] text-gray-400 mt-1">{new Date(msg.created_at).toLocaleTimeString()}</p>
                            </div>
                          </div>
                          <div className="bg-purple-50/50 rounded-lg p-3 border border-purple-50/80">
                            {msg.content_text && <p className="text-sm text-gray-800 italic break-words">"{msg.content_text}"</p>}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-2 border-t border-gray-100 text-right">
                          <button onClick={() => handleReportBan(msg)} className="text-xs font-bold text-red-600 hover:text-red-800 px-3 py-1 bg-red-50 hover:bg-red-100 rounded border border-red-100 transition-colors">Ban Sender</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>)}

          {/* ── ISSUE BAN ──────────────────────────────────────────────── */}
          {(activeTab === 'ban' || activeTab === 'all') && (
            <div style={{ borderBottom: activeTab === 'all' ? '12px solid #f8f9fa' : 'none' }}>
              {activeTab === 'all' && (
                <div style={{ padding: '24px 24px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: 700, color: '#0f766e' }}>
                  <UserMinusIcon style={{ width: 18, height: 18, color: '#00d084' }} />
                  Administrative Enforcement (Manual Ban)
                </div>
              )}
              <div className="p-6">
                <div className="bg-gray-900 text-white p-6 rounded-2xl">
                  <form onSubmit={handleBan} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 items-end">
                    <div>
                      <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Circle ID</label>
                      <input type="text" value={circleId} onChange={e => setCircleId(e.target.value)} required className="w-full bg-gray-800 border-none text-white text-sm py-3 px-4 rounded-xl focus:ring-2 focus:ring-red-500 outline-none" placeholder="UUID" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Identifier (Email/ID)</label>
                      <input type="text" value={userId} onChange={e => setUserId(e.target.value)} required className="w-full bg-gray-800 border-none text-white text-sm py-3 px-4 rounded-xl focus:ring-2 focus:ring-red-500 outline-none" placeholder="User email or ID" />
                    </div>
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Formal Reason</label>
                      <input type="text" value={reason} onChange={e => setReason(e.target.value)} required className="w-full bg-gray-800 border-none text-white text-sm py-3 px-4 rounded-xl focus:ring-2 focus:ring-red-500 outline-none" placeholder="Reason for ban" />
                    </div>
                    <div className="lg:col-span-1">
                      <button disabled={isSubmitting} type="submit" className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl shadow-lg transition-all active:scale-95">
                        {isSubmitting ? 'Processing...' : 'Execute Ban'}
                      </button>
                    </div>
                  </form>
                  {submitError && <p className="mt-4 text-red-400 text-sm font-semibold">{submitError}</p>}
                </div>
              </div>
            </div>
          )}

          {/* ── AUTH LOGS ─────────────────────────────────────────────── */}
          {(activeTab === 'auth' || activeTab === 'all') && (
            <div style={{ borderBottom: activeTab === 'all' ? '12px solid #f8f9fa' : 'none' }}>
              {activeTab === 'all' && (
                <div style={{ padding: '24px 24px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: 700, color: '#0f766e' }}>
                    <ShieldCheckIcon style={{ width: 18, height: 18, color: '#0d9488' }} />
                    Authentication Integrity Trail
                </div>
              )}
              <div className="p-6">
                {authLogs.length === 0 ? (
                  <div className="text-center py-16 text-gray-400 italic">No authentication logs recorded yet.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-gray-100 uppercase tracking-widest text-[10px] text-gray-400 font-bold">
                          <th className="pb-3 px-2">Timestamp</th>
                          <th className="pb-3 px-2">Account (Email)</th>
                          <th className="pb-3 px-2">Status</th>
                          <th className="pb-3 px-2">Diagnostic Comment</th>
                          <th className="pb-3 px-2">Metadata</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {authLogs.map(log => {
                            const isFail = log.status !== 'SUCCESS';
                            return (
                                <tr key={log.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="py-4 px-2 text-xs text-gray-500 whitespace-nowrap">
                                        <div className="font-bold text-gray-700">{new Date(log.timestamp).toLocaleDateString()}</div>
                                        <div>{new Date(log.timestamp).toLocaleTimeString()}</div>
                                    </td>
                                    <td className="py-4 px-2">
                                        <span className="text-sm font-semibold text-emerald-600 underline underline-offset-4 decoration-emerald-100">{log.email}</span>
                                    </td>
                                    <td className="py-4 px-2">
                                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                                            log.status === 'SUCCESS' ? 'bg-green-50 text-green-700 border-green-100' : 
                                            log.status === 'FAIL_KYC' ? 'bg-orange-50 text-orange-700 border-orange-100' :
                                            'bg-red-50 text-red-700 border-red-100'
                                        }`}>
                                            {log.status}
                                        </span>
                                    </td>
                                    <td className="py-4 px-2">
                                        <p className={`text-xs ${isFail ? 'font-bold text-gray-800' : 'text-gray-500'}`}>{log.comment}</p>
                                    </td>
                                    <td className="py-4 px-2">
                                        <p className="text-[10px] text-gray-400 font-mono" title={log.user_agent}>{log.ip_address || '0.0.0.0'}</p>
                                    </td>
                                </tr>
                            )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── BAN HISTORY ────────────────────────────────────────────── */}
          {(activeTab === 'history' || activeTab === 'all') && (
            <div style={{ borderBottom: activeTab === 'all' ? '12px solid #f8f9fa' : 'none' }}>
              {activeTab === 'all' && (
                <div style={{ padding: '24px 24px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: 700, color: '#0f766e' }}>
                  <TrashIcon style={{ width: 18, height: 18, color: '#64748b' }} />
                  Record of Active Enforcements
                </div>
              )}
              <div className="p-6">
                {bans.length === 0 ? (
                  <div className="text-center py-16 text-gray-400 italic">No ban records found.</div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {bans.map(ban => (
                      <div key={ban.id} className="py-5 first:pt-0 last:pb-0">
                        <div className="flex justify-between items-start gap-6">
                          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-5">
                            <div>
                              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Target User</p>
                              <p className="text-sm font-bold text-gray-900">{ban.user_email || 'System ID only'}</p>
                              <p className="text-[10px] font-mono text-gray-400 mt-1">{ban.user_id}</p>
                            </div>
                            <div>
                              <p style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Enforcement Detail</p>
                              <div style={{ background: '#fef2f2', padding: '12px', borderRadius: '12px', border: '1px solid #fee2e2', marginTop: '4px' }}>
                                <p style={{ fontSize: '12px', fontWeight: 700, color: '#991b1b' }}>Reason: <span style={{ fontWeight: 500, color: '#451a1a' }}>{ban.reason}</span></p>
                                {ban.reported_message_content && <div style={{ marginTop: '8px', borderTop: '1px solid #fca5a5', paddingTop: '8px', fontStyle: 'italic', fontSize: '11px', color: '#7f1d1d' }}>&ldquo;{ban.reported_message_content}&rdquo;</div>}
                              </div>
                            </div>
                            <div>
                              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Circle</p>
                              <p className="text-xs text-gray-600 truncate" title={ban.circle_id}>{ban.circle_id}</p>
                              <p className="text-[10px] text-gray-400 mt-1">{new Date(ban.created_at).toLocaleDateString()} at {new Date(ban.created_at).toLocaleTimeString()}</p>
                            </div>
                          </div>
                          <button onClick={() => handleRevoke(ban.id)} className="group flex flex-col items-center gap-1 mt-4 md:mt-0">
                            <div className="p-2 bg-gray-50 group-hover:bg-red-50 text-gray-400 group-hover:text-red-600 rounded-full transition-colors border border-transparent group-hover:border-red-100">
                              <TrashIcon className="w-5 h-5" />
                            </div>
                            <span className="text-[9px] font-bold text-gray-400 group-hover:text-red-600 uppercase">Revoke</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>)}

          {/* ── AUDIT TRAIL ────────────────────────────────────────────── */}
          {(activeTab === 'audit' || activeTab === 'all') && (
            <div>
              {/* Section Header */}
              <div style={{ padding: '28px 28px 0' }}>
                <p style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1.5px', margin: 0 }}>Administrative Surveillance</p>
                <h2 style={{ fontSize: '22px', fontWeight: 800, color: '#0f172a', margin: '4px 0 0' }}>System Integrity Trail</h2>
              </div>

              <div style={{ padding: '20px 28px 28px' }}>
                {activity.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '48px 0', color: '#94a3b8', fontStyle: 'italic' }}>No activity logs recorded yet.</div>
                ) : (
                  <div>
                    {/* Column Headers - hidden on mobile */}
                    <div className="hidden md:grid" style={{ gridTemplateColumns: '160px 180px 130px 1fr', gap: '12px', padding: '12px 16px', borderBottom: '1px solid #e2e8f0', marginBottom: '4px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Timestamp</span>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Administrator</span>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Action Taken</span>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Incident Details & Metadata</span>
                    </div>

                    {/* Log Rows */}
                    {activity.map((log, idx) => {
                      let details = {}
                      try { if (log.changes_json) details = typeof log.changes_json === 'string' ? JSON.parse(log.changes_json.replace(/'/g, '"')) : log.changes_json } catch { }
                      const adminName = log.admin_email ? log.admin_email.split('@')[0] : 'System'
                      const isBan = log.action === 'CREATE_BAN'
                      const isLast = idx === activity.length - 1

                      const actionColors = isBan
                        ? { bg: '#dc2626', text: '#fff' }
                        : { bg: '#16a34a', text: '#fff' }

                      return (
                        <div key={log.id} className="hidden md:grid" style={{
                          gridTemplateColumns: '160px 180px 130px 1fr',
                          gap: '12px', padding: '16px 16px',
                          borderBottom: isLast ? 'none' : '1px solid #f1f5f9',
                          borderLeft: isLast ? '3px solid #0f766e' : '3px solid transparent',
                          background: isLast ? '#f8fafc' : 'transparent',
                          alignItems: 'center',
                          transition: 'background 0.15s',
                        }}>
                          {/* Timestamp */}
                          <div>
                            <p style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b', margin: 0 }}>
                              {log.created_at ? new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
                            </p>
                            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '2px 0 0', fontFamily: 'monospace' }}>
                              {log.created_at ? new Date(log.created_at).toLocaleTimeString('en-US', { hour12: false }) + ' UTC' : ''}
                            </p>
                          </div>

                          {/* Admin */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <PersonaAvatar nickname={adminName} size="sm" />
                            <span style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>{adminName}</span>
                          </div>

                          {/* Action Badge */}
                          <div>
                            <span style={{
                              display: 'inline-block', fontSize: '10px', fontWeight: 800,
                              padding: '4px 10px', borderRadius: '4px', letterSpacing: '0.5px',
                              background: actionColors.bg, color: actionColors.text,
                              textTransform: 'uppercase',
                            }}>
                              {isBan ? 'CREATE BAN' : 'REVOKE BAN'}
                            </span>
                          </div>

                          {/* Details */}
                          <div>
                            <p style={{ fontSize: '13px', color: '#334155', margin: 0, lineHeight: 1.5 }}>
                              {Object.entries(details).length > 0
                                ? Object.entries(details).map(([k, v]) =>
                                  k.toLowerCase().includes('user') ? (
                                    <span key={k}>{isBan ? 'Banned' : 'Restored access for'} User <span style={{ fontWeight: 700, color: '#0d9488' }}>#{String(v).split('-')[0]}</span>. </span>
                                  ) : k.toLowerCase().includes('reason') ? (
                                    <span key={k}>Reason: {String(v)}. </span>
                                  ) : null
                                )
                                : <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '12px' }}>No metadata recorded</span>
                              }
                            </p>
                          </div>
                        </div>
                      )
                    })}
                    {/* Mobile Card Layout - visible only on mobile */}
                    <div className="md:hidden space-y-3">
                      {activity.map((log) => {
                        let details = {}
                        try { if (log.changes_json) details = typeof log.changes_json === 'string' ? JSON.parse(log.changes_json.replace(/'/g, '"')) : log.changes_json } catch { }
                        const adminName = log.admin_email ? log.admin_email.split('@')[0] : 'System'
                        const isBan = log.action === 'CREATE_BAN'
                        return (
                          <div key={`m-${log.id}`} style={{ padding: '14px', borderBottom: '1px solid #f1f5f9', borderLeft: `3px solid ${isBan ? '#dc2626' : '#16a34a'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <span style={{ fontSize: '12px', fontWeight: 600, color: '#1e293b' }}>
                                {log.created_at ? new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
                              </span>
                              <span style={{
                                display: 'inline-block', fontSize: '10px', fontWeight: 800,
                                padding: '3px 8px', borderRadius: '4px',
                                background: isBan ? '#dc2626' : '#16a34a', color: '#fff',
                                textTransform: 'uppercase',
                              }}>
                                {isBan ? 'BAN' : 'REVOKE'}
                              </span>
                            </div>
                            <p style={{ fontSize: '13px', fontWeight: 600, color: '#334155', margin: '0 0 4px' }}>By: {adminName}</p>
                            <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
                              {Object.entries(details).length > 0
                                ? Object.entries(details).map(([k, v]) =>
                                    k.toLowerCase().includes('reason') ? `Reason: ${String(v)}` : null
                                  ).filter(Boolean).join('. ') || 'Action recorded'
                                : 'No metadata'}
                            </p>
                          </div>
                        )
                      })}
                    </div>

                    {/* Footer */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderTop: '1px solid #e2e8f0', marginTop: '8px' }}>
                      <span style={{ fontSize: '12px', color: '#94a3b8' }}>Showing {activity.length} entries</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </Layout>
  )
}
