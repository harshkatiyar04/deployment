import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatBubbleLeftRightIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { ChatProvider } from '../../contexts/ChatContext'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import StageBar from './StageBar'
import RaiseHandButton from './RaiseHandButton'
import { usePersona } from '../../contexts/PersonaContext'
import axios from 'axios'

function WidgetInner({ circleId }) {
  const { persona } = usePersona()
  const userRole = persona || 'sponsor'

  return (
    <ChatProvider circleId={circleId}>
      <div className="flex flex-col h-full bg-gray-50/50">
        <StageBar userPersona={userRole} />
        <div className="flex-1 flex flex-col min-h-0 relative">
          <div className="absolute top-2 right-2 z-10">
            <RaiseHandButton userPersona={userRole} />
          </div>
          <MessageList userPersona={userRole} />
        </div>
        <MessageInput userPersona={userRole} handRaised={false} />
      </div>
    </ChatProvider>
  )
}

export default function ChatWidget() {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const [circleId, setCircleId] = useState('')
  const [activeCircleId, setActiveCircleId] = useState(null)
  
  // Hide widget on certain pages to avoid overlap
  if (location.pathname === '/chat-demo') {
    return null
  }
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [token, setToken] = useState(localStorage.getItem('chat_token'))

  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError('')
    try {
      const getApiBase = () => {
        if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
        if (typeof window !== 'undefined' && (window.location.hostname.includes('vercel.app') || window.location.hostname.includes('zenk'))) {
          return 'https://deployment-production-27bd.up.railway.app';
        }
        return 'http://localhost:8000';
      };
      const apiBase = getApiBase();
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
    if (!circleId.trim()) return
    setActiveCircleId(circleId.trim())
  }

  return (
    <div className="fixed bottom-4 right-4 md:bottom-6 md:right-6 z-50 flex flex-col items-end">
      {/* The Popup Window */}
      {isOpen && (
        <div className="mb-4 w-[calc(100vw-32px)] md:w-[350px] h-[70vh] md:h-[500px] bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col transition-all duration-300 origin-bottom-right">
          
          {/* Header */}
          <div className="bg-teal-600 text-white px-4 py-3 flex justify-between items-center shadow-sm z-10">
            <div className="flex items-center gap-2">
              <ChatBubbleLeftRightIcon className="w-5 h-5" />
              <h3 className="font-semibold text-sm">Zenk Chat</h3>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto bg-gray-50 flex flex-col">
            {!token ? (
              <div className="p-6 h-full flex flex-col justify-center">
                <h4 className="font-medium text-gray-900 mb-4 text-center">Login to Chat</h4>
                <form onSubmit={handleLogin} className="space-y-3">
                  <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-teal-500 outline-none"
                    required
                  />
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-teal-500 outline-none"
                    required
                  />
                  {authError && <p className="text-red-500 text-xs">{authError}</p>}
                  <button className="w-full bg-teal-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-teal-700">
                    Authenticate
                  </button>
                </form>
              </div>
            ) : !activeCircleId ? (
              <div className="p-6 h-full flex flex-col justify-center">
                <h4 className="font-medium text-gray-900 mb-2 text-center">Join Circle</h4>
                <p className="text-xs text-gray-500 text-center mb-4">Enter a Circle ID to connect to the live chat session.</p>
                <form onSubmit={handleJoin} className="space-y-3">
                  <input
                    type="text"
                    placeholder="Circle ID"
                    value={circleId}
                    onChange={e => setCircleId(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-2 focus:ring-teal-500 outline-none"
                    required
                  />
                  <button className="w-full bg-teal-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-teal-700">
                    Connect
                  </button>
                </form>
              </div>
            ) : (
              <WidgetInner circleId={activeCircleId} />
            )}
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-14 h-14 bg-teal-600 hover:bg-teal-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center ${isOpen ? 'rotate-90 scale-90 bg-gray-600 hover:bg-gray-700' : ''}`}
      >
        {isOpen ? (
          <XMarkIcon className="w-6 h-6" />
        ) : (
          <ChatBubbleLeftRightIcon className="w-6 h-6" />
        )}
      </button>
    </div>
  )
}
