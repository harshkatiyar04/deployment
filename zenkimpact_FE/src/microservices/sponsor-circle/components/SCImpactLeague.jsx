import { useState } from 'react'
import {
  TrophyIcon,
  CheckCircleIcon,
  UserGroupIcon,
  CurrencyRupeeIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  AcademicCapIcon,
  GiftIcon
} from '@heroicons/react/24/outline'

export default function SCImpactLeague() {
  const [activeTab, setActiveTab] = useState('leaderboard') // leaderboard, missions, badges

  // MOCK DATA: 1-to-1 Deep Impact League Data
  const leaderboard = [
    { rank: 1, circleName: 'VIT Rising Circle', impactScore: 12450, studentName: 'Ayesha M.', coverage: '100% Funded', contributions: '₹2,45,000', mentoringHours: 420, missionsCompleted: 12, badge: 'gold', change: '+1' },
    { rank: 2, circleName: 'Mumbai Tech Philanthropy', impactScore: 11800, studentName: 'Ravi S.', coverage: '100% Funded', contributions: '₹1,98,000', mentoringHours: 350, missionsCompleted: 10, badge: 'silver', change: '-1' },
    { rank: 3, circleName: 'Delhi Edu-Leaders', impactScore: 9210, studentName: 'Priya T.', coverage: '85% Funded', contributions: '₹1,50,000', mentoringHours: 290, missionsCompleted: 8, badge: 'bronze', change: '+2' },
    { rank: 4, circleName: 'Pune Changemakers', impactScore: 8400, studentName: 'Karan V.', coverage: '70% Funded', contributions: '₹1,20,000', mentoringHours: 210, missionsCompleted: 6, badge: null, change: '-1' },
    { rank: 5, circleName: 'Bangalore Innovators', impactScore: 7850, studentName: 'Ananya G.', coverage: '60% Funded', contributions: '₹95,000', mentoringHours: 195, missionsCompleted: 5, badge: null, change: '0' },
  ]

  const impactMissions = [
    {
      id: 1,
      title: 'Ayesha\'s Final Year Laptop Upgrade',
      description: 'Funding a high-performance refurbished laptop so Ayesha can complete her Computer Science capstone project.',
      targetAmount: 45000,
      currentAmount: 38000,
      progress: 84,
      deadline: '2026-05-15',
      status: 'active',
      circle: 'VIT Rising Circle',
      category: 'Infrastructure'
    },
    {
      id: 2,
      title: 'Ravi\'s Housing Stipend (Term 3)',
      description: 'Covering 6 months of hostel fees and meal plans to ensure Ravi\'s living conditions are fully secured.',
      targetAmount: 60000,
      currentAmount: 60000,
      progress: 100,
      deadline: '2026-04-01',
      status: 'completed',
      circle: 'Mumbai Tech Philanthropy',
      category: 'Living Expenses'
    },
    {
      id: 3,
      title: 'Priya\'s 1-on-1 IELTS Coaching',
      description: 'Sponsoring intensive English fluency coaching to prepare Priya for her upcoming international internship interview.',
      targetAmount: 25000,
      currentAmount: 8500,
      progress: 34,
      deadline: '2026-06-30',
      status: 'active',
      circle: 'Delhi Edu-Leaders',
      category: 'Skill Development'
    }
  ]

  const badges = [
    { id: 1, name: 'First Milestone', description: 'Crossed ₹10,000 in total circle contributions.', icon: CurrencyRupeeIcon, earned: true, color: 'blue' },
    { id: 2, name: 'Knowledge Sharer', description: 'Logged 100 hours of 1-on-1 student mentoring.', icon: ChatBubbleLeftRightIcon, earned: true, color: 'purple' },
    { id: 3, name: 'Pillar of Impact', rank: 'Top 3', description: 'Maintained a Top 3 status in the National Impact League.', icon: TrophyIcon, earned: true, color: 'gold' },
    { id: 4, name: 'Mission Architect', description: 'Fully funded 5 deep-impact missions for your student.', icon: CheckCircleIcon, earned: true, color: 'green' },
    { id: 5, name: 'Graduate Maker', description: 'Sponsored a student all the way through their final degree graduation.', icon: AcademicCapIcon, earned: false, progress: 85, color: 'orange' },
  ]

  const currentCircle = leaderboard[0];

  const getRankIcon = (rank) => {
    if (rank === 1) return <TrophyIcon className="sc-league-medal medal-gold" />
    if (rank === 2) return <TrophyIcon className="sc-league-medal medal-silver" />
    if (rank === 3) return <TrophyIcon className="sc-league-medal medal-bronze" />
    return <span className="sc-league-rank-num">#{rank}</span>
  }

  return (
    <div className="sc-impact-league">
      {/* Premium Hero Banner Custom to League */}
      <div className="sc-league-hero">
        <div className="sc-league-hero-content">
          <h1>National Impact League</h1>
          <p>Compete, collaborate, and celebrate real-world change.</p>
        </div>
        <div className="sc-league-my-circle">
          <div className="sc-league-my-circle-header">
            <span>Your Circle</span>
            <div className="sc-league-badge-tag gold-badge">Gold Tier</div>
          </div>
          <h2>{currentCircle.circleName}</h2>
          <div className="sc-league-my-stats">
            <div>
              <label>Impact Score</label>
              <strong>{currentCircle.impactScore.toLocaleString()}</strong>
            </div>
            <div>
              <label>Rank</label>
              <strong>#{currentCircle.rank}</strong>
            </div>
            <div>
              <label>Trend</label>
              <strong className="text-green">{currentCircle.change}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Modern Tabs */}
      <div className="sc-league-tabs-container">
        <button className={`sc-league-tab ${activeTab === 'leaderboard' ? 'active' : ''}`} onClick={() => setActiveTab('leaderboard')}>
          Leaderboard
        </button>
        <button className={`sc-league-tab ${activeTab === 'missions' ? 'active' : ''}`} onClick={() => setActiveTab('missions')}>
          Active Missions
        </button>
        <button className={`sc-league-tab ${activeTab === 'badges' ? 'active' : ''}`} onClick={() => setActiveTab('badges')}>
          Achievements & Badges
        </button>
        <button className={`sc-league-tab ${activeTab === 'path' ? 'active' : ''}`} onClick={() => setActiveTab('path')}>
          Season Path
        </button>
      </div>

      {/* LEADERBOARD VIEW */}
      {activeTab === 'leaderboard' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* RIVALS CLASH CARD */}
          <div className="sc-rivals-card" style={{ flexWrap: 'wrap' }}>
            <div className="sc-rival-col">
              <span className="sc-rival-label">Your Circle</span>
              <strong className="sc-rival-score">{leaderboard[0].impactScore.toLocaleString()}</strong>
              <span className="sc-rival-name">{leaderboard[0].circleName}</span>
            </div>
            
            <div className="sc-rival-vs">VS</div>
            
            <div className="sc-rival-col">
              <span className="sc-rival-label">Target Rival</span>
              <strong className="sc-rival-score" style={{ color: '#f87171' }}>12,800</strong>
              <span className="sc-rival-name">Tech For Good India</span>
            </div>
            
            <div className="sc-rival-footer">
              <strong style={{ color: 'var(--sc-green-dark)' }}>Weekly Challenge:</strong> Log 5 more 1-on-1 Mentorship Hours to overtake Tech For Good India and claim the ultimate #1 spot!
            </div>
          </div>

          <div className="sc-card sc-league-table-container">
          <table className="sc-league-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Circle Name</th>
                <th>Impact Score</th>
                <th>Student Focus</th>
                <th>Funding Depth</th>
                <th>Missions</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row) => (
                <tr key={row.rank} className={row.rank === 1 ? 'my-circle-row' : ''}>
                  <td>
                    <div className="sc-flex-center gap-2">
                      {getRankIcon(row.rank)}
                      {row.change !== '0' && (
                        <span className={`sc-trend-micro ${row.change.startsWith('+') ? 'text-green' : 'text-red'}`}>
                          {row.change}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="sc-flex-center gap-2">
                      <div className="sc-circle-icon-mini" style={{ display: 'flex', alignItems: 'center' }}>
                         <UserGroupIcon style={{ width: '24px', height: '24px', color: 'var(--sc-text-muted)' }} />
                      </div>
                      <strong>{row.circleName}</strong>
                      {row.rank === 1 && <span className="sc-chip text-green">You</span>}
                    </div>
                  </td>
                  <td><strong style={{ fontSize: '1.1rem' }}>{row.impactScore.toLocaleString()}</strong></td>
                  <td>{row.studentName}</td>
                  <td>{row.coverage}</td>
                  <td>{row.missionsCompleted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* --- NEW ADDITIONS TO FILL VERTICAL SPACE --- */}
        
        <div className="sc-league-bottom-grid">
          
          {/* 1. Student Spotlight Card */}
          <div className="sc-card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ 
              height: '140px', 
              background: 'url(https://images.unsplash.com/photo-1543269865-cbf427effbad?q=80&w=1470&auto=format&fit=crop) center/cover',
              position: 'relative'
            }}>
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '50%', background: 'linear-gradient(transparent, rgba(0,0,0,0.8))' }}></div>
              <div style={{ position: 'absolute', bottom: '16px', left: '24px', color: '#fff' }}>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: '#fcd34d', fontWeight: 'bold' }}>Circle Spotlight</div>
                <h3 style={{ margin: 0, fontSize: '20px' }}>Priya's First Internship</h3>
              </div>
            </div>
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--sc-text-muted)', lineHeight: '1.6', fontStyle: 'italic' }}>
                "Thanks to the rapid IELTS coaching funded by my circle, I just cleared my international placement interview. I never thought I'd be leaving my village to work in tech."
              </p>
              <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div className="sc-badge-icon-wrap" style={{ width: 32, height: 32, background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                  <AcademicCapIcon className="w-5 h-5" />
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--sc-text-muted)' }}>Funded by</div>
                  <strong style={{ fontSize: '14px' }}>Delhi Edu-Leaders</strong>
                </div>
              </div>
            </div>
          </div>

          {/* 2. League Live Activity Feed */}
          <div className="sc-card">
            <div className="sc-card-title">League Activity Radar</div>
            <div className="sc-timeline" style={{ marginTop: '20px' }}>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80' }}/></div>
                <div className="sc-timeline-content">
                  <div><strong>Mumbai Tech</strong> fully funded Ravi's Housing Stipend!</div>
                  <span className="sc-timeline-time">2 hours ago</span>
                </div>
              </div>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fcd34d' }}/></div>
                <div className="sc-timeline-content">
                  <div><strong>Bangalore Innovators</strong> leveled up to Silver Tier!</div>
                  <span className="sc-timeline-time">14 hours ago</span>
                </div>
              </div>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#60a5fa' }}/></div>
                <div className="sc-timeline-content">
                  <div><strong>VIT Rising Circle</strong> logged +20 mentoring hours.</div>
                  <span className="sc-timeline-time">Yesterday</span>
                </div>
              </div>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#c084fc' }}/></div>
                <div className="sc-timeline-content">
                  <div><strong>Pune Changemakers</strong> unlocked 'Knowledge Sharer' badge.</div>
                  <span className="sc-timeline-time">2 days ago</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        </div>
      )}

      {/* MISSIONS VIEW */}
      {activeTab === 'missions' && (
        <div className="sc-league-missions-grid">
          {impactMissions.map(m => (
            <div key={m.id} className="sc-card sc-mission-card">
              <div className="sc-mission-header">
                <h3>{m.title}</h3>
                <span className={`sc-mission-status ${m.status === 'completed' ? 'status-completed' : 'status-active'}`}>
                  {m.status}
                </span>
              </div>
              <p className="sc-mission-desc">{m.description}</p>
              
              <div className="sc-mission-meta">
                <span><strong>Origin:</strong> {m.circle}</span>
                <span><strong>Deadline:</strong> {m.deadline}</span>
              </div>

              <div className="sc-mission-progress-block">
                <div className="sc-mission-progress-labels">
                  <span>₹{m.currentAmount.toLocaleString()} funded</span>
                  <span>₹{m.targetAmount.toLocaleString()} Goal</span>
                </div>
                <div className="sc-progress-bar">
                  <div 
                    className={`sc-progress-fill ${m.progress === 100 ? 'sc-progress-green' : ''}`} 
                    style={{ width: `${m.progress}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* BADGES VIEW */}
      {activeTab === 'badges' && (
        <div className="sc-league-badges-grid">
          {badges.map(b => {
             const Icon = b.icon
             return (
               <div key={b.id} className={`sc-badge-card ${b.earned ? 'earned' : 'locked'}`}>
                 <div className={`sc-badge-icon-box color-${b.color}`}>
                    <Icon />
                 </div>
                 <div className="sc-badge-info">
                   <h4>{b.name}</h4>
                   <p>{b.description}</p>
                   {b.earned ? (
                     <div className="sc-badge-earned-tag">
                       <SparklesIcon className="w-4 h-4" /> Earned
                     </div>
                   ) : (
                     <div className="sc-badge-progress-block">
                       <div className="sc-progress-bar" style={{ height: '6px', marginTop: '8px' }}>
                         <div className="sc-progress-fill sc-progress-green" style={{ width: `${b.progress}%` }}></div>
                       </div>
                       <span style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>{b.progress}% to unlock</span>
                     </div>
                   )}
                 </div>
               </div>
             )
          })}
        </div>
      )}

      {/* IMPACT PATH VIEW */}
      {activeTab === 'path' && (
        <div className="sc-impact-path-container">
          
          <div className="sc-card">
            <div className="sc-card-title" style={{ marginBottom: '8px' }}>Season 1 Target Path</div>
            <p className="sc-card-desc" style={{ marginBottom: '32px' }}>
              Level up your Circle tier to unlock permanent ecosystem benefits.
            </p>

            <div className="sc-path-tracker">
              <div className="sc-path-line">
                 <div className="sc-path-line-fill" style={{ width: '68%' }}></div>
              </div>

              <div className="sc-path-node unlocked">
                 <div className="sc-path-node-icon"><TrophyIcon className="w-6 h-6" /></div>
                 <span className="sc-path-node-title">Bronze Tier</span>
                 <span className="sc-path-node-req">10k Score</span>
              </div>
              
              <div className="sc-path-node unlocked">
                 <div className="sc-path-node-icon"><TrophyIcon className="w-6 h-6" /></div>
                 <span className="sc-path-node-title">Silver Tier</span>
                 <span className="sc-path-node-req">11k Score</span>
              </div>

              <div className="sc-path-node current">
                 <div className="sc-path-node-icon"><TrophyIcon className="w-6 h-6" /></div>
                 <span className="sc-path-node-title">Gold Tier</span>
                 <span className="sc-path-node-req">12k Score (You)</span>
              </div>

              <div className="sc-path-node">
                 <div className="sc-path-node-icon"><TrophyIcon className="w-6 h-6" /></div>
                 <span className="sc-path-node-title">Platinum Tier</span>
                 <span className="sc-path-node-req">15k Score</span>
              </div>
            </div>
          </div>

          <div className="sc-tier-perks-card">
             <div className="sc-tier-perks-header">
               <GiftIcon className="w-8 h-8" style={{ color: '#fbbf24' }} />
               <div>
                  <h2>Next Milestone: Platinum Tier</h2>
                  <span className="sc-badge-desc">Unlocks at 15,000 Impact Score</span>
               </div>
             </div>
             
             <div className="sc-perk-list">
               <div className="sc-perk-item">
                 <CheckCircleIcon className="w-5 h-5" />
                 <div>
                   <strong style={{ fontSize: '14px', color: 'var(--sc-text)' }}>Priority Student Matching</strong>
                   <div className="sc-badge-desc">Get access to new student intakes 48 hours before the public.</div>
                 </div>
               </div>
               <div className="sc-perk-item">
                 <CheckCircleIcon className="w-5 h-5" />
                 <div>
                   <strong style={{ fontSize: '14px', color: 'var(--sc-text)' }}>Automated 80G Certificates</strong>
                   <div className="sc-badge-desc">Instant, dynamic downloads for all verified tax compliance.</div>
                 </div>
               </div>
               <div className="sc-perk-item">
                 <CheckCircleIcon className="w-5 h-5" />
                 <div>
                   <strong style={{ fontSize: '14px', color: 'var(--sc-text)' }}>VIP Gala Invitation</strong>
                   <div className="sc-badge-desc">2 tickets to the ZENK Impact Annual Philanthropy Gala in Mumbai.</div>
                 </div>
               </div>
               <div className="sc-perk-item">
                 <CheckCircleIcon className="w-5 h-5" />
                 <div>
                   <strong style={{ fontSize: '14px', color: 'var(--sc-text)' }}>Dedicated Account Manager</strong>
                   <div className="sc-badge-desc">A direct line to our ground-ops team for custom funding requests.</div>
                 </div>
               </div>
             </div>
          </div>
        </div>
      )}

    </div>
  )
}
