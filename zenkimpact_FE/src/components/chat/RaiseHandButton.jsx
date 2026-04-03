
import { HandRaisedIcon } from '@heroicons/react/24/outline'
import { useChat } from '../../contexts/ChatContext'

export default function RaiseHandButton({ userPersona }) {
  const { stageActive, handsRaised, raiseHand, lowerHand, personaId } = useChat()

  // Show the raise hand button when stage is active (removed restriction for demo purposes)
  if (!stageActive) return null

  // Find if current user has hand raised by checking the handsRaised array against personaId
  const isRaised = handsRaised.some((h) => h.persona_id === personaId)

  const handleToggle = () => {
    if (isRaised) {
      lowerHand()
    } else {
      raiseHand()
    }
  }

  return (
    <button
      id="raise-hand-btn"
      onClick={handleToggle}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${isRaised
          ? 'bg-yellow-400 text-yellow-900 hover:bg-yellow-300 shadow-md'
          : 'bg-teal-100 text-teal-700 hover:bg-teal-200 border border-teal-200'
        }`}
      title={isRaised ? 'Lower hand' : 'Raise hand to speak'}
    >
      <HandRaisedIcon className={`w-5 h-5 ${isRaised ? 'text-yellow-800' : 'text-teal-600'}`} />
      {isRaised ? 'Lower hand' : 'Raise hand'}
    </button>
  )
}
