import React, { useState, useEffect } from 'react'
import { USER_PROFILE, LEADER_PROFILE } from '../data/placeholders'
import {
  TrophyIcon,
  FireIcon,
  SparklesIcon,
  AcademicCapIcon,
  HandRaisedIcon,
  ArrowPathIcon
} from '@heroicons/react/24/solid'
import SCJourneyAnimation from './SCJourneyAnimation'
import SCGraduateSpotlight from './SCGraduateSpotlight'
import apiClient from '../../../utils/apiClient'

const GLOBAL_NEWS_MOCK = [
  { id: 1, text: "Rural India sees 15% spike in female literacy following aggressive NGO interventions.", source: "Education Ministry", time: "2h ago", image: "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=800&q=80", url: "#" },
  { id: 2, text: "Tech consortium pledges ₹50 Crore to bridge the digital divide in village schools.", source: "Tech For Good", time: "5h ago", image: "https://images.unsplash.com/photo-1542810634-71277d95dcbb?auto=format&fit=crop&w=800&q=80", url: "#" },
  { id: 3, text: "Community micro-sponsorships via blockchain shown to increase graduation rates by 40%.", source: "Global Education Review", time: "1d ago", image: "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&w=800&q=80", url: "#" },
  { id: 4, text: "Over 10,000 students receive automated scholarship disbursements through ZenK Smart Contracts.", source: "Impact Daily", time: "2d ago", image: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=80", url: "#" },
  { id: 5, text: "New report: Transparent donation tracking leads to 3x higher sponsor retention rates.", source: "Nonprofit Quarterly", time: "3d ago", image: "https://images.unsplash.com/photo-1529390079861-591de354faf5?auto=format&fit=crop&w=800&q=80", url: "#" }
]

const BADGES = [
  { id: 1, title: 'Founding Member', desc: 'Joined ZENK Impact in the first month', icon: TrophyIcon, color: '#f08c3b', bg: '#fef3c7' },
  { id: 2, title: '6-Month Streak', desc: 'Consistent contributions for 6 months', icon: FireIcon, color: '#00694c', bg: '#e8f5f0' },
  { id: 3, title: 'First Term Funded', desc: 'Helped pay the first school fee block', icon: AcademicCapIcon, color: '#1e40af', bg: '#eff6ff' },
  { id: 4, title: 'Early Advocate', desc: 'Brought 2 new members to the circle', icon: HandRaisedIcon, color: '#6b21a8', bg: '#f3e8ff' },
]

export default function SCSponsorProfile({ isLeader = false }) {
  const PROFILE = isLeader ? LEADER_PROFILE : USER_PROFILE

  const [globalFeed, setGlobalFeed] = useState([])
  const [circleFeed, setCircleFeed] = useState([])
  const [globalIdx, setGlobalIdx] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isPaused, setIsPaused] = useState(false)

  const curateAndCategorize = (doc) => {
    const title = (doc.title || doc.webTitle || "").toLowerCase()
    const desc = (doc.description || doc.trailText || "").toLowerCase()
    const combined = title + " " + desc
    const TOXIC = ['assault', 'cop', 'police', 'arrest', 'military', 'war', 'killing', 'dead', 'shooting', 'anti-ice', 'us politics', 'uk news', 'phoenix', 'london', 'pakistan', 'conflict']
    if (TOXIC.some(word => combined.includes(word))) return null
    let category = "General Impact"
    if (combined.includes('donate') || combined.includes('pledge') || combined.includes('csr') || combined.includes('philanthropy'))
      category = "Donation Impact"
    else if (combined.includes('scholarship') || combined.includes('grant') || combined.includes('funding') || combined.includes('fundraise'))
      category = "Funding Announcements"
    else if (combined.includes('literacy') || combined.includes('dropout') || combined.includes('enrollment') || combined.includes('gender gap') || combined.includes('stats'))
      category = "Education Stats"
    else if (combined.includes('graduate') || combined.includes('benefited') || combined.includes('milestone') || combined.includes('success story'))
      category = "Success Stories"
    else if (combined.includes('akshaya patra') || combined.includes('teach for india') || combined.includes('pratham') || combined.includes('giveindia') || combined.includes('ngo') || combined.includes('foundation'))
      category = "NGO/Foundation Activity"
      
    // Relaxed filtering for demo: We require an education keyword, but we won't strictly enforce "india" 
    // because The Guardian is primarily a UK paper and doesn't always have matching articles daily.
    if (!combined.includes('edu') && !combined.includes('school') && !combined.includes('student') && !combined.includes('literacy')) return null
    
    return {
      id: doc.url || doc.webUrl || Math.random(),
      text: doc.title || doc.webTitle,
      summary: (doc.description || doc.trailText || "").split('. ').slice(0, 2).join('. ') + '.',
      category,
      source: doc.source?.name || 'The Guardian',
      time: doc.publishedAt || doc.webPublicationDate,
      image: doc.image || doc.urlToImage || doc.fields?.thumbnail || GLOBAL_NEWS_MOCK[0].image,
      url: doc.url || doc.webUrl
    }
  }



  const fetchImpactData = async () => {
    setIsLoading(true);
    try {
      // For demo purposes, we exclusively use curated thematic data 
      // instead of live political news from The Guardian.
      const curatedItems = GLOBAL_NEWS_MOCK.map(m => ({ 
        ...m, 
        type: 'GLOBAL', 
        category: 'Field Impact', 
        summary: m.text 
      }));
      
      // Artificial delay for smooth UI loading illusion
      setTimeout(() => {
        setGlobalFeed(curatedItems);
        setIsLoading(false);
      }, 600);
      
      // 3. Fetch Circle/Pulse data (Simulated/Mocked)
      await new Promise(resolve => setTimeout(resolve, 400));
      const SIMULATED_STORY = [
        { id: 'sim-1', type: 'CIRCLE', text: 'Ananya D. reached 90% attendance milestone! 🎓', source: 'Student Success', time: new Date().toISOString() },
        { id: 'sim-2', type: 'CIRCLE', text: 'New member joined: Rohit Chawla is now a supporter. 🤝', source: 'Circle Growth', time: new Date().toISOString() },
        { id: 'sim-3', type: 'CIRCLE', text: 'Circle achieved 74% participation this month! 🏆', source: 'Community', time: new Date().toISOString() },
      ]
      setCircleFeed(SIMULATED_STORY.sort(() => Math.random() - 0.5));

    } catch (err) {
      console.error("Failed to fetch live impact feed:", err);
      // Absolute fallback to mock data
      setGlobalFeed(GLOBAL_NEWS_MOCK.map(m => ({ ...m, type: 'GLOBAL', summary: m.text })));
      setCircleFeed([]);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchImpactData()
    const refreshInterval = setInterval(fetchImpactData, 15 * 60 * 1000)
    return () => clearInterval(refreshInterval)
  }, [])

  useEffect(() => {
    if (globalFeed.length === 0 || isPaused) return
    const interval = setInterval(() => {
      setGlobalIdx((prev) => (prev + 1) % globalFeed.length)
    }, 8000)
    return () => clearInterval(interval)
  }, [globalFeed, isPaused])

  const currentNews = globalFeed.length > 0 ? globalFeed[globalIdx] : null

  const handlePrev = () => setGlobalIdx(prev => (prev === 0 ? globalFeed.length - 1 : prev - 1))
  const handleNext = () => setGlobalIdx(prev => (prev + 1) % globalFeed.length)

  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return ''
    if (typeof dateStr === 'string' && dateStr.includes('ago')) return dateStr
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return dateStr
    const diff = new Date() - date
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins === 0 ? 'Just now' : mins + 'm ago'}`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return date.toLocaleDateString()
  }

  const totalContribution = isLeader ? '45,000' : '60,000'
  const circleShare = isLeader ? '36%' : '15%'
  const circleName = isLeader ? 'Ashoka Rising Circle' : 'VIT Rising Circle'
  const tier = isLeader ? 'Platinum Sponsor' : 'Gold Sponsor'
  const tierColor = isLeader ? '#64748b' : '#f08c3b'
  const tierGradient = isLeader ? 'linear-gradient(90deg, #94a3b8, #cbd5e1)' : 'linear-gradient(90deg, #f08c3b, #fcd34d)'
  const tierPercent = isLeader ? '90%' : '75%'
  const tierMessage = isLeader
    ? <span>You have unlocked <strong>Platinum</strong> status and priority matching for new students.</span>
    : <span>You are ₹15,000 away from unlocking <strong>Platinum</strong> status and priority matching for new students.</span>

  const heroBg = isLeader
    ? 'linear-gradient(135deg, #92400e 0%, #d97706 100%)'
    : 'linear-gradient(135deg, #00694c 0%, #00d084 100%)'
  const avatarRing = isLeader ? '#f59e0b' : '#00d084'

  return (
    <div className="sc-profile-view">

      {/* ── NEW PREMIUM HERO BANNER ─────────────────────────────── */}
      <div style={{
        background: heroBg,
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '4px',
        position: 'relative',
        overflow: 'hidden',
        animation: 'sc-slide-down 0.6s ease-out',
      }}>
        {/* Hex mesh SVG overlay */}
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.07 }} xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hex-profile" x="0" y="0" width="50" height="57.74" patternUnits="userSpaceOnUse">
              <polygon points="25,0 50,14.43 50,43.3 25,57.74 0,43.3 0,14.43" fill="none" stroke="white" strokeWidth="1.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hex-profile)"/>
        </svg>

        <div className="relative flex flex-col sm:flex-row sm:items-center gap-5">
          {/* Top row: Avatar & Info */}
          <div className="flex items-center gap-4 sm:gap-6 flex-1 min-w-0">
            {/* Avatar with pulse ring */}
            <div className="relative shrink-0">
              <div style={{
                position: 'absolute', inset: '-6px', borderRadius: '50%',
                border: `2px solid ${avatarRing}`,
                opacity: 0.5,
                animation: 'sc-pulse-ring 2s ease-out infinite',
              }}/>
              <div style={{
                width: 76, height: 76, borderRadius: '50%',
                background: 'rgba(255,255,255,0.2)',
                border: `3px solid ${avatarRing}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 28, fontWeight: 800, color: 'white',
                backdropFilter: 'blur(8px)',
              }}>
                {PROFILE.initials}
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-[22px] font-extrabold text-white leading-tight truncate">{PROFILE.name}</h1>
                {isLeader && (
                  <span className="text-[10px] bg-white/20 text-white px-2 py-0.5 rounded-md font-bold tracking-wider backdrop-blur-sm">
                    CIRCLE COORDINATOR
                  </span>
                )}
              </div>
              <p className="text-white/80 text-[13px] mt-1 mb-0.5 truncate">{PROFILE.circle}</p>
              <p className="text-white/65 text-[12px] m-0">
                {isLeader ? 'Coordinator' : 'Member'} since August 2025
              </p>
            </div>
          </div>

          {/* Top contributor pill (stack under on mobile, far right on desktop) */}
          <div className="shrink-0 sm:ml-auto">
            <div style={{
              background: 'rgba(255,255,255,0.15)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: '20px',
              padding: '6px 14px',
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              color: 'white', fontSize: 12, fontWeight: 700,
            }}>
              <SparklesIcon className="w-4 h-4" />
              Top 10% Contributor
            </div>
          </div>
        </div>
      </div>

      {/* ── ORIGINAL CONTENT ─────────────────────────────────────── */}
      <div className="sc-profile-grid">

        {/* Left Column */}
        <div className="sc-profile-col">

          <div className="sc-card">
            <div className="sc-card-title">My Impact Snapshot</div>
            <div className="sc-profile-stats-grid">
              <div className="sc-stat-box">
                <div className="sc-stat-label">Total Contribution</div>
                <div className="sc-stat-val text-green">₹{totalContribution}</div>
              </div>
              <div className="sc-stat-box">
                <div className="sc-stat-label">Current Streak</div>
                <div className="sc-stat-val flex items-center gap-1">
                  8 Months <FireIcon className="w-5 h-5" style={{ color: '#f08c3b' }} />
                </div>
              </div>
            </div>

            <div className="sc-share-section">
              <div className="sc-share-header">
                <span className="sc-share-title">My Circle Share</span>
                <span className="sc-share-percent">{circleShare}</span>
              </div>
              <div className="sc-progress-bar">
                <div className="sc-progress-fill sc-progress-green" style={{ width: circleShare }}></div>
              </div>
              <p className="sc-share-text">
                Your contributions make up {circleShare} of the total {circleName} fund. This translates directly to funding approx. {isLeader ? '108' : '45'} days of education per year.
              </p>
            </div>

            <div className="sc-share-section" style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid var(--sc-border)' }}>
              <div className="sc-share-header">
                <span className="sc-share-title">Sponsorship Tier</span>
                <span className="sc-share-percent" style={{ color: tierColor }}>{tier}</span>
              </div>
              <div className="sc-progress-bar">
                <div className="sc-progress-fill" style={{ width: tierPercent, background: tierGradient }}></div>
              </div>
              <p className="sc-share-text">{tierMessage}</p>
            </div>
          </div>

          <div className="sc-news-card">
            <div className="sc-news-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="sc-news-title">Global Impact Radar</span>
              <button
                onClick={() => { setIsLoading(true); fetchImpactData() }}
                className="sc-refresh-btn"
                title="Refresh feed"
                style={{ background: 'none', border: 'none', color: 'var(--sc-green)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: '600', padding: '4px 8px', borderRadius: '4px', transition: 'all 0.2s' }}
              >
                <ArrowPathIcon className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                REFRESH RADAR
              </button>
            </div>
            <div className="sc-news-body" style={{ position: 'relative' }}>
              {isLoading ? (
                <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', fontStyle: 'italic', padding: '16px' }}>
                  Syncing global impact...
                </div>
              ) : currentNews ? (
                <div key={currentNews.id} className="sc-news-ticker-item">
                  {currentNews.image && (
                    <div className="sc-news-image">
                      <img src={currentNews.image} alt="" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="sc-news-content-wrapper">
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ fontSize: '9px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '4px', background: '#00694c', color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {currentNews.category || 'IMPACT NEWS'}
                      </span>
                      <span style={{ fontSize: '9px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '4px', background: '#e8f5f0', color: '#00694c' }}>INDIA</span>
                    </div>
                    <h4 className="sc-news-headline" style={{ fontSize: '16px', lineHeight: '1.4', marginBottom: '8px', color: '#1a1a1a' }}>{currentNews.text}</h4>
                    <p style={{ fontSize: '13px', color: '#4a4a4a', lineHeight: '1.5', marginBottom: '12px', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {currentNews.summary}
                    </p>
                    <div className="sc-news-meta" style={{ borderTop: '1px solid #f0f0f0', paddingTop: '8px' }}>
                      <span style={{ color: 'var(--sc-green)', fontWeight: 'bold' }}>{currentNews.source}</span>
                      <span>•</span>
                      <span>{formatTimeAgo(currentNews.time)}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', padding: '16px' }}>No global news available.</div>
              )}
            </div>
            <div className="sc-news-footer" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: 'var(--sc-cream)', borderTop: '1px solid var(--sc-border)' }}>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <button onClick={handlePrev} style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}>← Prev</button>
                <button onClick={() => setIsPaused(!isPaused)} style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}>{isPaused ? '▶ Play' : '⏸ Pause'}</button>
                <button onClick={handleNext} style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}>Next →</button>
              </div>
              {currentNews?.url && (
                <a href={currentNews.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--sc-green-dark)', fontSize: '12px', fontWeight: '600', textDecoration: 'none' }}>
                  Read Full Story ↗
                </a>
              )}
            </div>
          </div>

          {/* ZENK Platform Pulse */}
          <div className="sc-card">
            <div className="sc-card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>ZENK Platform Pulse</span>
              <div className="sc-live-indicator">
                <div className="sc-live-pulse" /> LIVE
              </div>
            </div>
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {isLoading ? (
                <div style={{ fontSize: '13px', color: 'var(--sc-text-muted)' }}>Syncing pulse...</div>
              ) : circleFeed.slice(0, 3).map((item, idx) => (
                <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'center', paddingBottom: '16px', borderBottom: idx < 2 ? '1px solid var(--sc-border)' : 'none' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--sc-green-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '18px' }}>
                    {item.source.includes('Growth') ? '🤝' : item.source.includes('Student') ? '🎓' : '🌟'}
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--sc-text-dark)', marginBottom: '4px' }}>{item.text}</div>
                    <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)', display: 'flex', gap: '8px' }}>
                      <span style={{ color: 'var(--sc-green)', fontWeight: '600' }}>{item.source}</span>
                      <span>•</span>
                      <span>Just now</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column */}
        <div className="sc-profile-col">

          <SCJourneyAnimation />

          <div className="sc-card" style={{ height: '100%' }}>
            <div className="sc-card-title">Impact Badges</div>
            <p className="sc-card-desc" style={{ marginBottom: '16px' }}>
              Badges earned through consistent support and circle engagement.
            </p>
            <div className="sc-badges-grid">
              {BADGES.map(badge => {
                const IconComponent = badge.icon
                return (
                  <div key={badge.id} className="sc-badge-item">
                    <div className="sc-badge-icon-wrap" style={{ backgroundColor: badge.bg, color: badge.color }}>
                      <IconComponent className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="sc-badge-title">{badge.title}</div>
                      <div className="sc-badge-desc">{badge.desc}</div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="sc-card-title" style={{ marginTop: '32px' }}>Recent Activity</div>
            <div className="sc-timeline">
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--sc-green)' }} /></div>
                <div className="sc-timeline-content">
                  <div>Funded Term 2 Fees (₹12,000)</div>
                  <span className="sc-timeline-time">March 5, 2026</span>
                </div>
              </div>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--sc-green)' }} /></div>
                <div className="sc-timeline-content">
                  <div>Unlocked <strong>6-Month Streak</strong> Badge</div>
                  <span className="sc-timeline-time">February 15, 2026</span>
                </div>
              </div>
              <div className="sc-timeline-item">
                <div className="sc-timeline-icon"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--sc-green)' }} /></div>
                <div className="sc-timeline-content">
                  <div>Voted to approve Circle Budget FY26</div>
                  <span className="sc-timeline-time">January 10, 2026</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <SCGraduateSpotlight />

    </div>
  )
}
