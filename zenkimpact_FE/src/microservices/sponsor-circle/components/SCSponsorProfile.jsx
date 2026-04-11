import React, { useState, useEffect } from 'react'
import { USER_PROFILE } from '../data/placeholders'
import {
  TrophyIcon,
  FireIcon,
  StarIcon,
  SparklesIcon,
  AcademicCapIcon,
  HandRaisedIcon,
  ArrowPathIcon
} from '@heroicons/react/24/solid'
import SCJourneyAnimation from './SCJourneyAnimation'
import SCGraduateSpotlight from './SCGraduateSpotlight'

const GLOBAL_NEWS_MOCK = [
  { id: 1, text: "Global literacy rates reach an all-time high of 87%.", source: "UNESCO Update", time: "2m ago", image: "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=800&q=80", url: "https://www.unesco.org/en/education" },
  { id: 2, text: "Tech billionaire pledges $1B to bridge the rural digital divide.", source: "Tech For Good", time: "15m ago", image: "https://images.unsplash.com/photo-1542810634-71277d95dcbb?auto=format&fit=crop&w=800&q=80", url: "https://news.google.com/search?q=philanthropy+rural+education" },
  { id: 3, text: "Community micro-sponsorships shown to increase graduation rates by 40%.", source: "Global Education Review", time: "1h ago", image: "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&w=800&q=80", url: "https://news.google.com/search?q=education+micro-sponsorships" },
]

const BADGES = [
  { id: 1, title: 'Founding Member', desc: 'Joined ZENK Impact in the first month', icon: TrophyIcon, color: '#f08c3b', bg: '#fef3c7' },
  { id: 2, title: '6-Month Streak', desc: 'Consistent contributions for 6 months', icon: FireIcon, color: '#00694c', bg: '#e8f5f0' },
  { id: 3, title: 'First Term Funded', desc: 'Helped pay the first school fee block', icon: AcademicCapIcon, color: '#1e40af', bg: '#eff6ff' },
  { id: 4, title: 'Early Advocate', desc: 'Brought 2 new members to the circle', icon: HandRaisedIcon, color: '#6b21a8', bg: '#f3e8ff' },
]

