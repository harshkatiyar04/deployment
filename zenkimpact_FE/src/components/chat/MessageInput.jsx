import { useRef, useState } from 'react'
import { PaperAirplaneIcon, PaperClipIcon, FaceSmileIcon } from '@heroicons/react/24/outline'
import EmojiPicker from 'emoji-picker-react'
import { useChat } from '../../contexts/ChatContext'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAX_CHARS = 2000

export default function MessageInput({ userPersona, handRaised }) {
  const { sendMessage, activeChannel, stageActive, status } = useChat()
  const [text, setText] = useState('')
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
    setText(e.target.value.slice(0, MAX_CHARS))
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

      <div className="flex items-end gap-2">
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

        {/* Input Field */}
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
              ? 'Type a message to the circle...'
              : 'Select a channel'
          }
          className="flex-1 resize-none rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 disabled:bg-gray-50 disabled:text-gray-400 leading-relaxed transition-all"
          style={{ maxHeight: '120px', overflowY: 'auto' }}
        />

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
