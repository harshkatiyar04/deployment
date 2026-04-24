import { useState } from 'react'
import { AcademicCapIcon } from '@heroicons/react/24/outline'
import { useIsMobile } from '../../hooks/useIsMobile'

const SCHOOL_CONTACTS = [
  { id: 'principal', name: 'Mrs. Rekha Iyer', role: 'Principal', school: "St. Mary's High School", online: true, initials: 'RI' },
  { id: 'teacher', name: 'Mr. Sameer Joshi', role: 'Class Teacher', school: "St. Mary's High School", online: false, initials: 'SJ' },
  { id: 'counselor', name: 'Ms. Anita Rao', role: 'Guidance Counselor', school: "St. Mary's High School", online: true, initials: 'AR' },
]

const STUDENTS = [
  { id: 'ananya', name: 'Ananya Deshpande', grade: '9th Std', school: "St. Mary's High School", attendance: '94%', initials: 'AD', status: 'active' },
  { id: 'ravi', name: 'Ravi Shankar', grade: '8th Std', school: "St. Mary's High School", attendance: '88%', initials: 'RS', status: 'active' },
  { id: 'meera', name: 'Meera Kulkarni', grade: '10th Std', school: "St. Mary's High School", attendance: '91%', initials: 'MK', status: 'active' },
]

const INITIAL_MESSAGES = {
  principal: [
    { id: 1, sender: 'them', name: 'Mrs. Rekha Iyer', text: 'Good afternoon, Rohit. Ananya has been performing well in her mid-term assessments. Her attendance is consistent.', time: '2:30 PM' },
    { id: 2, sender: 'you', text: 'Thank you, Mrs. Iyer. We wanted to discuss the upcoming term fees and whether the school can accommodate our payment schedule.', time: '2:45 PM' },
    { id: 3, sender: 'them', name: 'Mrs. Rekha Iyer', text: 'Absolutely. We can work out a staggered payment plan. Please send the proposal and we will review it.', time: '3:10 PM' },
  ],
  teacher: [],
  counselor: [],
  ananya: [
    { id: 1, sender: 'them', name: 'Ananya Deshpande', text: 'Sir, I got selected for the district-level science fair! Thank you for the support. 🎉', time: '11:00 AM' },
    { id: 2, sender: 'you', text: 'That is wonderful news, Ananya! We are all very proud. Let us know if you need any materials for the project.', time: '11:15 AM' },
  ],
  ravi: [],
  meera: [],
}