export default function SCSponsorProfile() {
  const [globalFeed, setGlobalFeed] = useState([])
  const [circleFeed, setCircleFeed] = useState([])

  const [globalIdx, setGlobalIdx] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isPaused, setIsPaused] = useState(false)

  // THE EDITORIAL CURATOR ENGINE
  const curateAndCategorize = (doc) => {
    const title = (doc.title || doc.webTitle || "").toLowerCase()
    const desc = (doc.description || doc.trailText || "").toLowerCase()
    const combined = title + " " + desc
    
    // 1. Strict India-Centric Rejected (Check for other countries/violence)
    const TOXIC = ['assault', 'cop', 'police', 'arrest', 'military', 'war', 'killing', 'dead', 'shooting', 'anti-ice', 'us politics', 'uk news', 'phoenix', 'london', 'pakistan', 'conflict']
    if (TOXIC.some(word => combined.includes(word))) return null
    
    // 2. Identify Indian Category
    let category = "General Impact"
    if (combined.includes('donate') || combined.includes('pledge') || combined.includes('csr') || combined.includes('philanthropy')) 
      category = "Donation Impact"
    else if (combined.includes('scholarship') || combined.includes('grant') || combined.includes('funding') || combined.includes('fundraise')) 
      category = "Funding Announcements"
    else if (combined.includes('literacy') || combined.includes('dropout') || combined.includes('enrollment') || combined.includes('gender gap') || combined.includes('stats')) 
      category = "Education Stats"
    else if (combined.includes('graduate') || combined.includes('benefited') || combined.includes('milestone') || combined.includes('pm poshan') || combined.includes('success story')) 
      category = "Success Stories"
    else if (combined.includes('akshaya patra') || combined.includes('teach for india') || combined.includes('pratham') || combined.includes('giveindia') || combined.includes('ngo') || combined.includes('foundation')) 
      category = "NGO/Foundation Activity"

    // If it doesn't even mention India or Education strongly, reject (EDITORIAL REJECTION)
    if (!combined.includes('india') && !combined.includes('indian')) return null
    if (!combined.includes('edu') && !combined.includes('school') && !combined.includes('student') && !combined.includes('literacy')) return null

    return {
      id: doc.url || doc.webUrl || Math.random(),
      text: doc.title || doc.webTitle,
      summary: (doc.description || doc.trailText || "").split('. ').slice(0, 2).join('. ') + '.',
      category: category,
      source: doc.source?.name || 'The Guardian',
      time: doc.publishedAt || doc.webPublicationDate,
      image: doc.image || doc.urlToImage || doc.fields?.thumbnail || GLOBAL_NEWS_MOCK[0].image,
      url: doc.url || doc.webUrl
    }
  }

  const fetchImpactData = async () => {
    try {
      const gnewsKey = 'e3d9cf8ba124ee84dc994f9047b3cb80'
      const newsApiKey = '869deb62e3ad4e98b3305acd694f49b2'
      
      // 1. PRIMARY: GNEWS (Country: IN) - Strictly Curated
      const gnewsQuery = encodeURIComponent('("education" OR "literacy" OR "donation" OR "scholarship") AND ("India" OR "NGO")')
      const gnewsUrl = `https://gnews.io/api/v4/search?q=${gnewsQuery}&country=in&lang=en&apikey=${gnewsKey}`
      
      const newsRes = await fetch(gnewsUrl)
      const newsData = await newsRes.json()
      
      let items = []
      if (newsData.articles) {
        items = newsData.articles.map(curateAndCategorize).filter(Boolean)
      }

      // 2. FALLBACK: NewsAPI (Strict Query for Indian NGOs)
      if (items.length < 3) {
        const fallbackQuery = encodeURIComponent('("education India" OR "scholarship India" OR "Akshaya Patra" OR "Teach For India")')
        const fallbackUrl = `https://newsapi.org/v2/everything?q=${fallbackQuery}&language=en&sortBy=publishedAt&pageSize=20&apiKey=${newsApiKey}`
        const fbRes = await fetch(fallbackUrl)
        const fbData = await fbRes.json()
        if (fbData.articles) {
          const fbItems = fbData.articles.map(curateAndCategorize).filter(Boolean)
          items = [...items, ...fbItems]
        }
      }
      
      // FALLBACK TO MOCK if world results fail
      if (items.length === 0) items = GLOBAL_NEWS_MOCK.map(m => ({ ...m, type: 'GLOBAL', category: 'Education Stats', summary: m.text }))
      
      setGlobalFeed(items)

      // 3. Local Circle Activity
      const activityRes = await fetch('http://localhost:8000/sponsor-circle/budget')
      const activityData = await activityRes.json()

      let cItems = []
      if (activityData.transactions) {
        cItems = activityData.transactions.map((t, i) => ({
          id: `act-${i}`,
          type: 'CIRCLE',
          text: `${t.description}: ${t.amount > 0 ? '₹' + t.amount.toLocaleString() : ''} - Impact applied.`,
          source: t.category,
          time: new Date().toISOString(),
        }))
      }

      // Add high-fidelity "Charity" style simulation items
      const SIMULATED_STORY = [
        { id: 'sim-1', type: 'CIRCLE', text: 'Ananya D. reached 90% attendance milestone! 🎓', source: 'Student Success', time: new Date().toISOString() },
        { id: 'sim-2', type: 'CIRCLE', text: 'New member joined: Rohit Chawla is now a supporter. 🤝', source: 'Circle Growth', time: new Date().toISOString() },
        { id: 'sim-3', type: 'CIRCLE', text: 'Circle achieved 74% participation this month! 🏆', source: 'Community', time: new Date().toISOString() },
      ]

      cItems = [...cItems, ...SIMULATED_STORY]
      cItems.sort(() => Math.random() - 0.5)
      setCircleFeed(cItems)

    } catch (err) {
      console.error("Failed to fetch impact feed:", err)
      setGlobalFeed(GLOBAL_NEWS_MOCK.map(m => ({ ...m, type: 'GLOBAL' })))
      setCircleFeed([])
    } finally {
      setIsLoading(false)
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

  // Navigation handlers
  const handlePrev = () => {
    setGlobalIdx(prev => (prev === 0 ? globalFeed.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setGlobalIdx(prev => (prev + 1) % globalFeed.length)
  }

  // Live Timer Helper
  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    if (typeof dateStr === 'string' && dateStr.includes('ago')) return dateStr;
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;

    const diff = new Date() - date
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins === 0 ? 'Just now' : mins + 'm ago'}`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="sc-profile-view">

      {/* Premium Header Banner */}
      <div className="sc-profile-header-banner">
        <div className="sc-profile-avatar-large">
          {USER_PROFILE.initials}
        </div>
        <div className="sc-profile-header-info">
          <h1>{USER_PROFILE.name}</h1>
          <p className="sc-profile-header-sub">
            {USER_PROFILE.circle} • Member since August 2025
          </p>
        </div>
        <div className="sc-profile-badge-featured">
          <SparklesIcon className="w-5 h-5 text-yellow-500" />
          <span>Top 10% Contributor</span>
        </div>
      </div>

      <div className="sc-profile-grid">

        {/* Left Column: Stats & Contribution */}
        <div className="sc-profile-col">

          <div className="sc-card">
            <div className="sc-card-title">My Impact Snapshot</div>

            <div className="sc-profile-stats-grid">
              <div className="sc-stat-box">
                <div className="sc-stat-label">Total Contribution</div>
                <div className="sc-stat-val text-green">₹60,000</div>
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
                <span className="sc-share-percent">15%</span>
              </div>
              <div className="sc-progress-bar">
                <div className="sc-progress-fill sc-progress-green" style={{ width: '15%' }}></div>
              </div>
              <p className="sc-share-text">
                Your contributions make up 15% of the total VIT Rising Circle fund. This translates directly to funding approx. 45 days of education per year.
              </p>
            </div>

            {/* Sponsorship Tier */}
            <div className="sc-share-section" style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid var(--sc-border)' }}>
              <div className="sc-share-header">
                <span className="sc-share-title">Sponsorship Tier</span>
                <span className="sc-share-percent" style={{ color: '#f08c3b' }}>Gold Sponsor</span>
              </div>
              <div className="sc-progress-bar">
                <div className="sc-progress-fill" style={{ width: '75%', background: 'linear-gradient(90deg, #f08c3b, #fcd34d)' }}></div>
              </div>
              <p className="sc-share-text">
                You are ₹15,000 away from unlocking <strong>Platinum</strong> status and priority matching for new students.
              </p>
            </div>
          </div>

          <div className="sc-news-card">
            <div className="sc-news-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="sc-news-title">Global Impact Radar</span>
              <button 
                onClick={() => {
                  setIsLoading(true)
                  fetchImpactData()
                }}
                className="sc-refresh-btn"
                title="Refresh feed"
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--sc-green)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  fontWeight: '600',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  transition: 'all 0.2s'
                }}
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
                      <span style={{ 
                        fontSize: '9px', 
                        fontWeight: 'bold', 
                        padding: '2px 8px', 
                        borderRadius: '4px',
                        background: '#00694c',
                        color: '#ffffff',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        {currentNews.category || 'IMPACT NEWS'}
                      </span>
                      <span style={{ 
                        fontSize: '9px', 
                        fontWeight: 'bold', 
                        padding: '2px 8px', 
                        borderRadius: '4px',
                        background: '#e8f5f0',
                        color: '#00694c',
                      }}>
                        INDIA
                      </span>
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
                <div style={{ textAlign: 'center', color: 'var(--sc-text-muted)', fontSize: '13px', padding: '16px' }}>
                  No global news available.
                </div>
              )}
            </div>
            <div className="sc-news-footer" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: 'var(--sc-cream)', borderTop: '1px solid var(--sc-border)' }}>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <button
                  onClick={handlePrev}
                  style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
                >
                  &larr; Prev
                </button>
                <button
                  onClick={() => setIsPaused(!isPaused)}
                  style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
                >
                  {isPaused ? '▶ Play' : '⏸ Pause'}
                </button>
                <button
                  onClick={handleNext}
                  style={{ background: 'none', border: 'none', color: 'var(--sc-text)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
                >
                  Next &rarr;
                </button>
              </div>
              {currentNews && currentNews.url && (
                <a
                  href={currentNews.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: 'var(--sc-green-dark)', fontSize: '12px', fontWeight: '600', textDecoration: 'none' }}
                >
                  Read Full Story &nearr;
                </a>
              )}
            </div>
          </div>

          {/* Dedicated ZENK Circle Activity Feed */}
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

        {/* Right Column: Badges & Rewards */}
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
