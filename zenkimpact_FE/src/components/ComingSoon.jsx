import { usePersona } from '../contexts/PersonaContext'
import { ClockIcon } from '@heroicons/react/24/outline'

function ComingSoon({ pageName }) {
  const { getPersonaLabel } = usePersona()

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center">
            <ClockIcon className="w-10 h-10 text-blue-600" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{pageName}</h2>
        <p className="text-gray-600 mb-1">This feature is coming soon!</p>
        <p className="text-sm text-gray-500">Viewing as: {getPersonaLabel()}</p>
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg max-w-md mx-auto">
          <p className="text-sm text-blue-800">
            <strong>Status:</strong> This page is part of Phase 1 implementation and will be available soon.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ComingSoon

