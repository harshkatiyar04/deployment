import { useCallback, useEffect, useRef, useState } from 'react'

const WS_CLOSE_CODES = {
  4000: 'auth_failed',
  4001: 'not_enrolled',
  4003: 'not_a_member',
  4004: 'consent_required',
  4005: 'banned',
}

const BACKOFF_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000]

export function useCircleChat(circleId) {
  const [status, setStatus] = useState('idle') // 'idle'|'connecting'|'open'|'closed'|'error'
  const [messages, setMessages] = useState([])
  const [handsRaised, setHandsRaised] = useState([]) // array of { persona_id, nickname, avatar_key }
  const [nudgeActive, setNudgeActive] = useState(false)
  const [wsError, setWsError] = useState(null) // null | { code: string, reason: string }
  const [presence, setPresence] = useState({}) // { persona_id: 'online'|'offline' }

  const [personaId, setPersonaId] = useState(null)
  const [hasMore, setHasMore] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  const wsRef = useRef(null)
  const backoffRef = useRef(0)
  const reconnectTimerRef = useRef(null)
  const circleIdRef = useRef(circleId)

  // Keep ref in sync so reconnect closure uses latest circleId
  useEffect(() => { circleIdRef.current = circleId }, [circleId])

  const scheduleReconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current)
    const delay = BACKOFF_DELAYS_MS[Math.min(backoffRef.current, BACKOFF_DELAYS_MS.length - 1)]
    backoffRef.current += 1
    reconnectTimerRef.current = setTimeout(() => {
      connect(circleIdRef.current) // eslint-disable-line no-use-before-define
    }, delay)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const connect = useCallback((cid) => {
    if (!cid) return

    const token = localStorage.getItem('chat_token')
    if (!token) {
      setWsError({ code: 'auth_failed', reason: 'No chat token in localStorage' })
      setStatus('error')
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = import.meta.env.VITE_API_WS_HOST || window.location.host
    const url = `${protocol}://${host}/ws/circle/${cid}?token=${encodeURIComponent(token)}`

    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('open')
      backoffRef.current = 0 // reset backoff on successful connect
      setWsError(null)
    }

    ws.onclose = (event) => {
      setStatus('closed')
      wsRef.current = null

      const errorKey = WS_CLOSE_CODES[event.code]
      if (errorKey) {
        // Hard errors — do NOT reconnect
        // Preserve existing detailed error (e.g. from 'error' message) if it exists
        setWsError((prev) => (prev?.code === errorKey ? prev : { code: errorKey, reason: `Connection closed: ${errorKey}` }))
        return
      }
      // Soft close (network blip etc.) — schedule reconnect
      scheduleReconnect()
    }

    ws.onerror = (err) => {
      console.error('[useCircleChat] WS error', err)
      setWsError({ code: 'connection_failed', reason: 'Could not connect to the chat server. Check if your backend is running and your .env URLs are correct.' })
      setStatus('error')
      ws.close()
    }

    ws.onmessage = (event) => {
      let envelope
      try {
        envelope = JSON.parse(event.data)
      } catch {
        console.warn('[useCircleChat] Could not parse WS message', event.data)
        return
      }

      switch (envelope.type) {
        case 'welcome':
          setPersonaId(envelope.payload.persona_id)
          break

        case 'new_message':
          setMessages((prev) => [...prev, { ...envelope.payload, hidden: false }])
          break

        case 'hand_raised':
          setHandsRaised((prev) => {
            if (prev.find((h) => h.persona_id === envelope.payload.persona_id)) return prev
            return [...prev, envelope.payload]
          })
          break

        case 'hand_lowered':
          setHandsRaised((prev) =>
            prev.filter((h) => h.persona_id !== envelope.payload.persona_id)
          )
          break

        case 'message_hidden':
          setMessages((prev) =>
            prev.map((m) =>
              m.id === envelope.payload.message_id ? { ...m, hidden: true } : m
            )
          )
          break

        case 'safety_nudge':
          setNudgeActive(true)
          break

        case 'message_deleted':
          setMessages((prev) =>
            prev.map((m) =>
              m.id === envelope.payload.message_id
                ? { ...m, deleted_at: new Date().toISOString(), content_text: null, media_url: null }
                : m
            )
          )
          break
        
        case 'presence_update':
          setPresence((prev) => ({
            ...prev,
            [envelope.payload.persona_id]: envelope.payload.status,
          }))
          break
          

        case 'pong':
          // no-op — connection keepalive acknowledgement
          break

        case 'error':
          console.error('[useCircleChat] Server error event', envelope.payload)
          setWsError(envelope.payload)
          break

        default:
          console.warn('[useCircleChat] Unknown envelope type', envelope.type)
      }
    }
  }, [scheduleReconnect])

  // Connect when circleId changes; disconnect on unmount
  useEffect(() => {
    if (circleId) connect(circleId)
    return () => {
      clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect on intentional close
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [circleId, connect])

  // --- Message Actions ---

  const sendMessage = useCallback((channelId, contentText, mediaUrl = null) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({
      type: 'send_message',
      payload: { channel_id: channelId, content_text: contentText, media_url: mediaUrl },
    }))
  }, [])

  const raiseHand = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'raise_hand', payload: {} }))
  }, [])

  const lowerHand = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'lower_hand', payload: {} }))
  }, [])

  const triggerSOS = useCallback((messageId) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({
      type: 'sos_report',
      payload: { message_id: messageId },
    }))
  }, [])

  const deleteMessage = useCallback((messageId) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({
      type: 'delete_message',
      payload: { message_id: messageId },
    }))
  }, [])


  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current)
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('closed')
  }, [])

  const dismissNudge = useCallback(() => setNudgeActive(false), [])

  const loadHistory = useCallback(async (channelId) => {
    if (!channelId) return
    const token = localStorage.getItem('chat_token')
    if (!token) return

    try {
      const apiHost = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiHost}/chat/messages/${channelId}?token=${encodeURIComponent(token)}&limit=50`)
      if (!response.ok) return
      const history = await response.json()
      
      setHasMore(history.length === 50)
      setMessages(history.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)))
    } catch (err) {
      console.error('[useCircleChat] Failed to load history', err)
    }
  }, [])

  const loadMoreHistory = useCallback(async (channelId) => {
    if (!channelId || !hasMore || isLoadingMore) return
    const token = localStorage.getItem('chat_token')
    if (!token) return

    setIsLoadingMore(true)
    try {
      const oldestMsg = messages[0]
      const before = oldestMsg ? oldestMsg.created_at : null
      if (!before) {
        setHasMore(false)
        return
      }

      const apiHost = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiHost}/chat/messages/${channelId}?token=${encodeURIComponent(token)}&before=${encodeURIComponent(before)}&limit=100`)
      if (!response.ok) return
      const olderHistory = await response.json()
      
      if (olderHistory.length < 100) {
        setHasMore(false)
      }

      if (olderHistory.length > 0) {
        setMessages((prev) => {
          const existingIds = new Set(prev.map(m => m.id))
          const newMessages = olderHistory.filter(m => !existingIds.has(m.id))
          return [...newMessages, ...prev].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
        })
      }
    } catch (err) {
      console.error('[useCircleChat] Failed to load more history', err)
    } finally {
      setIsLoadingMore(false)
    }
  }, [hasMore, isLoadingMore, messages])

  const loadMembers = useCallback(async () => {
    if (!circleId) return
    const token = localStorage.getItem('chat_token')
    if (!token) return

    try {
      const apiHost = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiHost}/chat/circle/${circleId}/members?token=${encodeURIComponent(token)}`)
      if (!response.ok) return
      return await response.json()
    } catch (err) {
      console.error('[useCircleChat] Failed to load members', err)
      return []
    }
  }, [circleId])

  return {
    status,
    messages,
    handsRaised,
    nudgeActive,
    wsError,
    setWsError,
    presence,
    personaId,
    hasMore,
    isLoadingMore,
    sendMessage,
    raiseHand,
    lowerHand,
    triggerSOS,
    deleteMessage,
    disconnect,
    dismissNudge,
    loadHistory,
    loadMoreHistory,
    loadMembers,
  }
}
