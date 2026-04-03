/**
 * StageBar — banner shown when stageActive is true.
 * Sponsors/mentors see the raised-hand queue.
 * Students see "raise your hand to speak" instruction.
 */
import { HandRaisedIcon, MicrophoneIcon } from '@heroicons/react/24/outline'
import PersonaAvatar from './PersonaAvatar'
import { useChat } from '../../contexts/ChatContext'

export default function StageBar({ userPersona }) {
  const { stageActive, handsRaised, setStageActive } = useChat()

  if (!stageActive) return null

  const isLead = userPersona === 'sponsor' || userPersona === 'mentor' || userPersona === 'admin'

  return (
    <div
      id="stage-bar"
      className="bg-teal-700 text-white px-4 py-2 flex items-center gap-3 flex-wrap"
    >
      <MicrophoneIcon className="w-5 h-5 shrink-0 text-teal-200" />
      <span className="text-sm font-semibold">Stage is active</span>

      {isLead ? (
        <>
          <span className="text-xs text-teal-300 mr-2">
            {handsRaised.length === 0
              ? 'No hands raised yet'
              : `${handsRaised.length} hand${handsRaised.length > 1 ? 's' : ''} raised:`}
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            {handsRaised.map((h) => (
              <div
                key={h.persona_id}
                className="flex items-center gap-1.5 bg-teal-600 rounded-full pl-1 pr-2.5 py-0.5 text-xs"
                title={h.nickname}
              >
                <PersonaAvatar nickname={h.nickname} avatarKey={h.avatar_key} size="sm" />
                <span>{h.nickname}</span>
              </div>
            ))}
          </div>
          {/* End stage button for leads */}
          <button
            id="end-stage-btn"
            onClick={() => setStageActive(false)}
            className="ml-auto text-xs bg-teal-800 hover:bg-teal-900 rounded px-2 py-1 transition-colors"
          >
            End stage
          </button>
        </>
      ) : (
        <span className="text-sm text-teal-200">
          Raise your hand to speak during this stage session.
        </span>
      )}
    </div>
  )
}
