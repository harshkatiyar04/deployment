import { useState, useCallback, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ChatProvider } from '../../../contexts/ChatContext'
import MessageList from '../../../components/chat/MessageList'
import MessageInput from '../../../components/chat/MessageInput'
import StageBar from '../../../components/chat/StageBar'
import RaiseHandButton from '../../../components/chat/RaiseHandButton'
import { usePersona } from '../../../contexts/PersonaContext'
import { SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useChat } from '../../../contexts/ChatContext'
import InterventionOverlay from '../../../components/chat/InterventionOverlay'

const QUICK_CHIPS = [
  "Review Ananya's progress",
  "Ananya's attendance",
  "Budget summary",
  "Planning for FY27",
  "Circle rank",
  "My contribution",
  "Top 3 national circles",
  "Monthly time stats"
]

function QuickChips() {
  const { sendMessage, activeChannel } = useChat()
  const scrollRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [startX, setStartX] = useState(0)
  const [scrollLeft, setScrollLeft] = useState(0)
  const [hasDragged, setHasDragged] = useState(false)

  const handleMouseDown = (e) => {
    setIsDragging(true)
    setHasDragged(false)
    setStartX(e.pageX - scrollRef.current.offsetLeft)
    setScrollLeft(scrollRef.current.scrollLeft)
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return
    e.preventDefault()
    const x = e.pageX - scrollRef.current.offsetLeft
    const walk = (x - startX) * 2
    if (Math.abs(walk) > 5) {
      setHasDragged(true)
    }
    scrollRef.current.scrollLeft = scrollLeft - walk
  }

  const handleMouseUp = () => setIsDragging(false)
  const handleMouseLeave = () => setIsDragging(false)

  const canSend = !!activeChannel?.id

  return (
    <div 
      className="sc-quick-chips"
      ref={scrollRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
    >
      {QUICK_CHIPS.map((chip) => (
        <button 
          key={chip} 
          className="sc-chip" 
          disabled={!canSend}
          onMouseUp={(e) => {
            if (!hasDragged && canSend) {
              sendMessage(activeChannel.id, `@Kia ${chip}`)
            }
          }}
          style={{ 
            opacity: canSend ? 1 : 0.5, 
            cursor: canSend ? (isDragging ? 'grabbing' : 'pointer') : 'not-allowed' 
          }}
        >
          {chip}
        </button>
      ))}
    </div>
  )
}

function ChatContentWrapper({ userRole }) {
  const { wsError, setWsError, nudgeActive, dismissNudge, channels, activeChannel, setActiveChannel } = useChat()
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--sc-cream)', position: 'relative', overflow: 'hidden' }}>
      {wsError?.code === 'message_blocked' && (
        <InterventionOverlay 
          type="block" 
          message={wsError.reason} 
          onDismiss={() => setWsError(null)} 
        />
      )}

      {wsError && wsError.code !== 'message_blocked' && (
        <div style={{ padding: '8px 12px', background: '#fee2e2', color: '#991b1b', fontSize: '11px', borderBottom: '1px solid #fca5a5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span><strong>Connection Error:</strong> {wsError.reason || wsError.code}</span>
          {wsError.code === 'auth_failed' && (
            <Link to="/chat-demo" style={{ background: '#991b1b', color: 'white', padding: '2px 6px', borderRadius: '4px', textDecoration: 'none', fontWeight: 'bold', fontSize: '10px' }}>
              Login
            </Link>
          )}
        </div>
      )}

      {nudgeActive && (
        <div style={{ padding: '8px 12px', background: '#fffbeb', color: '#92400e', fontSize: '11px', borderBottom: '1px solid #fde68a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>⚠️ Keep conversations safe and on-platform.</span>
          <button onClick={dismissNudge} style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '2px' }}>
            <XMarkIcon className="w-3 h-3 text-[#92400e]" />
          </button>
        </div>
      )}

      <StageBar userPersona={userRole} />

      {/* Channel Switcher added inside KIA panel */}
      {channels && channels.length > 0 && (
        <div style={{ display: 'flex', overflowX: 'auto', gap: '8px', padding: '8px 12px', background: 'white', borderBottom: '1px solid var(--sc-border)', scrollbarWidth: 'none' }} className="sc-quick-chips">
          {channels.map(channel => (
            <button
              key={channel.id}
              onClick={() => setActiveChannel(channel)}
              style={{
                flexShrink: 0,
                padding: '4px 12px',
                borderRadius: '999px',
                fontSize: '11px',
                fontWeight: activeChannel?.id === channel.id ? 700 : 500,
                background: activeChannel?.id === channel.id ? 'var(--sc-green-dark)' : 'var(--sc-cream)',
                color: activeChannel?.id === channel.id ? 'white' : 'var(--sc-text)',
                border: '1px solid',
                borderColor: activeChannel?.id === channel.id ? 'var(--sc-green-dark)' : 'var(--sc-border)',
                cursor: 'pointer'
              }}
            >
              #{channel.name}
            </button>
          ))}
        </div>
      )}

      <QuickChips />
      
      <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column', background: 'white' }}>
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}>
          <RaiseHandButton userPersona={userRole} />
        </div>
        <MessageList userPersona={userRole} />
      </div>

      <div style={{ background: 'white', padding: '10px 12px', borderTop: '1px solid var(--sc-border)' }}>
        <MessageInput userPersona={userRole} />
      </div>
    </div>
  )
}

