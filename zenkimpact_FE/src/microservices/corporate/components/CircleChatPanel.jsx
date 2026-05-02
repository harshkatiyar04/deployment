import React, { useState, useRef, useEffect } from 'react';

export default function CircleChatPanel({ circle, onClose, inline = false }) {
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      sender: 'Rohit Chawla', 
      role: 'SL',
      initials: 'RC',
      avatarColor: '#bbf7d0',
      avatarText: '#166534',
      bubbleBg: '#ecfdf5',
      text: `Great news — student scored 84% in Term 1 maths, up from 61% baseline. The circle's effort is showing real results.`, 
      time: '8 Mar, 11:05 AM',
      align: 'left'
    },
    { 
      id: 2, 
      sender: 'Kia', 
      role: '',
      initials: 'K',
      avatarColor: '#10b981',
      avatarText: '#ffffff',
      bubbleBg: '#d1fae5',
      text: `TCS Foundation's Q1 allocation of ₹20,000 has been confirmed to this circle. This funded the student's Term 2 textbooks and science materials. ZenQ impact from this allocation: +6.2 pts to TCS Corporate score.`,
      kiaNote: `Your volunteer Priya Kulkarni's mentoring sessions contributed +0.9 pts to your Corporate ZenQ this month. Nominating one more employee as science tutor would accelerate the student's ZQA preparation.`,
      time: '8 Mar, 11:06 AM',
      align: 'left'
    },
    { 
      id: 3, 
      sender: 'TCS Foundation', 
      role: '',
      initials: 'TC',
      avatarColor: '#3b82f6',
      avatarText: '#ffffff',
      bubbleBg: '#e0f2fe',
      text: `Excellent progress. TCS is proud to support this circle. We are committed through FY27. Our employee Priya mentioned the student is interested in a science competition — we would be happy to provide a TCS mentor to help prepare.`, 
      time: '10 Mar, 9:30 AM',
      align: 'right'
    },
    { 
      id: 4, 
      sender: 'Priya Sharma', 
      role: 'Member',
      initials: 'PS',
      avatarColor: '#f1f5f9',
      avatarText: '#475569',
      bubbleBg: '#f8fafc',
      text: `Thank you TCS Foundation. The circle deeply appreciates your support and engagement. It makes a real difference to see the company involved directly.`, 
      time: '10 Mar, 10:15 AM',
      align: 'left'
    }
  ]);
  
  const [input, setInput] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setMessages([...messages, { 
      id: Date.now(), 
      sender: 'TCS Foundation', 
      role: '',
      initials: 'TC',
      avatarColor: '#3b82f6',
      avatarText: '#ffffff',
      bubbleBg: '#e0f2fe',
      text: input, 
      time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', month: 'short', day: 'numeric'}),
      align: 'right'
    }]);
    
    setInput('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: inline ? 600 : 500, background: '#fff' }}>
      
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{ 
        padding: '16px 20px', 
        borderBottom: '1px solid #e8e8e4', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center' 
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>
          {circle.circle_name} — ZenK Circle Chat
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 12, fontStyle: 'italic', color: '#888' }}>
            Observer member — messages visible to the circle
          </div>
          {!inline && (
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#888' }}>&times;</button>
          )}
        </div>
      </div>

      {/* ── Chat Body ──────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {messages.map(m => {
          const isRight = m.align === 'right';
          return (
            <div key={m.id} style={{ display: 'flex', flexDirection: isRight ? 'row-reverse' : 'row', gap: 12, alignItems: 'flex-start' }}>
              
              {/* Avatar */}
              <div style={{ 
                width: 32, 
                height: 32, 
                borderRadius: '50%', 
                background: m.avatarColor, 
                color: m.avatarText, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                fontSize: 12, 
                fontWeight: 600,
                flexShrink: 0,
                marginTop: 4
              }}>
                {m.initials}
              </div>

              {/* Message Content */}
              <div style={{ maxWidth: '80%', display: 'flex', flexDirection: 'column', alignItems: isRight ? 'flex-end' : 'flex-start' }}>
                <div style={{ 
                  background: m.bubbleBg, 
                  padding: '12px 16px', 
                  borderRadius: 8,
                  fontSize: 13,
                  color: '#1a1a1a',
                  lineHeight: 1.5,
                  border: m.bubbleBg === '#f8fafc' ? '1px solid #e2e8f0' : 'none'
                }}>
                  {m.text}

                  {m.kiaNote && (
                    <div style={{ 
                      marginTop: 12, 
                      background: '#fff', 
                      border: '1px solid #a7f3d0', 
                      borderRadius: 6, 
                      padding: 12 
                    }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#065f46', marginBottom: 4 }}>Kia notes for TCS:</div>
                      <div style={{ fontSize: 12, color: '#064e3b' }}>{m.kiaNote}</div>
                    </div>
                  )}
                </div>
                
                {/* Meta text below bubble */}
                <div style={{ fontSize: 10, color: '#888', marginTop: 6, paddingLeft: isRight ? 0 : 4, paddingRight: isRight ? 4 : 0 }}>
                  {m.sender}{m.role ? ` (${m.role})` : ''} - {m.time}
                </div>
              </div>

            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {/* ── Input Area ─────────────────────────────────────────────── */}
      <div style={{ padding: '16px 24px', borderTop: '1px solid #e8e8e4', background: '#fff' }}>
        <form onSubmit={handleSend} style={{ display: 'flex', gap: 12 }}>
          <input 
            type="text" 
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Message the circle as TCS Foundation..." 
            style={{ 
              flex: 1, 
              padding: '10px 16px', 
              fontSize: 13, 
              border: '1px solid #cbd5e1', 
              borderRadius: 8,
              outline: 'none'
            }}
            onFocus={e => e.target.style.borderColor = '#3b82f6'}
            onBlur={e => e.target.style.borderColor = '#cbd5e1'}
          />
          <button 
            type="submit" 
            style={{ 
              background: '#3b82f6', 
              color: '#fff', 
              border: 'none', 
              padding: '0 24px', 
              borderRadius: 8, 
              fontSize: 13, 
              fontWeight: 600, 
              cursor: 'pointer' 
            }}
          >
            Send
          </button>
        </form>
      </div>

    </div>
  );
}
