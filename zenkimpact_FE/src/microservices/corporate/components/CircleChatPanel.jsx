import React, { useState, useRef, useEffect } from 'react';

export default function CircleChatPanel({ circle, onClose }) {
  const [messages, setMessages] = useState([
    { id: 1, sender: 'Kia', type: 'system', text: `Welcome to the ${circle.circle_name} stakeholder chat. The circle leader ${circle.leader} is available here.`, time: new Date(Date.now() - 3600000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) },
    { id: 2, sender: circle.leader, type: 'leader', text: 'Thank you so much for the recent funding increase! The students are thrilled with the new science kits.', time: new Date(Date.now() - 1800000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }
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
      sender: 'You', 
      type: 'user', 
      text: input, 
      time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) 
    }]);
    
    setInput('');
    
    // Simulate leader reply
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: circle.leader,
        type: 'leader',
        text: "I'll make sure to update the progress tracker. Let me know if you need anything else!",
        time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      }]);
    }, 1500);
  };

  return (
    <div className="c-chat-panel">
      <div className="c-chat-header">
        <div>
          <h3>{circle.circle_name} Chat</h3>
          <span>{circle.leader} (Leader) • {circle.members} Members</span>
        </div>
        <button className="c-btn-icon" onClick={onClose}>×</button>
      </div>
      
      <div className="c-chat-body">
        {messages.map(m => (
          <div key={m.id} className={`c-chat-msg ${m.type}`}>
            <div className="c-chat-msg-meta">
              <strong>{m.sender}</strong> <span>{m.time}</span>
            </div>
            <div className="c-chat-msg-bubble">{m.text}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      
      <form className="c-chat-input" onSubmit={handleSend}>
        <input 
          type="text" 
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Message the circle leader..." 
          className="c-input"
        />
        <button type="submit" className="c-btn c-btn-primary">Send</button>
      </form>
    </div>
  );
}
