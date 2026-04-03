/**
 * ChannelSidebar — lists chat channels for the active circle.
 */
import { HashtagIcon } from '@heroicons/react/24/outline'
import { useChat } from '../../contexts/ChatContext'

export default function ChannelSidebar() {
  const { channels, activeChannel, setActiveChannel } = useChat()

  if (channels.length === 0) {
    return (
      <div className="w-48 bg-white text-gray-400 flex flex-col p-4 border-r border-gray-100">
        <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mb-3">Channels</p>
        <p className="text-xs text-gray-400 italic">No channels yet</p>
      </div>
    )
  }

  return (
    <div className="w-48 bg-white text-gray-600 flex flex-col py-4 px-3 shrink-0 border-r border-gray-100">
      <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mb-3 px-2">Channels</p>
      <ul className="space-y-0.5">
        {channels.map((ch) => {
          const isActive = activeChannel?.id === ch.id
          return (
            <li key={ch.id}>
              <button
                id={`channel-${ch.id}`}
                onClick={() => setActiveChannel(ch)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${isActive
                    ? 'bg-teal-50 text-teal-700 font-semibold border border-teal-100'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }`}
              >
                <HashtagIcon className={`w-4 h-4 shrink-0 ${isActive ? 'text-teal-500' : 'text-gray-400'}`} />
                <span className="truncate">{ch.name}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
