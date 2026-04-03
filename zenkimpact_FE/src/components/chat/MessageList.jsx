import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import { useChat } from '../../contexts/ChatContext'

export default function MessageList({ userPersona, activeChannelId }) {
  const { messages, nudgeActive, dismissNudge, hasMore, isLoadingMore, loadMoreHistory } = useChat()
  const bottomRef = useRef(null)
  const topSentinelRef = useRef(null)
  const prevMessagesLength = useRef(0)
  const listContainerRef = useRef(null)

  const channelMessages = activeChannelId
    ? messages.filter((m) => m.channel_id === activeChannelId)
    : messages

  useEffect(() => {
    if (!hasMore || isLoadingMore || !topSentinelRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMoreHistory(activeChannelId)
        }
      },
      { threshold: 1.0 }
    )

    observer.observe(topSentinelRef.current)
    return () => observer.disconnect()
  }, [activeChannelId, hasMore, isLoadingMore, loadMoreHistory])

  useEffect(() => {
    if (channelMessages.length > prevMessagesLength.current) {
      const isInitialLoad = prevMessagesLength.current === 0
      const isNewMsgAtBottom = channelMessages[channelMessages.length - 1].id !== messages[messages.length - 1]?.id

      if (isInitialLoad || isNewMsgAtBottom) {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }
    }
    prevMessagesLength.current = channelMessages.length
  }, [channelMessages.length, messages])

  return (
    <div ref={listContainerRef} className="flex-1 overflow-y-auto flex flex-col min-h-0 relative">
      {nudgeActive && (
        <div
          role="alert"
          className="sticky top-2 z-[100] mx-4 mt-1 flex items-center justify-between gap-3 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg px-4 py-3 text-sm shadow-md"
        >
          <span>
            ⚠️ This message may contain personal information. Please keep all conversations on-platform.
          </span>
          <button
            onClick={dismissNudge}
            className="text-yellow-700 hover:text-yellow-900 font-medium shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {hasMore && (
        <div ref={topSentinelRef} className="h-4 w-full flex items-center justify-center py-8">
          {isLoadingMore && (
            <div className="flex items-center gap-2 text-xs font-bold text-teal-600 bg-teal-50/50 px-4 py-2 rounded-full border border-teal-100 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
              Loading History...
            </div>
          )}
        </div>
      )}

      {channelMessages.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          No messages yet. Say hello!
        </div>
      )}

      <div className="py-2">
        {channelMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} userPersona={userPersona} />
        ))}
      </div>

      <div ref={bottomRef} />
    </div>
  )
}
