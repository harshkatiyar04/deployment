import { useState, useEffect } from 'react'
import { BUDGET } from '../data/placeholders'

const CATEGORY_CLASS = {
  Student: 'student',
  Platform: 'platform',
  Operational: 'operational',
}

export default function SCBudgetTracker() {
  const [insight, setInsight] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  
  const b = BUDGET
  const spentPct = Math.round((b.spent / b.total_budget) * 100)
  const todayPct = spentPct

  const fmt = (n) => '₹' + n.toLocaleString('en-IN')

  useEffect(() => {
    async function fetchInsight() {
      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiBase}/sponsor-circle/budget-insight`)
        const data = await res.json()
        setInsight(data)
      } catch (err) {
        console.error('Failed to fetch Kia insight:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchInsight()
  }, [])

  return (
    <div className="sc-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="sc-card-title">Budget Tracker — {b.fy_label}</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#191c1d' }}>
          {fmt(b.spent)}{' '}
          <span style={{ fontSize: 11, fontWeight: 400, color: '#6b7280' }}>of {fmt(b.total_budget)}</span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6b7280', marginBottom: 4 }}>
        <span>Spent so far</span>
      </div>

      <div className="sc-budget-bar-wrap">
        <div className="sc-budget-bar-fill" style={{ width: `${spentPct}%` }} />
        <div className="sc-budget-today" style={{ left: `${todayPct}%` }}>
          <span className="sc-budget-today-label">Today</span>
          <div className="sc-budget-today-line" />
        </div>
      </div>

      <div className="sc-budget-row-ends">
        <span>Apr 2025</span>
        <span>Mar 2026</span>
      </div>
      <div className="sc-budget-balance">Balance to spend: {fmt(b.balance_to_spend)}</div>

      <div className="sc-budget-boxes">
        <div className="sc-budget-box">
          <div className="sc-budget-box-label">Total Collected</div>
          <div className="sc-budget-box-val green">{fmt(b.collected)}</div>
        </div>
        <div className="sc-budget-box">
          <div className="sc-budget-box-label">Spent to Date</div>
          <div className="sc-budget-box-val red">{fmt(b.spent)}</div>
        </div>
        <div className="sc-budget-box">
          <div className="sc-budget-box-label">Balance</div>
          <div className="sc-budget-box-val dark">{fmt(b.collected - b.spent)}</div>
        </div>
      </div>

      {/* Kia Insight Card (Flex) - Now Live! */}
      <div className={`mt-5 p-4 rounded-xl border transition-all duration-700 ${
        isLoading ? 'bg-gray-50 border-gray-100 animate-pulse' : 'bg-[#F0FDF4] border-[#DCFCE7] shadow-sm'
      }`}>
        {isLoading ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-gray-200" />
              <div className="h-3 w-24 bg-gray-200 rounded" />
            </div>
            <div className="h-3 w-full bg-gray-200 rounded" />
            <div className="h-3 w-2/3 bg-gray-200 rounded" />
          </div>
        ) : (
          <>
            <div className="flex items-start gap-2.5 mb-2.5">
              <div className="w-6 h-6 rounded-full overflow-hidden shrink-0 shadow-sm border border-black/5">
                <img src="/kia-bot-avatar.png" alt="Kia" className="w-full h-full object-cover" />
              </div>
              <div className="flex-1">
                <div className="text-[12px] font-bold text-[#134E4A] flex items-center gap-1.5 opacity-90">
                  Kia <span className="opacity-40">•</span> Planning ahead
                </div>
                <p className="text-[13px] text-[#115E59] leading-relaxed mt-1.5 font-medium italic">
                  "{insight?.analysis}"
                </p>
              </div>
            </div>

            <div className="bg-white/80 border border-[#DCFCE7] rounded-lg p-3 shadow-sm transform transition-all hover:scale-[1.01] hover:bg-white cursor-default">
              <div className="text-[10px] font-bold text-[#0D9488] mb-1 uppercase tracking-wider opacity-70">
                Kia suggests:
              </div>
              <p className="text-[13px] text-[#14532D] font-bold leading-normal">
                {insight?.suggestion}
              </p>
            </div>
          </>
        )}
      </div>

      <div className="sc-statement-title">Recent Transactions</div>
      {b.transactions.map((txn, i) => (
        <div key={i} className="sc-txn-row">
          <span className="sc-txn-date">{txn.date}</span>
          <span className="sc-txn-desc">{txn.description}</span>
          <span className={`sc-txn-cat ${CATEGORY_CLASS[txn.category] || 'operational'}`}>{txn.category}</span>
          <span className="sc-txn-amount">{fmt(txn.amount)}</span>
        </div>
      ))}
    </div>
  )
}
