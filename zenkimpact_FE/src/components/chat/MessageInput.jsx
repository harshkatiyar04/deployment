import { useRef, useState } from 'react'
import { PaperAirplaneIcon, PaperClipIcon, FaceSmileIcon } from '@heroicons/react/24/outline'
import EmojiPicker from 'emoji-picker-react'
import { useChat } from '../../contexts/ChatContext'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAX_CHARS = 2000

export default function MessageInput({ userPersona, handRaised }) {
  const { sendMessage, activeChannel, stageActive, status, members } = useChat()
  const [text, setText] = useState('')
  const [showMentions, setShowMentions] = useState(false)
  const [mentionFilter, setMentionFilter] = useState('')
  const [uploading, setUploading] = useState(false)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const fileInputRef = useRef(null)

  const stageBlocked = stageActive && userPersona === 'student' && !handRaised
  const wsConnected = status === 'open'
  const disabled = stageBlocked || !wsConnected || !activeChannel

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    sendMessage(activeChannel.id, trimmed, null)
    setText('')
    setShowEmojiPicker(false)
  }

  const handleChange = (e) => {
    const val = e.target.value.slice(0, MAX_CHARS)
    setText(val)
    
    // Simple Mention Trigger Logic
    const lastChar = val[e.target.selectionStart - 1]
    const textBeforeCursor = val.slice(0, e.target.selectionStart)
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/)
    
    if (mentionMatch) {
      setShowMentions(true)
      setMentionFilter(mentionMatch[1].toLowerCase())
    } else {
      setShowMentions(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !activeChannel) return

    const token = localStorage.getItem('chat_token')
    if (!token) return

    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(
        `${API_BASE}/chat/upload?token=${encodeURIComponent(token)}`,
        { method: 'POST', body: form }
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(err.detail || 'Upload failed')
        return
      }
      const { url } = await res.json()
      sendMessage(activeChannel.id, text.trim() || null, url)
      setText('')
    } catch (err) {
      console.error('[MessageInput] Upload error', err)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="bg-white">
      {stageBlocked && (
        <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-3 py-1.5 mb-2">
          Stage is active — raise your hand to speak.
        </p>
      )}
      {!wsConnected && (
        <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-1.5 mb-2">
          Reconnecting to chat…
        </p>
      )}

      <div className="flex items-center gap-1">
        {/* Emoji Picker */}
        <div className="relative">
          <button
            id="chat-emoji-btn"
            type="button"
            disabled={disabled}
            onClick={() => setShowEmojiPicker((prev) => !prev)}
            className="p-2 text-gray-400 hover:text-teal-600 disabled:opacity-40 transition-colors"
            title="Add Emoji"
          >
            <FaceSmileIcon className="w-5 h-5" />
          </button>

          {showEmojiPicker && (
            <div className="absolute bottom-12 left-0 z-50 shadow-2xl rounded-xl overflow-hidden border border-gray-100">
              <EmojiPicker
                onEmojiClick={(e) => setText((prev) => prev + e.emoji)}
                theme="light"
                lazyLoadEmojis={true}
              />
            </div>
          )}
        </div>

        {/* File Attach */}
        <button
          id="chat-file-attach"
          type="button"
          disabled={disabled || uploading}
          onClick={() => fileInputRef.current?.click()}
          className="p-2 text-gray-400 hover:text-teal-600 disabled:opacity-40 transition-colors"
          title="Attach file (image or PDF, max 5MB)"
        >
          <PaperClipIcon className="w-5 h-5" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Input Field + Mentions Wrapper */}
        <div className="flex-1 relative">
          {/* Mention Suggestions Popup */}
          {showMentions && (
            <div className="absolute bottom-full left-0 mb-3 w-72 bg-white rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.15)] border border-gray-100 overflow-hidden z-[1000] animate-in slide-in-from-bottom-2 duration-200">
              <div className="px-4 py-3 bg-gray-50 border-bottom border-gray-100 flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Mention Member</span>
                <span className="text-[10px] text-teal-600 font-medium bg-teal-50 px-1.5 py-0.5 rounded">@{mentionFilter || '...'}</span>
              </div>
              <div className="max-h-60 overflow-y-auto">
                {[ { nickname: 'Kia', id: 'kia-bot', avatar_key: 'avatar_kia', isBot: true }, ...members]
                  .filter(m => m.nickname.toLowerCase().includes(mentionFilter))
                  .map((member) => (
                    <button
                      key={member.id || member.persona_id}
                      type="button"
                      onClick={() => {
                        const beforeMention = text.slice(0, text.lastIndexOf('@'))
                        setText(beforeMention + '@' + member.nickname + ' ')
                        setShowMentions(false)
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-teal-50 transition-colors text-left group"
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] text-white font-bold shrink-0 shadow-sm ${member.isBot ? 'bg-gradient-to-br from-teal-500 to-emerald-600' : 'bg-gray-300'}`}>
                        {member.isBot ? (
                          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                        ) : (
                          member.nickname.slice(0, 2).toUpperCase()
                        )}
                      </div>
                      <div className="flex flex-col">
                        <span className={`text-sm font-semibold ${member.isBot ? 'text-teal-700' : 'text-gray-700'} group-hover:text-teal-800`}>
                          {member.nickname}
                        </span>
                        {member.isBot && <span className="text-[10px] text-teal-500 font-medium">AI Mentor</span>}
                      </div>
                    </button>
                  ))
                }
                {members.filter(m => m.nickname.toLowerCase().includes(mentionFilter)).length === 0 && mentionFilter && (
                   <div className="px-4 py-6 text-center text-gray-400 text-xs italic">
                      No members found matching "@{mentionFilter}"
                   </div>
                )}
              </div>
            </div>
          )}

          <textarea
            id="chat-message-input"
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={
              stageBlocked
                ? 'Stage is active — raise your hand to speak'
                : activeChannel
                ? 'Type a message (use @ to tag)...'
                : 'Select a channel'
            }
            className="w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 disabled:bg-gray-50 disabled:text-gray-400 leading-relaxed transition-all"
            style={{ maxHeight: '120px', overflowY: 'auto' }}
          />
        </div>

        {/* Send Button */}
        <button
          id="chat-send-btn"
          type="button"
          disabled={!text.trim() || disabled}
          onClick={handleSend}
          className="px-5 py-2.5 bg-teal-600 text-white rounded-lg text-sm font-semibold hover:bg-teal-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors shrink-0 shadow-sm"
          title="Send (Enter)"
        >
          Send
        </button>
      </div>

      <div className="flex justify-end mt-1">
        <span className={`text-xs ${text.length > MAX_CHARS * 0.9 ? 'text-red-500' : 'text-gray-300'}`}>
          {text.length}/{MAX_CHARS}
        </span>
      </div>
    </div>
  )
}
