import { useEffect, useState } from 'react'
import { XMarkIcon, UsersIcon, ShieldCheckIcon, AcademicCapIcon, BriefcaseIcon } from '@heroicons/react/24/outline'
import PersonaAvatar from './PersonaAvatar'
import { useChat } from '../../contexts/ChatContext'

export default function CircleInfoModal({ isOpen, onClose }) {
  const { loadMembers } = useChat()
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen) {
      setLoading(true)
      loadMembers().then(data => {
        setMembers(data || [])
        setLoading(false)
      })
    }
  }, [isOpen, loadMembers])

  if (!isOpen) return null

  const getRoleIcon = (role) => {
    switch (role) {
      case 'admin': return <ShieldCheckIcon className="w-4 h-4 text-purple-500" />
      case 'student': return <AcademicCapIcon className="w-4 h-4 text-blue-500" />
      case 'mentor': return <BriefcaseIcon className="w-4 h-4 text-green-500" />
      case 'sponsor': return <UsersIcon className="w-4 h-4 text-orange-500" />
      default: return null
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
      <div 
        className="bg-white/90 backdrop-blur-xl w-full max-w-md rounded-2xl shadow-2xl border border-white/20 overflow-hidden flex flex-col animate-in zoom-in-95 duration-200"
        style={{ maxHeight: '80vh' }}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-blue-50/50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-xl text-blue-600">
              <UsersIcon className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 tracking-tight">Circle Members</h2>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Group Info</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm text-gray-500 font-medium">Fetching personas...</p>
            </div>
          ) : members.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-gray-400 text-sm">No members found in this circle.</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {members.map((member) => (
                <div 
                  key={member.persona_id} 
                  className="group flex items-center gap-4 p-3 rounded-xl hover:bg-blue-50/50 border border-transparent hover:border-blue-100 transition-all cursor-default"
                >
                  <div className="relative">
                    <PersonaAvatar 
                      nickname={member.nickname} 
                      avatarKey={member.avatar_key} 
                      className="w-12 h-12 shadow-sm group-hover:scale-105 transition-transform" 
                    />
                    <div className="absolute -bottom-1 -right-1 bg-white p-1 rounded-full shadow-sm border border-gray-50">
                      {getRoleIcon(member.role)}
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-bold text-gray-900 group-hover:text-blue-700 transition-colors">
                      {member.nickname}
                    </p>
                    <div className="flex items-center gap-2">
                       <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                        {member.role}
                      </span>
                      <span className="text-[10px] text-gray-300">•</span>
                      <span className="text-[10px] text-gray-400 font-medium">
                        Joined {new Date(member.joined_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
          <p className="text-[10px] text-center text-gray-400 leading-relaxed italic">
            Persona identities are anonymous to protect member privacy. Real names and user IDs are never shared.
          </p>
        </div>
      </div>
    </div>
  )
}
