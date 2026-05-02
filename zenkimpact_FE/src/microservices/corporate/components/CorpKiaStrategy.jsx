import React, { useState } from 'react';
import CircleChatPanel from './CircleChatPanel';

export default function CorpKiaStrategy({ 
  profile, 
  strategyBrief, 
  peerBenchmarks, 
  goals, 
  circlesPerf,
  onRefresh 
}) {
  const [activeCircleChat, setActiveCircleChat] = useState(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  
  const handleRegenerate = async () => {
    try {
      setIsRegenerating(true);
      const token = localStorage.getItem('access_token');
      // The API call to force refresh. Note: usually we'd have this in the hook, but for now we can do a direct fetch and then onRefresh
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      await fetch(`${API_BASE}/corporate/kia-strategy-brief?force_refresh=true`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await onRefresh();
    } catch (e) {
      console.error("Failed to regenerate", e);
    } finally {
      setIsRegenerating(false);
    }
  };

  // Format date for strategy brief
  const generatedDate = strategyBrief?.generated_at 
    ? new Date(strategyBrief.generated_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : 'Recently';

  return (
    <div className="corp-kia-strategy-tab">
      
      {/* ── Section 1: Kia Strategy Briefing ─────────────────────────────────── */}
      <div className="c-card" style={{ marginBottom: 24, borderTop: '4px solid #F0A500' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <div className="corp-kia-dot" style={{ background: '#F0A500' }} />
          <h3 style={{ margin: 0, color: '#1a1a1a', fontWeight: 600 }}>
            Kia · Corporate strategy · {generatedDate}
          </h3>
          <button 
            className="c-btn-secondary" 
            style={{ marginLeft: 'auto', padding: '4px 12px', fontSize: 12, opacity: isRegenerating ? 0.7 : 1 }}
            onClick={handleRegenerate}
            disabled={isRegenerating}
          >
            {isRegenerating ? 'Generating...' : 'Regenerate Strategy'}
          </button>
        </div>
        
        <p style={{ color: '#444', marginBottom: 20 }}>
          Your Corporate ZenQ of {profile?.corporate_zenq || 78.4} places {profile?.company_name || 'your company'} in the top 12% of all corporate partners on the platform. Three highest-impact actions for the next quarter:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {strategyBrief?.priorities?.map((priority, idx) => (
            <div key={idx} className="strategy-priority-card" style={{
              padding: 16, 
              border: '1px solid #e8e8e4',
              borderRadius: 8,
              borderLeft: `4px solid ${priority.urgency === 'high' ? '#10B981' : priority.urgency === 'medium' ? '#F59E0B' : '#3B82F6'}`,
              background: '#fcfcfc'
            }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: 14, color: '#1a1a1a' }}>
                Priority {idx + 1} — {priority.title}
              </h4>
              <p style={{ margin: 0, fontSize: 13, color: '#555', lineHeight: 1.5 }}>
                {priority.body}
              </p>
            </div>
          ))}
          
          {(!strategyBrief || !strategyBrief.priorities) && (
            <div style={{ padding: 16, background: '#f5f5f5', borderRadius: 8, textAlign: 'center', color: '#666' }}>
              No strategy brief generated yet. Click "Regenerate Strategy" to ask Kia for recommendations.
            </div>
          )}
        </div>
      </div>

      {/* ── Section 2: Peer Benchmarking ─────────────────────────────────────── */}
      <div className="c-card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#888', margin: '0 0 16px 0' }}>
          PEER BENCHMARKING — ANONYMISED
        </h3>
        <p style={{ fontSize: 13, color: '#555', marginBottom: 20 }}>
          How does your Corporate ZenQ compare to other companies on the ZenK platform? All names are anonymised except yours.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {peerBenchmarks?.map((peer, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 24, fontSize: 12, fontWeight: 600, color: peer.is_you ? '#F0A500' : '#888' }}>
                #{peer.rank}
              </div>
              <div style={{ width: 180, fontSize: 13 }}>
                <strong style={{ color: peer.is_you ? '#1a1a1a' : '#555' }}>{peer.label}</strong>
                {peer.sector !== 'You' && <span style={{ color: '#888', fontSize: 11, marginLeft: 6 }}>({peer.sector})</span>}
                {peer.is_you && <span style={{ color: '#10B981', fontSize: 11, marginLeft: 6 }}>You</span>}
              </div>
              <div style={{ flex: 1, height: 8, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ 
                  height: '100%', 
                  background: peer.is_you ? '#10B981' : '#3B82F6', 
                  width: `${(peer.zenq / 100) * 100}%`,
                  opacity: peer.is_you ? 1 : 0.6
                }} />
              </div>
              <div style={{ width: 40, textAlign: 'right', fontSize: 13, fontWeight: 600, color: peer.is_you ? '#10B981' : '#1a1a1a' }}>
                {peer.zenq.toFixed(1)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Section 3: Goal Tracker ──────────────────────────────────────────── */}
      <div className="c-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#888', margin: 0 }}>
            CORPORATE CSR GOALS
          </h3>
          <button className="c-btn-secondary" style={{ padding: '4px 12px', fontSize: 12 }}>+ Add Goal</button>
        </div>

        <div style={{ display: 'flex', gap: 16 }}>
          {(goals && goals.length > 0) ? goals.map((goal, idx) => (
            <div key={idx} style={{ flex: 1, padding: 16, border: '1px solid #e8e8e4', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: 14 }}>{goal.title}</h4>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>
                {goal.current_value} / {goal.target_value} <span style={{ fontSize: 14, color: '#888', fontWeight: 400 }}>{goal.unit}</span>
              </div>
              <div style={{ height: 6, background: '#f0f0f0', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', background: '#F0A500', width: `${Math.min(100, (goal.current_value / goal.target_value) * 100)}%` }} />
              </div>
            </div>
          )) : (
            <div style={{ flex: 1, padding: 24, textAlign: 'center', background: '#fcfcfc', border: '1px dashed #e8e8e4', borderRadius: 8, color: '#888' }}>
              No goals set. Click "+ Add Goal" or let Kia suggest some for you.
            </div>
          )}
        </div>
      </div>

      {/* ── Section 4: Scenario Planner ────────────────────────────────────── */}
      <div className="c-card" style={{ marginBottom: 24, background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)', border: '1px solid #e2e8f0' }}>
        <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', margin: '0 0 16px 0' }}>
          KIA SCENARIO PLANNER
        </h3>
        <p style={{ fontSize: 13, color: '#475569', marginBottom: 16 }}>
          Ask Kia to project the impact of hypothetical CSR decisions on your Corporate ZenQ.
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['Add ₹50K to top circle', 'Enroll 50 more employees', 'Fund a new circle in Delhi'].map(chip => (
            <button key={chip} className="corp-kia-chip" style={{ background: '#fff', border: '1px solid #cbd5e1' }}>{chip}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input type="text" className="c-input" placeholder="What if we..." style={{ flex: 1, background: '#fff' }} />
          <button className="c-btn c-btn-primary">Model Scenario</button>
        </div>
      </div>

      {/* ── Section 5: ZenK Circle Chat ──────────────────────────────────────── */}
      <div className="c-card">
        <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#888', margin: '0 0 16px 0' }}>
          ZENK CIRCLE CHAT — CONNECT WITH SPONSOR LEADERS
        </h3>
        
        <div style={{ padding: 12, background: '#FFFBEB', border: '1px solid #FEF3C7', borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#B45309', display: 'flex', gap: 8 }}>
          <span>👀</span>
          <span>
            As a corporate partner you are an automatic observer member of all circles you fund. You can post encouragement and strategic direction — but circles operate independently. Kia monitors all corporate messages to ensure they align with ZenK circle autonomy principles.
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {circlesPerf?.map(circle => (
            <button 
              key={circle.circle_name}
              className={`c-btn ${activeCircleChat?.circle_name === circle.circle_name ? 'c-btn-primary' : 'c-btn-secondary'}`}
              style={{ padding: '6px 12px', fontSize: 13, borderRadius: 20, background: activeCircleChat?.circle_name === circle.circle_name ? '#10B981' : undefined, color: activeCircleChat?.circle_name === circle.circle_name ? '#fff' : undefined }}
              onClick={() => setActiveCircleChat(circle)}
            >
              {circle.circle_name}
            </button>
          ))}
        </div>

        {activeCircleChat ? (
          <div style={{ border: '1px solid #e8e8e4', borderRadius: 8, overflow: 'hidden' }}>
            <CircleChatPanel circle={activeCircleChat} onClose={() => setActiveCircleChat(null)} />
          </div>
        ) : (
          <div style={{ padding: 32, textAlign: 'center', background: '#fcfcfc', border: '1px dashed #e8e8e4', borderRadius: 8, color: '#888' }}>
            Select a circle above to view its chat history and message the sponsor leader.
          </div>
        )}
      </div>

      {/* ── Section 6: Kia Conversational ────────────────────────────────────── */}
      <div className="c-card" style={{ marginTop: 24, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', height: 400 }}>
        <div style={{ padding: '16px 20px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="corp-kia-avatar-circle" style={{ width: 32, height: 32 }}>
            <img src="/kia-bot-avatar.png" alt="Kia" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: 14, color: '#1e293b' }}>Kia Strategy Chat</h3>
            <div style={{ fontSize: 12, color: '#64748b' }}>Deep dive into your portfolio strategy</div>
          </div>
        </div>
        <div style={{ flex: 1, padding: 20, overflowY: 'auto', background: '#fff' }}>
          <div className="c-chat-msg system">
            <div className="c-chat-msg-bubble" style={{ background: '#f1f5f9', color: '#334155', border: 'none' }}>
              Hello! I've prepared your strategy brief above. I'm ready to answer any questions about your portfolio, help draft communications to circle leaders, or run what-if scenarios.
            </div>
          </div>
        </div>
        <div style={{ padding: 16, borderTop: '1px solid #e2e8f0', background: '#f8fafc' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {['Explain Priority 1', 'Compare my circles', 'Draft employee email'].map(chip => (
              <button key={chip} style={{ padding: '4px 12px', fontSize: 12, background: '#fff', border: '1px solid #cbd5e1', borderRadius: 12, color: '#475569', cursor: 'pointer' }}>
                {chip}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <input type="text" className="c-input" placeholder="Message Kia about your strategy..." style={{ flex: 1 }} />
            <button className="c-btn c-btn-primary">Send</button>
          </div>
        </div>
      </div>

    </div>
  );
}
