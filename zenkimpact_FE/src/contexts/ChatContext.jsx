import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useCircleChat } from '../hooks/useCircleChat'

const ChatContext = createContext(null)

export const useChat = () => {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within a ChatProvider')
  return ctx
}

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
  if (hostname.includes('vercel.app') || hostname.includes('zenk') || hostname.includes('railway.app')) {
    return 'https://deployment-production-27bd.up.railway.app';
  }
  return 'http://localhost:8000';
};

const API_BASE = getApiBase();

export const ChatProvider = ({ circleId, userRole = 'sponsor', children }) => {
  const chat = useCircleChat(circleId, userRole)

  const [channels, setChannels] = useState([])
  const [activeChannel, setActiveChannel] = useState(null)
  const [stageActive, setStageActive] = useState(false)
  const [channelError, setChannelError] = useState(null)

  const fetchChannels = useCallback(async () => {
    if (!circleId) return
    const token = localStorage.getItem('chat_token')
    if (!token) return
    try {
      const res = await fetch(
        `${API_BASE}/chat/channels/${circleId}?token=${encodeURIComponent(token)}`
      )
      if (!res.ok) throw new Error(`Channels fetch failed: ${res.status}`)
      const data = await res.json()
      setChannels(data)
      if (data && data.length > 0 && !activeChannel) {
        setActiveChannel(data[0])
      }
    } catch (err) {
      console.error('[ChatContext] Failed to fetch channels', err)
      setChannelError(err.message)
    }
  }, [circleId, activeChannel])

  useEffect(() => {
    if (chat.status === 'open') {
      fetchChannels()
    }
  }, [chat.status, fetchChannels])

  useEffect(() => {
    if (activeChannel?.id) {
      chat.loadHistory(activeChannel.id)
    }
  }, [activeChannel?.id, chat.status]) // also run on reconnect if channel is already active

  const value = {
    ...chat,
    channels,
    activeChannel,
    setActiveChannel,
    channelError,
    stageActive,
    setStageActive,
    fetchChannels,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}
