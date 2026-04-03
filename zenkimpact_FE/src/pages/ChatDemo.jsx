import { useState } from 'react'
import { ChatProvider, useChat } from '../contexts/ChatContext'
import ChannelSidebar from '../components/chat/ChannelSidebar'
import MessageList from '../components/chat/MessageList'
import MessageInput from '../components/chat/MessageInput'
import StageBar from '../components/chat/StageBar'
import RaiseHandButton from '../components/chat/RaiseHandButton'
import { usePersona } from '../contexts/PersonaContext'
import axios from 'axios'
import Layout from '../components/Layout'
import { ChatBubbleLeftRightIcon, KeyIcon, ArrowRightOnRectangleIcon, LockClosedIcon, ShieldCheckIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import CircleInfoModal from '../components/chat/CircleInfoModal'
import InterventionOverlay from '../components/chat/InterventionOverlay'

function ChatSandbox({ circleId, onDisconnect, onLogout }) {
  const { persona } = usePersona()
  const userRole = persona || 'sponsor'

  return (
    <ChatProvider circleId={circleId}>
      <ChatContent userRole={userRole} circleId={circleId} onDisconnect={onDisconnect} onLogout={onLogout} />
    </ChatProvider>
  )
}

function ChatContent({ userRole, circleId, onDisconnect, onLogout }) {
  const { wsError, setWsError, activeChannel, status, stageActive, setStageActive } = useChat()
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false)

  // Handle transient errors (like message_blocked) without full-page replacement
  if (wsError?.code === 'message_blocked') {
    return (
      <ChatSandboxContent setStageActive={setStageActive} stageActive={stageActive} circleId={circleId} isInfoModalOpen={isInfoModalOpen} setIsInfoModalOpen={setIsInfoModalOpen} onDisconnect={onDisconnect} onLogout={onLogout} userRole={userRole} activeChannel={activeChannel} wsError={wsError} setWsError={setWsError} />
    )
  }

  if (wsError || status === 'error') {
    const isBanned = wsError?.code === 'banned'
    const errorMsg = wsError?.reason || 'Failed to connect to the circle chat. Please check your backend and connection settings.'

    return (
      <div className={`flex flex-col items-center justify-center h-[calc(100vh-120px)] ${isBanned ? 'bg-red-50 text-red-700 border-red-200' : 'bg-orange-50 text-orange-700 border-orange-200'} border rounded-xl mx-4 my-6 p-8 text-center shadow-sm`}>
        <div className={`${isBanned ? 'bg-red-100' : 'bg-orange-100'} p-4 rounded-full mb-4`}>
          <svg className={`w-12 h-12 ${isBanned ? 'text-red-600' : 'text-orange-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold mb-2">{isBanned ? 'Access Denied' : 'Connection Error'}</h2>
        <p className="max-w-md mx-auto mb-4">
          {isBanned ? 'You have been banned from this circle.' : errorMsg}
        </p>
        {wsError?.code && !isBanned && (
          <div className="bg-orange-200/50 px-4 py-2 rounded-lg border border-orange-200 text-sm font-medium">
            Error Code: {wsError.code}
          </div>
        )}
      </div>
    )
  }

  if (status === 'connecting') {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-120px)] bg-white border border-gray-200 rounded-xl mx-4 my-6 shadow-sm">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-500 font-medium">Connecting to circle...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-96px)] max-w-[1600px] mx-auto w-full bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200">
      <CircleInfoModal isOpen={isInfoModalOpen} onClose={() => setIsInfoModalOpen(false)} />
      
      {/* Top Header — Circle name + Kla badge + Controls */}
      <div className="flex items-center justify-between bg-white px-6 py-3 border-b border-gray-100">
        <div className="flex items-center gap-4">
          <div 
            className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-xl transition-colors group"
            onClick={() => setIsInfoModalOpen(true)}
          >
            <div className="flex items-center justify-center w-9 h-9 rounded-full bg-teal-50 text-teal-600 group-hover:scale-105 transition-transform">
               <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-gray-900 text-sm font-bold block tracking-tight">Circle Environment</span>
                <InformationCircleIcon className="w-4 h-4 text-teal-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className="text-teal-600 text-xs font-mono font-medium">{circleId}</span>
            </div>
          </div>

          {/* Kla Active Badge */}
          <div className="flex items-center gap-1.5 text-xs font-semibold text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-100">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
            Kia is active
          </div>
        </div>

        <div className="flex gap-4 items-center">
          <button
            id="start-stage-btn"
            onClick={() => setStageActive(!stageActive)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-sm ${stageActive
                ? 'bg-teal-600 text-white hover:bg-teal-700 ring-2 ring-teal-500/50'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
          >
            {stageActive ? 'Stop Stage Session' : 'Start Stage Session'}
          </button>
          <div className="w-px h-6 bg-gray-200 mx-2"></div>
          <button
            onClick={onDisconnect}
            className="text-xs font-semibold text-gray-500 hover:text-teal-600 transition-colors"
          >
            Leave
          </button>
          <button
            onClick={onLogout}
            className="text-xs font-semibold text-gray-500 hover:text-teal-600 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat Layout */}
      <div className="flex-1 flex bg-white overflow-hidden relative">
        <ChannelSidebar />

        <div className="flex-1 flex flex-col min-w-0 bg-[#FAFBFC] relative z-0">
          <StageBar userPersona={userRole} />

          <div className="flex-1 flex flex-col min-h-0 relative z-10">
            <div className="absolute top-4 right-6 z-20 flex gap-2">
              <RaiseHandButton userPersona={userRole} />
            </div>

            <MessageList userPersona={userRole} activeChannelId={activeChannel?.id} />
          </div>

          <div className="bg-white z-10 px-6 py-4 border-t border-gray-100">
            <MessageInput userPersona={userRole} handRaised={false} />
          </div>
        </div>
      </div>
    </div>
  )
}

function ChatSandboxContent({ setStageActive, stageActive, circleId, isInfoModalOpen, setIsInfoModalOpen, onDisconnect, onLogout, userRole, activeChannel, wsError, setWsError }) {
  return (
    <div className="flex flex-col h-[calc(100vh-96px)] max-w-[1600px] mx-auto w-full bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200 relative">
      <CircleInfoModal isOpen={isInfoModalOpen} onClose={() => setIsInfoModalOpen(false)} />
      
      {wsError?.code === 'message_blocked' && (
        <InterventionOverlay 
          type="block" 
          message={wsError.reason} 
          onDismiss={() => setWsError(null)} 
        />
      )}
      
      {/* Top Header — Circle name + Kla badge + Controls */}
      <div className="flex items-center justify-between bg-white px-6 py-3 border-b border-gray-100">
        <div className="flex items-center gap-4">
          <div 
            className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-xl transition-colors group"
            onClick={() => setIsInfoModalOpen(true)}
          >
            <div className="flex items-center justify-center w-9 h-9 rounded-full bg-teal-50 text-teal-600 group-hover:scale-105 transition-transform">
               <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-gray-900 text-sm font-bold block tracking-tight">Circle Environment</span>
                <InformationCircleIcon className="w-4 h-4 text-teal-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className="text-teal-600 text-xs font-mono font-medium">{circleId}</span>
            </div>
          </div>

          {/* Kla Active Badge */}
          <div className="flex items-center gap-1.5 text-xs font-semibold text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-100">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
            Kia is active
          </div>
        </div>

        <div className="flex gap-4 items-center">
          <button
            id="start-stage-btn"
            onClick={() => setStageActive(!stageActive)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-sm ${stageActive
                ? 'bg-teal-600 text-white hover:bg-teal-700 ring-2 ring-teal-500/50'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
          >
            {stageActive ? 'Stop Stage Session' : 'Start Stage Session'}
          </button>
          <div className="w-px h-6 bg-gray-200 mx-2"></div>
          <button
            onClick={onDisconnect}
            className="text-xs font-semibold text-gray-500 hover:text-teal-600 transition-colors"
          >
            Leave
          </button>
          <button
            onClick={onLogout}
            className="text-xs font-semibold text-gray-500 hover:text-teal-600 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat Layout */}
      <div className="flex-1 flex bg-white overflow-hidden relative">
        <ChannelSidebar />

        <div className="flex-1 flex flex-col min-w-0 bg-[#FAFBFC] relative z-0">
          <StageBar userPersona={userRole} />

          <div className="flex-1 flex flex-col min-h-0 relative z-10">
            <div className="absolute top-4 right-6 z-20 flex gap-2">
              <RaiseHandButton userPersona={userRole} />
            </div>

            <MessageList userPersona={userRole} activeChannelId={activeChannel?.id} />
          </div>

          <div className="bg-white z-10 px-6 py-4 border-t border-gray-100">
            <MessageInput userPersona={userRole} handRaised={false} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ChatDemo() {
  const [circleId, setCircleId] = useState('')
  const [activeCircleId, setActiveCircleId] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [joinError, setJoinError] = useState('')
  const [token, setToken] = useState(localStorage.getItem('chat_token'))

  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError('')
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const res = await axios.post(`${apiBase}/auth/token`, {
        email: email,
        password: password
      })

      const newToken = res.data.access_token
      localStorage.setItem('chat_token', newToken)
      setToken(newToken)
    } catch (err) {
      setAuthError('Login failed: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleJoin = (e) => {
    e.preventDefault()
    setJoinError('')
    const trimmedId = circleId.trim()
    if (!trimmedId) return
    
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    if (!uuidRegex.test(trimmedId)) {
      setJoinError('Invalid Circle ID format. Must be a valid 36-character UUID.')
      return
    }
    
    setActiveCircleId(trimmedId)
  }

  const handleLogout = () => {
    localStorage.removeItem('chat_token')
    setToken(null)
    setActiveCircleId(null)
    setCircleId('')
  }

  return (
    <Layout>
      <div className={`bg-[#FAFBFC] relative ${activeCircleId ? 'h-[calc(100vh-64px)] py-4 overflow-hidden' : 'min-h-[calc(100vh-64px)] py-12 overflow-x-hidden'}`}>
        <div className="absolute top-0 left-0 w-full h-[450px] bg-gradient-to-b from-teal-600 to-teal-700 z-0"></div>

        <div className={`mx-auto w-full h-full relative z-10 transition-all duration-300 ${activeCircleId ? 'max-w-[1700px] px-2 flex flex-col' : 'max-w-5xl px-4'}`}>
          {(!token || !activeCircleId) && (
            <div className="flex flex-col items-center justify-center text-center mb-10 pt-4">
              <div className="inline-flex items-center justify-center p-3 bg-white/10 rounded-2xl backdrop-blur-md border border-white/20 mb-6 shadow-xl text-white">
                 <ChatBubbleLeftRightIcon className="w-8 h-8" />
              </div>
              <h1 className="text-3xl font-bold text-white tracking-tight">Zenk Impact Sandbox</h1>
              <p className="text-blue-100 text-lg mt-2 max-w-xl">Secure, AI-shielded communication for communities.</p>
            </div>
          )}

          <div className="flex justify-center flex-col items-center">
            {!token && (
              <div className="w-full bg-white p-10 rounded-2xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] flex flex-col md:flex-row gap-12 mx-auto border border-gray-100">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 mb-6 tracking-tight">Get Started</h2>
                  <ol className="list-decimal list-outside ml-5 text-gray-600 space-y-4 mb-8">
                    <li>Log in with your authorized email</li>
                    <li>Enter your account password</li>
                    <li>Click <span className="font-bold text-gray-900">Authenticate</span></li>
                  </ol>
                  <a href="#" className="text-teal-600 text-sm font-medium hover:text-teal-800 hover:underline">Need help logging in?</a>
                </div>
                
                <div className="w-full md:w-[360px]">
                  <form onSubmit={handleLogin} className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Email address</label>
                      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10 focus:outline-none text-gray-900 transition-all" placeholder="name@domain.com" required />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
                      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10 focus:outline-none text-gray-900 transition-all" placeholder="••••••••" required />
                    </div>
                    {authError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm font-medium border border-red-100">{authError}</div>}
                    <button type="submit" className="w-full flex justify-center py-3.5 px-4 rounded-xl shadow-sm text-sm font-bold text-white bg-teal-600 hover:bg-teal-700 transition-colors mt-4 block">
                      Authenticate
                    </button>
                  </form>
                </div>
              </div>
            )}

            {token && !activeCircleId ? (
               <div className="w-full bg-white p-10 rounded-2xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] flex flex-col md:flex-row gap-12 mx-auto border border-gray-100">
                <div className="flex-1">
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-teal-50 text-teal-700 text-xs font-bold uppercase tracking-wider mb-6 border border-teal-100">
                    <ShieldCheckIcon className="w-4 h-4 mr-1" /> Authenticated
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-4 tracking-tight">Connect to a Circle</h2>
                  <p className="text-gray-600 mb-8 max-w-sm">You are successfully authenticated. Please provide a Circle UUID to establish a secure WebSocket connection.</p>
                </div>
                
                <div className="w-full md:w-[360px] flex flex-col justify-center">
                  <form onSubmit={handleJoin} className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Target Circle UUID
                      </label>
                      <input
                        type="text"
                        value={circleId}
                        onChange={(e) => setCircleId(e.target.value)}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10 focus:outline-none text-gray-900 font-mono text-sm transition-all shadow-inner"
                        placeholder="e.g. 550e8400-e29b-..."
                        required
                      />
                    </div>
                    <button
                      type="submit"
                      className="w-full flex justify-center py-3.5 px-4 rounded-xl shadow-sm text-sm font-bold text-white bg-teal-600 hover:bg-teal-700 transition-colors mt-4 block"
                    >
                      Connect
                    </button>
                    {joinError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm font-medium border border-red-100 mt-2">{joinError}</div>}
                  </form>
                  
                  <div className="mt-8 pt-6 border-t border-gray-100">
                    <button onClick={handleLogout} className="text-gray-500 text-sm font-medium hover:text-red-600 transition-colors flex items-center justify-center w-full">
                      <LockClosedIcon className="w-4 h-4 mr-1" /> Revoke Token & Sign Out
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
            
            {token && activeCircleId && (
              <div className="w-full flex-1 flex flex-col min-h-0">
                <ChatSandbox circleId={activeCircleId} onDisconnect={() => setActiveCircleId(null)} onLogout={handleLogout} />
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