export default function SCSchoolComm() {
  const [activeContact, setActiveContact] = useState('principal')
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const isMobile = useIsMobile()
  const [mobileView, setMobileView] = useState('list')

  const handleContactOpen = (id) => {
    setActiveContact(id)
    if (isMobile) setMobileView('chat')
  }

  const currentContact = [...SCHOOL_CONTACTS, ...STUDENTS].find(c => c.id === activeContact)
  const currentMessages = messages[activeContact] || []

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim()) return
    const newMsg = {
      id: Date.now(),
      sender: 'you',
      text: input,
      time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => ({
      ...prev,
      [activeContact]: [...(prev[activeContact] || []), newMsg],
    }))
    setInput('')
  }

  const contactStyle = (id) => ({
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: '12px 16px', cursor: 'pointer',
    background: activeContact === id ? 'var(--sc-green-bg)' : 'transparent',
    borderLeft: activeContact === id ? '3px solid var(--sc-green)' : '3px solid transparent',
    transition: 'background 0.15s',
  })

  return (
    <div className="sc-school-comm-layout" style={{
      display: 'flex', flex: 1, minHeight: 0,
      background: 'white', borderRadius: isMobile ? '0' : '12px', overflow: 'hidden',
      border: isMobile ? 'none' : '1px solid var(--sc-border)', 
      boxShadow: isMobile ? 'none' : 'var(--sc-shadow)',
    }}>
      {/* Contact Rail */}
      {(!isMobile || mobileView === 'list') && (
        <div className="sc-school-contacts" style={{
          width: isMobile ? '100%' : '260px', borderRight: '1px solid var(--sc-border)',
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
          background: '#f8fafc',
        }}>
        <div style={{
          padding: '16px', borderBottom: '1px solid var(--sc-border)',
        }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--sc-text-muted)', letterSpacing: '0.8px', textTransform: 'uppercase' }}>
            School Communication
          </div>
          <div style={{ fontSize: '12px', color: 'var(--sc-text-muted)', marginTop: '4px' }}>
            St. Mary's High School
          </div>
        </div>

        {/* School Staff */}
        <div style={{ padding: '12px 16px 4px', fontSize: '10px', fontWeight: 700, color: 'var(--sc-text-muted)', letterSpacing: '0.8px', textTransform: 'uppercase' }}>
          School Staff
        </div>
        {SCHOOL_CONTACTS.map(contact => (
          <div key={contact.id} onClick={() => handleContactOpen(contact.id)} style={contactStyle(contact.id)}>
            <div style={{ position: 'relative' }}>
              <div style={{
                width: '32px', height: '32px', borderRadius: '8px',
                background: activeContact === contact.id ? 'var(--sc-green)' : '#e8f5f0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '10px', fontWeight: 700,
                color: activeContact === contact.id ? '#fff' : 'var(--sc-green-dark)',
              }}>{contact.initials}</div>
              {contact.online && (
                <div style={{
                  position: 'absolute', bottom: -1, right: -1,
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: '#22c55e', border: '2px solid #f8fafc',
                }} />
              )}
            </div>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text)' }}>{contact.name}</div>
              <div style={{ fontSize: '10px', color: 'var(--sc-text-muted)' }}>{contact.role}</div>
            </div>
          </div>
        ))}

        {/* Students */}
        <div style={{ padding: '16px 16px 4px', fontSize: '10px', fontWeight: 700, color: 'var(--sc-text-muted)', letterSpacing: '0.8px', textTransform: 'uppercase', borderTop: '1px solid var(--sc-border)', marginTop: '8px' }}>
          Students
        </div>
        {STUDENTS.map(student => (
          <div key={student.id} onClick={() => handleContactOpen(student.id)} style={contactStyle(student.id)}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: activeContact === student.id ? 'var(--sc-orange)' : 'var(--sc-orange-light)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '10px', fontWeight: 700,
              color: activeContact === student.id ? '#fff' : 'var(--sc-orange)',
            }}>{student.initials}</div>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text)' }}>{student.name}</div>
              <div style={{ fontSize: '10px', color: 'var(--sc-text-muted)' }}>{student.grade} · Attendance {student.attendance}</div>
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Chat Area */}
      {(!isMobile || mobileView === 'chat') && (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Header */}
        <div style={{
          padding: '14px 20px', borderBottom: '1px solid var(--sc-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isMobile && (
              <button 
                onClick={() => setMobileView('list')}
                style={{ padding: '6px', background: 'transparent', border: 'none', cursor: 'pointer', marginRight: '-2px', marginLeft: '-8px' }}
              >
                <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
            )}
            {currentContact && (
              <>
                <div style={{
                  width: '10px', height: '10px', borderRadius: '50%',
                  background: currentContact.online !== undefined
                    ? (currentContact.online ? '#22c55e' : '#94a3b8')
                    : 'var(--sc-orange)',
                }} />
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--sc-text)' }}>
                    {currentContact.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>
                    {currentContact.role || currentContact.grade} · {currentContact.school}
                  </div>
                </div>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {currentContact?.grade && (
              <span style={{
                fontSize: '10px', fontWeight: 600, padding: '4px 10px', borderRadius: '6px',
                background: 'var(--sc-orange-light)', color: 'var(--sc-orange)',
              }}>Student</span>
            )}
            {currentContact?.role && !currentContact?.grade && (
              <span style={{
                fontSize: '10px', fontWeight: 600, padding: '4px 10px', borderRadius: '6px',
                background: 'var(--sc-green-light)', color: 'var(--sc-green)',
              }}>Staff</span>
            )}
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '20px',
          display: 'flex', flexDirection: 'column', gap: '14px',
        }}>
          {currentMessages.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', marginTop: '60px' }}>
              <AcademicCapIcon style={{ width: 36, height: 36, opacity: 0.3, margin: '0 auto 8px' }} />
              <div>No messages with <strong>{currentContact?.name}</strong> yet.</div>
              <div style={{ fontSize: '11px', marginTop: '4px' }}>Start a conversation about student progress, fees, or events.</div>
            </div>
          )}
          {currentMessages.map((msg) => (
            <div key={msg.id} style={{
              display: 'flex',
              justifyContent: msg.sender === 'you' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: '65%', padding: '12px 16px', borderRadius: '12px',
                background: msg.sender === 'you' ? 'var(--sc-green)' : '#f3f4f6',
                color: msg.sender === 'you' ? '#fff' : 'var(--sc-text)',
                fontSize: '13px', lineHeight: '1.6',
              }}>
                {msg.sender !== 'you' && (
                  <div style={{
                    fontSize: '10px', fontWeight: 700, marginBottom: '4px',
                    color: msg.sender === 'you' ? '#fff' : 'var(--sc-green)', opacity: 0.8,
                  }}>{msg.name}</div>
                )}
                <div>{msg.text}</div>
                <div style={{
                  fontSize: '10px', opacity: 0.6, marginTop: '6px', textAlign: 'right',
                }}>{msg.time}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div style={{
          padding: '14px 20px', borderTop: '1px solid var(--sc-border)',
        }}>
          <form onSubmit={handleSend} style={{ display: 'flex', gap: '10px' }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Message ${currentContact?.name || ''}...`}
              style={{
                flex: 1, padding: '12px 16px', borderRadius: '10px',
                border: '1px solid var(--sc-border)', fontSize: '13px',
                background: '#fff', color: 'var(--sc-text)', outline: 'none',
              }}
            />
            <button type="submit" style={{
              padding: '12px 24px', borderRadius: '10px', border: 'none',
              background: 'var(--sc-green)', color: '#fff', fontWeight: 700,
              fontSize: '13px', cursor: 'pointer',
            }}>Send</button>
          </form>
        </div>
      </div>
      )}
    </div>
  )
}
