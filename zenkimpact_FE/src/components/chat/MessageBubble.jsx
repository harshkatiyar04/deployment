/**
 * MessageBubble — renders a single chat message.
 * Theme: Clean, modern layout matching the Zenk reference design.
 * - Name + timestamp shown BELOW the bubble
 * - Received: white bg, teal left accent
 * - Sent: light beige bg, right-aligned
 * - SOS/Delete on hover
 * - NEVER shows real name or user_id
 */
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { ExclamationTriangleIcon, TrashIcon } from '@heroicons/react/24/outline'
import PersonaAvatar from './PersonaAvatar'
import { useChat } from '../../contexts/ChatContext'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function formatDateTime(isoString) {
  if (!isoString) return 'No time provided'
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return String(isoString) // fallback to raw string if JS Date parsing fails completely
    const date = d.toLocaleDateString([], { day: 'numeric', month: 'short' })
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    return `${date}, ${time}`
  } catch {
    return String(isoString)
  }
}

export default function MessageBubble({ message, userPersona }) {
  const { triggerSOS, deleteMessage, personaId } = useChat()
  const [hovered, setHovered] = useState(false)
  const [isZoomed, setIsZoomed] = useState(false)

  const isOwner = personaId && message.gamified_persona_id === personaId
  const isDeleted = !!message.deleted_at
  const isStudent = userPersona === 'student'

  if (message.hidden) {
    return (
      <div className="flex items-center gap-2 px-6 py-2 text-xs text-gray-400 italic">
        <ExclamationTriangleIcon className="w-4 h-4 text-yellow-400" />
        This message has been hidden by a safety report.
      </div>
    )
  }

  return (
    <div
      id={`msg-${message.id}`}
      className={`group relative px-6 py-1.5 transition-colors ${isOwner ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Bubble Row: Avatar + Bubble */}
      <div className={`flex items-start gap-3 max-w-[75%] ${isOwner ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className="shrink-0 mt-0.5">
          <PersonaAvatar nickname={message.persona_nickname} avatarKey={message.avatar_key} size="md" />
        </div>

        <div className={`flex flex-col ${isOwner ? 'items-end' : 'items-start'}`}>
          {isDeleted ? (
            <p className="text-sm text-gray-400 italic bg-gray-50 px-4 py-2 rounded-lg border border-dashed border-gray-200">
              This message was deleted by the sender.
            </p>
          ) : (
            <>
              {/* Text Bubble */}
              {message.content_text && (
                <div className={`relative text-sm break-words whitespace-pre-wrap leading-relaxed px-4 py-2.5 shadow-sm ${
                  isOwner
                    ? 'bg-[#FFF1E1] border border-[#F5E6CE] text-gray-800 rounded-2xl rounded-br-sm'
                    : message.persona_nickname === 'Kia'
                      ? 'bg-[#E9F7F5] border border-[#B2DFD8] text-[#115E59] rounded-2xl rounded-bl-sm opacity-95 transition-all'
                      : 'bg-white border border-gray-100 text-gray-800 rounded-2xl rounded-bl-sm'
                }`}>
                  {(() => {
                    const text = message.content_text
                    const kiaKeyword = "Kia suggests:"
                    const lowerText = text.toLowerCase()
                    const lowerKeyword = kiaKeyword.toLowerCase()
                    
                    if (message.persona_nickname === 'Kia' && lowerText.includes(lowerKeyword)) {
                      const parts = text.split(new RegExp(kiaKeyword, 'i'))
                      const mainText = parts[0].trim()
                      const suggestion = parts.slice(1).join(kiaKeyword).trim()
                      
                      return (
                        <div className="flex flex-col gap-2">
                          {mainText && (
                            <span className="opacity-90">
                              {mainText.split(/(@\w+)/g).map((part, i) => 
                                part.startsWith('@') ? <strong key={i} className="text-[#0D9488]">{part}</strong> : part
                              )}
                            </span>
                          )}
                          <div className="bg-[#DCFCE7] border border-[#BBF7D0] rounded-xl px-3 py-2 shadow-sm mt-0.5">
                            <div className="text-[10px] font-bold text-[#115E59] mb-0.5 uppercase tracking-wide opacity-80">
                              Kia suggests:
                            </div>
                            <div className="text-[13px] text-[#14532D] font-medium leading-relaxed">
                              {suggestion}
                            </div>
                          </div>
                        </div>
                      )
                    }
                    
                    // Normal text mention highlighting
                    return text.split(/(@\w+)/g).map((part, i) => 
                      part.startsWith('@') ? <strong key={i} className="text-[#0D9488] font-bold">{part}</strong> : part
                    )
                  })()}
                </div>
              )}

              {/* Media */}
              {message.media_url && (
                <div className="mt-1.5">
                  {(() => {
                    const fullUrl = message.media_url.startsWith('/')
                      ? `${API_BASE}${message.media_url}`
                      : message.media_url

                    return /\.(jpg|jpeg|png|webp)$/i.test(fullUrl) ? (
                      <>
                        <img
                          src={fullUrl}
                          alt="attachment"
                          onClick={() => setIsZoomed(true)}
                          className="max-w-xs rounded-lg border border-gray-200 cursor-zoom-in hover:opacity-95 transition-opacity"
                        />
                        {isZoomed && createPortal(
                          <div
                            className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/85 backdrop-blur-md p-4 cursor-zoom-out animate-in fade-in duration-300"
                            onClick={() => setIsZoomed(false)}
                          >
                            <img
                              src={fullUrl}
                              alt="attachment-zoom"
                              className="max-h-full max-w-full rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-white/20 animate-in zoom-in-95 duration-300"
                            />
                            <button
                              className="absolute top-6 right-6 text-white bg-white/10 hover:bg-white/20 p-3 rounded-full backdrop-blur-md transition-all hover:scale-110 active:scale-90"
                              onClick={(e) => { e.stopPropagation(); setIsZoomed(false); }}
                            >
                              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>,
                          document.body
                        )}
                      </>
                    ) : (
                      <a
                        href={fullUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-teal-600 underline text-sm hover:text-teal-700"
                      >
                        📎 Attachment
                      </a>
                    )
                  })()}
                </div>
              )}
            </>
          )}

          {/* Meta: Name · Timestamp (BELOW the bubble) */}
          <div className={`flex items-center gap-1.5 mt-1 px-1 ${isOwner ? 'flex-row-reverse' : 'flex-row'}`}>
            <span className="text-[11px] font-medium text-gray-400">
              {message.persona_nickname}
            </span>
            <span className="text-[11px] text-gray-300">·</span>
            <span className="text-[11px] text-gray-400">
              {formatDateTime(message.created_at)}
            </span>
            {message.shield_action === 'warn' && (
              <>
                <span className="text-[11px] text-gray-300">·</span>
                <span className="text-[10px] text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded font-medium">⚠ reviewed</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Action buttons on hover (positioned to avoid bubble overlap) */}
      <div className={`absolute top-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-10 ${isOwner ? 'left-1' : 'right-1'}`}>
        {isOwner && !isDeleted && (
          <button
            id={`del-${message.id}`}
            onClick={() => {
              if (window.confirm("Are you sure you want to delete this message?")) {
                deleteMessage(message.id)
              }
            }}
            title="Delete your message"
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 bg-white border border-gray-200 rounded-md px-2 py-1 shadow-sm transition-colors"
          >
            <TrashIcon className="w-3.5 h-3.5" />
            Delete
          </button>
        )}

        {!isOwner && !isDeleted && (
          <button
            id={`sos-${message.id}`}
            onClick={() => triggerSOS(message.id)}
            title="Report this message"
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 bg-white border border-red-200 rounded-md px-2 py-1 shadow-sm transition-colors"
          >
            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
            Report
          </button>
        )}
      </div>
    </div>
  )
}