function LiveChatInner({ circleId, userRole }) {
  return (
    <ChatProvider circleId={circleId}>
      <ChatContentWrapper userRole={userRole} />
    </ChatProvider>
  )
}

export default function SCKiaPanel() {
  const { persona } = usePersona()
  const userRole = persona || 'sponsor'

  const [circleId, setCircleId] = useState('481eba8f-778d-4618-8f9e-6e6b263d89a0')
  const [activeCircleId, setActiveCircleId] = useState('481eba8f-778d-4618-8f9e-6e6b263d89a0')
  const [inputVal, setInputVal] = useState('')
  const [panelSize, setPanelSize] = useState('half') // 'compact', 'half', 'full'

  // Persist panel width in localStorage
  const [panelWidth, setPanelWidth] = useState(() => {
    const saved = localStorage.getItem('sc_chat_panel_width')
    return saved ? parseInt(saved, 10) : 450
  })

  const isResizing = useRef(false)

  useEffect(() => {
    localStorage.setItem('sc_chat_panel_width', panelWidth)
  }, [panelWidth])

  const handleMouseDown = useCallback((e) => {
    isResizing.current = true
    document.body.style.cursor = 'ew-resize'
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleMouseMove = useCallback((e) => {
    if (!isResizing.current) return
    const newWidth = document.body.clientWidth - e.clientX
    if (newWidth > 250 && newWidth < 800) {
      setPanelWidth(newWidth)
    }
  }, [])

  const handleMouseUp = useCallback(() => {
    isResizing.current = false
    document.body.style.cursor = 'auto'
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleJoin = (e) => {
    e.preventDefault()
    if (!inputVal.trim()) return
    setCircleId(inputVal.trim())
    setActiveCircleId(inputVal.trim())
  }

  return (
    <div className={`sc-right-panel mobile-size-${panelSize}`} style={window.innerWidth > 768 ? { width: panelWidth, minWidth: panelWidth, position: 'relative' } : {}}>
      {/* Resizer Handle */}
      <div 
        className="sc-resizer-handle"
        style={{ position: 'absolute', left: -2, top: 0, bottom: 0, width: '6px', cursor: 'ew-resize', zIndex: 100 }}
        onMouseDown={handleMouseDown}
      />
      <div className="sc-panel-header">
        <span className="sc-panel-dot" />
        <span className="sc-panel-title">Chat &amp; Kia</span>
        
        {/* Mobile Size Toggles */}
        <div className="sc-mobile-size-toggles" style={{ marginLeft: 'auto', display: 'none', alignItems: 'center', gap: '4px' }}>
          <button onClick={() => setPanelSize('compact')} style={{ padding: '2px 6px', fontSize: 10, borderRadius: 4, background: panelSize === 'compact' ? '#1e8e6a' : '#f4f3eb', color: panelSize === 'compact' ? 'white' : '#6b7280', border: 'none' }}>Compact</button>
          <button onClick={() => setPanelSize('half')} style={{ padding: '2px 6px', fontSize: 10, borderRadius: 4, background: panelSize === 'half' ? '#1e8e6a' : '#f4f3eb', color: panelSize === 'half' ? 'white' : '#6b7280', border: 'none' }}>Half</button>
          <button onClick={() => setPanelSize('full')} style={{ padding: '2px 6px', fontSize: 10, borderRadius: 4, background: panelSize === 'full' ? '#1e8e6a' : '#f4f3eb', color: panelSize === 'full' ? 'white' : '#6b7280', border: 'none' }}>Full</button>
        </div>

        <SparklesIcon style={{ marginLeft: window.innerWidth > 768 ? 'auto' : 0, width: 18, height: 18, color: '#f08c3b' }} />
      </div>

      <div className="sc-kia-header">
        <div className="sc-kia-avatar" style={{ padding: 0, overflow: 'hidden' }}>
          <img src="/kia-bot-avatar.png" alt="Kia" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div>
          <div className="sc-kia-name">Kia AI Copilot</div>
          <div className="sc-kia-sub">Your circle assistant</div>
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {!activeCircleId ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 20, gap: 12 }}>
            <div style={{ textAlign: 'center', fontSize: 13, color: '#191c1d', fontWeight: 600 }}>
              Join your Circle Chat
            </div>
            <div style={{ textAlign: 'center', fontSize: 12, color: '#6b7280' }}>
              Enter your Circle ID to connect to the live session
            </div>
            <form onSubmit={handleJoin} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <input
                type="text"
                placeholder="Circle ID (e.g. ashoka-01)"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                style={{
                  padding: '9px 12px',
                  borderRadius: 8,
                  border: '1px solid #e5e7eb',
                  fontSize: 13,
                  outline: 'none',
                  fontFamily: 'Inter, sans-serif',
                }}
              />
              <button
                type="submit"
                style={{
                  background: '#1e8e6a',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  padding: '9px 12px',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Connect to Chat
              </button>
            </form>
          </div>
        ) : (
          <LiveChatInner circleId={activeCircleId} userRole={userRole} />
        )}
      </div>
    </div>
  )
}
