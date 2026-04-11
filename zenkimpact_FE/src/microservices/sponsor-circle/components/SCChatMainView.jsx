import { useState } from 'react'
import { HashtagIcon } from '@heroicons/react/24/outline'
import { ChatProvider, useChat } from '../../../contexts/ChatContext'
import MessageList from '../../../components/chat/MessageList'
import MessageInput from '../../../components/chat/MessageInput'
import StageBar from '../../../components/chat/StageBar'
import RaiseHandButton from '../../../components/chat/RaiseHandButton'
import InterventionOverlay from '../../../components/chat/InterventionOverlay'

function ChatInner({ userRole }) {
  const { wsError, setWsError, channels, activeChannel, setActiveChannel, nudgeActive, dismissNudge } = useChat()

  return (
    <div style={{ display: 'flex', flex: 1, minHeight: 0, background: 'white', borderRadius: '10px', overflow: 'hidden', boxShadow: 'var(--sc-shadow)' }}>
      {/* Vertical Channel Rail */}
      <div style={{ width: '200px', background: '#f8fafc', borderRight: '1px solid var(--sc-border)', display: 'flex', flexDirection: 'column', paddingTop: '20px' }}>
        <div style={{ padding: '0 20px 12px', fontSize: '11px', fontWeight: 800, color: 'var(--sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          Circle Channels
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {channels.map((channel) => {
            const isActive = activeChannel?.id === channel.id
            return (
              <button
                key={channel.id}
                onClick={() => setActiveChannel(channel)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 20px',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--sc-green-dark)' : 'var(--sc-text-muted)',
                  background: isActive ? 'var(--sc-green-bg)' : 'transparent',
                  border: 'none',
                  borderLeft: isActive ? '4px solid var(--sc-green)' : '4px solid transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background 0.2s'
                }}
              >
                <HashtagIcon style={{ width: 16, height: 16, opacity: 0.7 }} />
                {channel.name}
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', minWidth: 0 }}>
        {wsError?.code === 'message_blocked' && (
          <InterventionOverlay 
            type="block" 
            message={wsError.reason} 
            onDismiss={() => setWsError(null)} 
          />
        )}

        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--sc-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#22c55e' }} />
          <div style={{ fontSize: '15px', fontWeight: 700 }}>#{activeChannel?.name || 'General Chat'}</div>
          <div style={{ position: 'absolute', top: 12, right: 20 }}>
            <RaiseHandButton userPersona={userRole} />
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <MessageList userPersona={userRole} activeChannelId={activeChannel?.id} />
        </div>

        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--sc-border)' }}>
          <MessageInput userPersona={userRole} />
        </div>
      </div>
    </div>
  )
}

export default function SCChatMainView({ circleId, userRole }) {
  return (
    <div className="sc-chat-main-container" style={{ display: 'flex', flex: 1, minHeight: 0 }}>
      <ChatProvider circleId={circleId}>
        <ChatInner userRole={userRole} />
      </ChatProvider>
    </div>
  )
}
