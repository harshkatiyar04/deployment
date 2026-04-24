import { useState, useEffect, useRef } from 'react'
import { ChevronDownIcon } from '@heroicons/react/24/solid'
import MessageBubble from './MessageBubble'
import { useChat } from '../../contexts/ChatContext'

export default function MessageList({ userPersona, activeChannelId }) {
  const { messages, nudgeActive, dismissNudge, hasMore, isLoadingMore, loadMoreHistory, kiaTyping } = useChat()
  const bottomRef = useRef(null)
  const topSentinelRef = useRef(null)
  const prevMessagesLength = useRef(0)
  const listContainerRef = useRef(null)
  const [showScrollDown, setShowScrollDown] = useState(false)

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

  // Handle auto-scroll to bottom
  useEffect(() => {
    if (channelMessages.length > prevMessagesLength.current) {
      const isInitialLoad = prevMessagesLength.current === 0
      if (isInitialLoad) {
        // Instant scroll for first load to avoid "stopping mid-way"
        bottomRef.current?.scrollIntoView({ behavior: 'auto' })
      } else {
        // Smooth scroll for new incoming messages
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }
    }
    prevMessagesLength.current = channelMessages.length
  }, [channelMessages.length])

  // Track scroll position to show/hide the "Scroll Down" button
  const handleScroll = () => {
    if (!listContainerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = listContainerRef.current
    const isAtBottom = scrollHeight - scrollTop <= clientHeight + 100
    setShowScrollDown(!isAtBottom)
  }

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div 
      ref={listContainerRef} 
      onScroll={handleScroll}
      className="flex-1 min-h-0 overflow-y-auto overscroll-contain touch-pan-y flex flex-col relative scroll-smooth pr-1 chat-custom-scrollbar"
    >
      {/* Scroll to Bottom Button */}
      {showScrollDown && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 right-4 z-50 p-2 bg-teal-600 text-white rounded-full shadow-lg hover:bg-teal-700 transition-all active:scale-95 animate-bounce"
          title="Scroll to latest messages"
        >
          <ChevronDownIcon className="w-4 h-4" />
        </button>
      )}

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

      {channelMessages.length === 0 && !kiaTyping && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          No messages yet. Say hello!
        </div>
      )}

      <div className="py-1">
        {channelMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} userPersona={userPersona} />
        ))}

        {/* Kia Typing Indicator */}
        {kiaTyping && (
          <div className="flex items-start gap-2 px-2 py-1 animate-in fade-in slide-in-from-bottom-2 duration-300">
             <div className="w-7 h-7 rounded-full bg-[#DCFCE7] flex items-center justify-center text-[9px] text-[#166534] font-bold shrink-0 shadow-sm border border-black/5">
                AI
             </div>
             <div className="bg-[#F0FDF4] border border-[#DCFCE7] rounded-2xl rounded-tl-none px-3 py-1.5 shadow-sm">
                <div className="flex items-center gap-1.5">
                   <span className="text-[14px] font-medium text-[#115E59]">Kia is typing</span>
                   <div className="flex gap-0.5">
                      <span className="w-1 h-1 bg-teal-500 rounded-full animate-pulse" />
                      <span className="w-1 h-1 bg-teal-500 rounded-full animate-pulse delay-75" />
                      <span className="w-1 h-1 bg-teal-500 rounded-full animate-pulse delay-150" />
                   </div>
                </div>
             </div>
          </div>
        )}
      </div>

      <div ref={bottomRef} />
    </div>
  )
}
