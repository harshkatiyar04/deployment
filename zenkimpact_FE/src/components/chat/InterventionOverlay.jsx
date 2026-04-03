import { XMarkIcon } from '@heroicons/react/24/solid'

// Custom geometric hexagonal shield — far more distinctive than heroicons default
const HexShieldIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M12 2L4.5 5.5V11C4.5 15.75 7.75 20.2 12 21.5C16.25 20.2 19.5 15.75 19.5 11V5.5L12 2Z"
      fill="currentColor"
      fillOpacity="0.15"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
    <path
      d="M9 11.5L11 13.5L15 9.5"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M12 2L4.5 5.5V8L12 4.5L19.5 8V5.5L12 2Z"
      fill="currentColor"
      fillOpacity="0.3"
    />
  </svg>
)

// Nudge uses a broken/alert variant of the shield
const ShieldAlertIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M12 2L4.5 5.5V11C4.5 15.75 7.75 20.2 12 21.5C16.25 20.2 19.5 15.75 19.5 11V5.5L12 2Z"
      fill="currentColor"
      fillOpacity="0.15"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
    <line x1="12" y1="8.5" x2="12" y2="13" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    <circle cx="12" cy="15.5" r="0.85" fill="currentColor" />
    <path
      d="M12 2L4.5 5.5V8L12 4.5L19.5 8V5.5L12 2Z"
      fill="currentColor"
      fillOpacity="0.3"
    />
  </svg>
)

export default function InterventionOverlay({ type, message, onDismiss }) {
  if (!type) return null
  const isBlock = type === 'block' || type === 'message_blocked'

  const Icon = isBlock ? HexShieldIcon : ShieldAlertIcon

  return (
    <div className="absolute top-5 left-1/2 -translate-x-1/2 z-[100] w-full max-w-md px-4 animate-in slide-in-from-top-4 duration-300">

      {/* Gradient glow border wrapper */}
      <div className={`p-[1.5px] rounded-2xl ${isBlock
        ? 'bg-gradient-to-br from-blue-500 via-indigo-500 to-blue-700'
        : 'bg-gradient-to-br from-blue-300 via-sky-400 to-blue-500'
        } shadow-lg ${isBlock ? 'shadow-blue-500/30' : 'shadow-blue-300/30'}`}>

        <div className="bg-white rounded-[14px] overflow-hidden flex">

          {/* ── Left accent panel ── */}
          <div className={`relative flex flex-col items-center justify-center gap-3 px-5 py-6 ${isBlock
            ? 'bg-gradient-to-b from-blue-600 to-indigo-700'
            : 'bg-gradient-to-b from-blue-400 to-sky-500'
            }`}>

            {/* Decorative blurred blob behind icon */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-16 h-16 rounded-full bg-white/10 blur-xl" />
            </div>

            {/* Animated pulse + icon */}
            <div className="relative z-10">
              <span className="absolute inset-0 rounded-full bg-white/25 animate-ping" />
              <div className="relative w-12 h-12 rounded-full bg-white/20 border border-white/30 flex items-center justify-center backdrop-blur-sm">
                <Icon className="w-6 h-6 text-white" />
              </div>
            </div>

            {/* Subtle stacked dots decoration */}
            <div className="flex flex-col items-center gap-1 z-10">
              {[1, 0.5, 0.25].map((op, i) => (
                <div key={i} className="w-1 h-1 rounded-full bg-white" style={{ opacity: op }} />
              ))}
            </div>
          </div>

          {/* ── Right content panel ── */}
          <div className="flex-1 flex flex-col justify-between p-4 pr-3">

            {/* Header row */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className={`inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-[0.15em] px-2 py-0.5 rounded-full mb-1.5 ${isBlock ? 'bg-blue-50 text-blue-600' : 'bg-sky-50 text-sky-500'
                  }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${isBlock ? 'bg-blue-500' : 'bg-sky-400'} animate-pulse`} />
                  {isBlock ? 'Blocked' : 'Warning'}
                </span>
                <p className="text-sm font-bold text-slate-800 leading-tight tracking-tight">
                  {isBlock ? 'Message Blocked' : 'Safety Nudge'}
                </p>
              </div>

              <button
                onClick={onDismiss}
                className="p-1 mt-0.5 rounded-full hover:bg-slate-100 transition-colors"
              >
                <XMarkIcon className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

            {/* Message */}
            <p className="text-xs text-slate-500 leading-relaxed mt-2">
              {message || 'This content violates community safety standards.'}
            </p>

            {/* Footer action row */}
            <div className="flex items-center gap-2.5 mt-3">
              <button
                onClick={onDismiss}
                className={`text-xs font-bold text-white px-4 py-1.5 rounded-lg transition-all active:scale-95 ${isBlock
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700'
                  : 'bg-gradient-to-r from-blue-400 to-sky-500 hover:from-blue-500 hover:to-sky-600'
                  } shadow-sm`}
              >
                Got it
              </button>
              <span className="h-3 w-px bg-slate-200" />
              <p className="text-[9px] uppercase tracking-widest text-slate-300 font-semibold select-none">
                Safety Guard
              </p>
            </div>
          </div>
        </div>

        {/* Bottom shimmer line */}
        <div className={`h-[2px] w-full ${isBlock
          ? 'bg-gradient-to-r from-blue-500 via-indigo-400 to-blue-600'
          : 'bg-gradient-to-r from-sky-300 via-blue-400 to-sky-300'
          }`} />
      </div>

    </div>
  )
}
