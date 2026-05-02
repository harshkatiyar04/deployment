import { createContext, useContext, useState } from 'react'

const PersonaContext = createContext()

export const usePersona = () => {
  const context = useContext(PersonaContext)
  if (!context) {
    throw new Error('usePersona must be used within a PersonaProvider')
  }
  return context
}

const getDefaultSubtype = (type) => {
  const defaults = {
    student: 'university',
    sponsor: 'individual',
    supplier: 'service',
    admin: null
  }
  return defaults[type] || null
}

export const PersonaProvider = ({ children }) => {
  const [activePersona, setActivePersona] = useState(() => {
    const isAdminSession = sessionStorage.getItem('isAdmin') === 'true';
    const savedPersona = sessionStorage.getItem('zenk_persona');
    
    if (isAdminSession) return { type: 'admin', subtype: null };
    if (savedPersona) return { type: savedPersona, subtype: getDefaultSubtype(savedPersona) };
    
    return {
      type: 'sponsor',
      subtype: 'individual',
    };
  });

  const switchPersona = (type, subtype = null) => {
    setActivePersona({
      type,
      subtype: subtype || getDefaultSubtype(type)
    })
  }


  const getPersonaLabel = () => {
    const { type, subtype } = activePersona
    
    if (type === 'student') {
      const labels = {
        primary: 'Primary School Student',
        secondary: 'Secondary School Student',
        university: 'University Student'
      }
      return labels[subtype] || 'Student'
    }
    
    if (type === 'sponsor') {
      const labels = {
        corporate: 'Corporate Sponsor',
        individual: 'Individual Sponsor',
        ngo: 'NGO Partner'
      }
      return labels[subtype] || 'Sponsor'
    }
    
    if (type === 'supplier') {
      const labels = {
        service: 'Educational Service Provider',
        product: 'Product Supplier'
      }
      return labels[subtype] || 'Supplier'
    }
    
    if (type === 'admin') {
      return 'Platform Administrator'
    }
    
    return 'User'
  }

  const value = {
    activePersona,
    switchPersona,
    getPersonaLabel,
    isStudent: activePersona.type === 'student',
    isSponsor: activePersona.type === 'sponsor',
    isSupplier: activePersona.type === 'supplier',
    isAdmin: activePersona.type === 'admin'
  }

  return (
    <PersonaContext.Provider value={value}>
      {children}
    </PersonaContext.Provider>
  )
}

