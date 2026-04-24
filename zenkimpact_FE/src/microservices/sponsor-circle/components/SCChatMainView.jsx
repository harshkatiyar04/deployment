import { useState, useEffect } from 'react'
import { HashtagIcon, UserIcon, ArrowLeftIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'
import { ChatProvider, useChat } from '../../../contexts/ChatContext'
import MessageList from '../../../components/chat/MessageList'
import MessageInput from '../../../components/chat/MessageInput'
import StageBar from '../../../components/chat/StageBar'
import RaiseHandButton from '../../../components/chat/RaiseHandButton'
import InterventionOverlay from '../../../components/chat/InterventionOverlay'
import { DM_MEMBERS } from '../data/placeholders'

/* ──────────────────────────────────────────────
   Mobile hook – true when viewport ≤ 768px
   ────────────────────────────────────────────── */
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const handler = (e) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return isMobile
}

/* ──────────────────────────────────────────────
   MOBILE Channel List (WhatsApp-style home screen)
   ────────────────────────────────────────────── */
function MobileChannelList({ channels, onSelectChannel, isLeader, onSelectDM }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'white', minHeight: 0 }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--sc-border)',
        background: 'linear-gradient(135deg, #1e8e6a 0%, #166d50 100%)',
        color: 'white',
      }}>
        <div style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.3px' }}>Chats</div>
        <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '2px' }}>
          {channels.length} channel{channels.length !== 1 ? 's' : ''} available
        </div>
      </div>

      {/* Channel list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        <div style={{ padding: '12px 20px 8px', fontSize: '11px', fontWeight: 800, color: 'var(--sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          Circle Channels
        </div>
        {channels.map((channel) => (
          <button
            key={channel.id}
            onClick={() => onSelectChannel(channel)}
            style={{
              display: 'flex', alignItems: 'center', gap: '14px', width: '100%',
              padding: '14px 20px', fontSize: '15px', fontWeight: 500,
              color: 'var(--sc-text)', background: 'transparent',
              border: 'none', borderBottom: '1px solid #f3f4f6',
              cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s',
            }}
          >
            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              background: 'var(--sc-green-bg)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <HashtagIcon style={{ width: 22, height: 22, color: 'var(--sc-green-dark)' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '15px', color: '#1a1a1a' }}>{channel.name}</div>
              <div style={{ fontSize: '12px', color: 'var(--sc-text-muted)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                Tap to join conversation
              </div>
            </div>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
          </button>
        ))}

        {/* DM Channels — Leader Only */}
        {isLeader && (
          <>
            <div style={{ padding: '20px 20px 8px', fontSize: '11px', fontWeight: 800, color: '#f08c3b', textTransform: 'uppercase', letterSpacing: '0.8px', borderTop: '1px solid var(--sc-border)', marginTop: '8px' }}>
              Direct Messages
            </div>
            {DM_MEMBERS.map((member) => (
              <button
                key={member.id}
                onClick={() => onSelectDM(member)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '14px', width: '100%',
                  padding: '14px 20px', fontSize: '15px', fontWeight: 500,
                  color: 'var(--sc-text)', background: 'transparent',
                  border: 'none', borderBottom: '1px solid #f3f4f6',
                  cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s',
                }}
              >
                <div style={{ position: 'relative' }}>
                  <div style={{
                    width: '44px', height: '44px', borderRadius: '50%',
                    background: '#fff7ed', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    fontSize: '14px', fontWeight: 700, color: '#f08c3b',
                  }}>{member.initials}</div>
                  {member.online && (
                    <div style={{ position: 'absolute', bottom: 1, right: 1, width: '12px', height: '12px', borderRadius: '50%', background: '#22c55e', border: '2px solid white' }} />
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '15px', color: '#1a1a1a' }}>{member.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--sc-text-muted)', marginTop: '2px' }}>
                    {member.online ? 'Online' : 'Offline'}
                  </div>
                </div>
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   MOBILE Chat View (WhatsApp-style conversation)
   ────────────────────────────────────────────── */
function MobileChatView({ userRole, activeDM, activeChannel, onBack, dmMessages, setDmMessages, dmInput, setDmInput }) {
  const { wsError, setWsError, nudgeActive, dismissNudge } = useChat()

  const handleDMSend = (e) => {
    e.preventDefault()
    if (!dmInput.trim() || !activeDM) return
    const msgs = dmMessages[activeDM.id] || []
    setDmMessages({
      ...dmMessages,
      [activeDM.id]: [...msgs, { id: Date.now(), text: dmInput, sender: 'you', time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) }]
    })
    setDmInput('')
  }

  const currentDMMessages = activeDM ? (dmMessages[activeDM.id] || []) : []
  const chatName = activeDM ? activeDM.name : `#${activeChannel?.name || 'General'}`
  const isDM = !!activeDM

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, background: 'white' }}>
      {/* WhatsApp-style top bar with back arrow */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '8px 12px',
        background: 'linear-gradient(135deg, #1e8e6a 0%, #166d50 100%)',
        color: 'white', flexShrink: 0,
      }}>
        <button
          onClick={onBack}
          style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
        >
          <ArrowLeftIcon style={{ width: 22, height: 22 }} />
        </button>
        <div style={{
          width: '36px', height: '36px', borderRadius: '50%',
          background: isDM ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          {isDM
            ? <span style={{ fontSize: '13px', fontWeight: 700 }}>{activeDM.initials}</span>
            : <HashtagIcon style={{ width: 18, height: 18 }} />
          }
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '16px', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {chatName}
          </div>
          <div style={{ fontSize: '11px', opacity: 0.8 }}>
            {isDM ? (activeDM.online ? 'Online' : 'Offline') : 'Circle channel'}
          </div>
        </div>
        {!isDM && <RaiseHandButton userPersona={userRole} />}
      </div>

      {/* Error / Nudge banners */}
      {wsError?.code === 'message_blocked' && (
        <InterventionOverlay type="block" message={wsError.reason} onDismiss={() => setWsError(null)} />
      )}
      {wsError && wsError.code !== 'message_blocked' && (
        <div style={{ padding: '8px 12px', background: '#fee2e2', color: '#991b1b', fontSize: '11px', borderBottom: '1px solid #fca5a5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span><strong>Connection Error:</strong> {wsError.reason || wsError.code}</span>
        </div>
      )}

      {/* Chat messages area */}
      {isDM ? (
        <>
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '12px 12px', display: 'flex', flexDirection: 'column', gap: '8px', background: '#f0f2f5' }}>
            {currentDMMessages.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', marginTop: '40px' }}>
                <UserIcon style={{ width: 36, height: 36, opacity: 0.3, margin: '0 auto 8px' }} />
                <div>Start a conversation with <strong>{activeDM.name}</strong></div>
              </div>
            )}
            {currentDMMessages.map((msg) => (
              <div key={msg.id} style={{ display: 'flex', justifyContent: msg.sender === 'you' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '80%', padding: '8px 12px', borderRadius: '10px',
                  borderTopRightRadius: msg.sender === 'you' ? '2px' : '10px',
                  borderTopLeftRadius: msg.sender !== 'you' ? '2px' : '10px',
                  background: msg.sender === 'you' ? '#dcf8c6' : '#fff',
                  color: '#1a1a1a', fontSize: '14px', lineHeight: '1.4',
                  boxShadow: '0 1px 1px rgba(0,0,0,0.06)',
                }}>
                  <div>{msg.text}</div>
                  <div style={{ fontSize: '10px', opacity: 0.5, marginTop: '3px', textAlign: 'right' }}>{msg.time}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ padding: '10px 12px', borderTop: '1px solid var(--sc-border)', background: '#f0f2f5' }}>
            <form onSubmit={handleDMSend} style={{ display: 'flex', gap: '8px' }}>
              <input
                value={dmInput}
                onChange={(e) => setDmInput(e.target.value)}
                placeholder={`Message ${activeDM.name}...`}
                style={{
                  flex: 1, padding: '10px 14px', borderRadius: '24px',
                  border: '1px solid #e5e7eb', fontSize: '14px', outline: 'none',
                  background: 'white',
                }}
              />
              <button type="submit" style={{
                width: '44px', height: '44px', borderRadius: '50%', border: 'none',
                background: '#1e8e6a', color: '#fff', fontWeight: 700, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <ChatBubbleLeftRightIcon style={{ width: 20, height: 20 }} />
              </button>
            </form>
          </div>
        </>
      ) : (
        <>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', background: '#f0f2f5' }}>
            <MessageList userPersona={userRole} activeChannelId={activeChannel?.id} />
          </div>
          <div style={{ padding: '8px 10px', borderTop: '1px solid var(--sc-border)', background: '#f0f2f5' }}>
            <MessageInput userPersona={userRole} />
          </div>
        </>
      )}
    </div>
  )
}

/* ──────────────────────────────────────────────
   Main ChatInner – switches between Desktop & Mobile
   ────────────────────────────────────────────── */
function ChatInner({ userRole, isLeader }) {
  const { wsError, setWsError, channels, activeChannel, setActiveChannel, nudgeActive, dismissNudge } = useChat()
  const [activeDM, setActiveDM] = useState(null)
  const [dmMessages, setDmMessages] = useState({})
  const [dmInput, setDmInput] = useState('')
  const isMobile = useIsMobile()

  /* Mobile: null = show channel list, non-null = show chat */
  const [mobileView, setMobileView] = useState('list') // 'list' | 'chat'

  const handleChannelSelect = (channel) => {
    setActiveChannel(channel)
    setActiveDM(null)
    if (isMobile) setMobileView('chat')
  }

  const handleDMSelect = (member) => {
    setActiveDM(member)
    setActiveChannel(null)
    if (isMobile) setMobileView('chat')
  }

  const handleMobileBack = () => {
    setMobileView('list')
  }

  const handleDMSend = (e) => {
    e.preventDefault()
    if (!dmInput.trim() || !activeDM) return
    const msgs = dmMessages[activeDM.id] || []
    setDmMessages({
      ...dmMessages,
      [activeDM.id]: [...msgs, { id: Date.now(), text: dmInput, sender: 'you', time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) }]
    })
    setDmInput('')
  }

  const currentDMMessages = activeDM ? (dmMessages[activeDM.id] || []) : []

  /* ─── MOBILE LAYOUT ─── */
  if (isMobile) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {mobileView === 'list' ? (
          <MobileChannelList
            channels={channels}
            onSelectChannel={handleChannelSelect}
            isLeader={isLeader}
            onSelectDM={handleDMSelect}
          />
        ) : (
          <MobileChatView
            userRole={userRole}
            activeDM={activeDM}
            activeChannel={activeChannel}
            onBack={handleMobileBack}
            dmMessages={dmMessages}
            setDmMessages={setDmMessages}
            dmInput={dmInput}
            setDmInput={setDmInput}
          />
        )}
      </div>
    )
  }

  /* ─── DESKTOP LAYOUT (unchanged side-by-side) ─── */
  return (
    <div className="sc-chat-app-layout" style={{ display: 'flex', flex: 1, minHeight: 0, background: 'white', borderRadius: '10px', overflow: 'hidden', boxShadow: 'var(--sc-shadow)' }}>
      {/* Vertical Channel Rail */}
      <div className="sc-chat-app-rail" style={{ width: '220px', background: '#f8fafc', borderRight: '1px solid var(--sc-border)', display: 'flex', flexDirection: 'column', paddingTop: '20px', overflowY: 'auto' }}>
        <div style={{ padding: '0 20px 12px', fontSize: '11px', fontWeight: 800, color: 'var(--sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          Circle Channels
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {channels.map((channel) => {
            const isActive = !activeDM && activeChannel?.id === channel.id
            return (
              <button
                key={channel.id}
                onClick={() => handleChannelSelect(channel)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '10px 20px', fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--sc-green-dark)' : 'var(--sc-text-muted)',
                  background: isActive ? 'var(--sc-green-bg)' : 'transparent',
                  border: 'none',
                  borderLeft: isActive ? '4px solid var(--sc-green)' : '4px solid transparent',
                  cursor: 'pointer', textAlign: 'left', transition: 'background 0.2s'
                }}
              >
                <HashtagIcon style={{ width: 16, height: 16, opacity: 0.7 }} />
                {channel.name}
              </button>
            )
          })}
        </div>

        {/* DM Channels — Leader Only */}
        {isLeader && (
          <>
            <div style={{ padding: '20px 20px 12px', fontSize: '11px', fontWeight: 800, color: '#f08c3b', textTransform: 'uppercase', letterSpacing: '0.8px', borderTop: '1px solid var(--sc-border)', marginTop: '12px' }}>
              Direct Messages
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {DM_MEMBERS.map((member) => {
                const isDMActive = activeDM?.id === member.id
                return (
                  <button
                    key={member.id}
                    onClick={() => handleDMSelect(member)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '10px 20px', fontSize: '13px',
                      fontWeight: isDMActive ? 600 : 500,
                      color: isDMActive ? '#f08c3b' : 'var(--sc-text-muted)',
                      background: isDMActive ? '#fff7ed' : 'transparent',
                      border: 'none',
                      borderLeft: isDMActive ? '4px solid #f08c3b' : '4px solid transparent',
                      cursor: 'pointer', textAlign: 'left', transition: 'background 0.2s'
                    }}
                  >
                    <div style={{ position: 'relative' }}>
                      <div style={{
                        width: '24px', height: '24px', borderRadius: '50%',
                        background: isDMActive ? '#f08c3b' : '#e8f5f0',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '9px', fontWeight: 700,
                        color: isDMActive ? '#fff' : 'var(--sc-green-dark)',
                      }}>{member.initials}</div>
                      {member.online && (
                        <div style={{ position: 'absolute', bottom: -1, right: -1, width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e', border: '2px solid #f8fafc' }}></div>
                      )}
                    </div>
                    {member.name}
                  </button>
                )
              })}
            </div>
          </>
        )}
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', minWidth: 0, minHeight: 0 }}>
        {wsError?.code === 'message_blocked' && (
          <InterventionOverlay 
            type="block" 
            message={wsError.reason} 
            onDismiss={() => setWsError(null)} 
          />
        )}

        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--sc-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: activeDM ? '#f08c3b' : '#22c55e' }} />
          <div style={{ fontSize: '15px', fontWeight: 700 }}>
            {activeDM ? `${activeDM.name}` : `#${activeChannel?.name || 'General Chat'}`}
          </div>
          {activeDM && (
            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: '#fff7ed', color: '#f08c3b', fontWeight: 600, marginLeft: '8px' }}>
              Private
            </span>
          )}
          {!activeDM && (
            <div style={{ position: 'absolute', top: 12, right: 20 }}>
              <RaiseHandButton userPersona={userRole} />
            </div>
          )}
        </div>

        {/* DM View or Circle Chat */}
        {activeDM ? (
          <>
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {currentDMMessages.length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', marginTop: '40px' }}>
                  <UserIcon style={{ width: 40, height: 40, opacity: 0.3, margin: '0 auto 8px' }} />
                  <div>Start a private conversation with <strong>{activeDM.name}</strong></div>
                  <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.6 }}>Messages here are private between you and this member.</div>
                </div>
              )}
              {currentDMMessages.map((msg) => (
                <div key={msg.id} style={{ display: 'flex', justifyContent: msg.sender === 'you' ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: '70%', padding: '10px 14px', borderRadius: '12px',
                    background: msg.sender === 'you' ? 'var(--sc-green)' : '#f3f4f6',
                    color: msg.sender === 'you' ? '#fff' : '#1a1a1a',
                    fontSize: '13px', lineHeight: '1.5',
                  }}>
                    <div>{msg.text}</div>
                    <div style={{ fontSize: '10px', opacity: 0.6, marginTop: '4px', textAlign: 'right' }}>{msg.time}</div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ padding: '16px 20px', borderTop: '1px solid var(--sc-border)' }}>
              <form onSubmit={handleDMSend} style={{ display: 'flex', gap: '10px' }}>
                <input
                  value={dmInput}
                  onChange={(e) => setDmInput(e.target.value)}
                  placeholder={`Message ${activeDM.name}...`}
                  style={{
                    flex: 1, padding: '10px 14px', borderRadius: '10px',
                    border: '1px solid var(--sc-border)', fontSize: '14px', outline: 'none',
                  }}
                />
                <button type="submit" style={{
                  padding: '10px 20px', borderRadius: '10px', border: 'none',
                  background: '#f08c3b', color: '#fff', fontWeight: 700, cursor: 'pointer',
                }}>Send</button>
              </form>
            </div>
          </>
        ) : (
          <>
            <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <MessageList userPersona={userRole} activeChannelId={activeChannel?.id} />
            </div>
            <div style={{ padding: '16px 20px', borderTop: '1px solid var(--sc-border)' }}>
              <MessageInput userPersona={userRole} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function SCChatMainView({ circleId, userRole, isLeader = false }) {
  return (
    <div className="sc-chat-main-container" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <ChatProvider circleId={circleId} userRole={userRole}>
        <ChatInner userRole={userRole} isLeader={isLeader} />
      </ChatProvider>
    </div>
  )
}
