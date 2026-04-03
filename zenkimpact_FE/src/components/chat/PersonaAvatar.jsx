import { useMemo, useState } from 'react'

const AVATAR_COLORS = [
  { bg: '#F8FAFC', text: '#475569' }, // Slate Gray
  { bg: '#0D9488', text: '#FFFFFF' }, // Zenk Teal
  { bg: '#FFF1F2', text: '#9F1239' }, // Soft Rose
  { bg: '#F0FDF4', text: '#166534' }, // Soft Green
  { bg: '#FFFBEB', text: '#92400E' }, // Soft Amber
  { bg: '#EFF6FF', text: '#1E40AF' }, // Soft Blue
  { bg: '#F5F3FF', text: '#5B21B6' }, // Soft Violet
  { bg: '#FEF2F2', text: '#991B1B' }  // Soft Red
]

/**
 * PersonaAvatar — renders an avatar image or initials fallback.
 */
export default function PersonaAvatar({ nickname = '?', avatarKey, isOnline = false, size = 'md' }) {
  const [imgError, setImgError] = useState(false)
  
  const sizeClasses = { 
    sm: 'w-7 h-7 text-[10px]', 
    md: 'w-8 h-8 text-[12px]', 
    lg: 'w-10 h-10 text-[14px]' 
  }
  
  const initials = useMemo(() => {
    const cleanNick = String(nickname || '?').trim()
    if (!cleanNick) return '?'
    const parts = cleanNick.split(/\s+/)
    if (parts.length > 1) {
      // e.g. "Rohit Chawla" -> "RC"
      return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
    }
    // e.g. "testuser4" -> "T4"
    if (cleanNick.length > 1) {
      return (cleanNick.charAt(0) + cleanNick.charAt(cleanNick.length - 1)).toUpperCase()
    }
    return cleanNick.charAt(0).toUpperCase()
  }, [nickname])

  const colors = useMemo(() => {
    const cleanNick = String(nickname || '?')
    let hash = 0
    for (let i = 0; i < cleanNick.length; i++) {
      hash = cleanNick.charCodeAt(i) + ((hash << 5) - hash)
    }
    const index = Math.abs(hash) % AVATAR_COLORS.length
    return AVATAR_COLORS[index]
  }, [nickname])

  const showInitials = !avatarKey || imgError

  return (
    <div className={`relative inline-block shrink-0 ${sizeClasses[size]}`} title={nickname}>
      <div
        className={`${sizeClasses[size]} rounded-full flex items-center justify-center font-extrabold select-none shadow-sm border border-black/5`}
        style={{ backgroundColor: colors.bg, color: colors.text }}
      >
        {!showInitials ? (
          <img
            src={avatarKey.startsWith('http') ? avatarKey : `/avatars/${avatarKey}.png`}
            alt={nickname}
            className="w-full h-full rounded-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          initials
        )}
      </div>
      {isOnline && (
        <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white" />
      )}
    </div>
  )
}
