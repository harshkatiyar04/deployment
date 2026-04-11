import React, { useState, useRef, useEffect } from 'react'
import { 
  ArrowDownTrayIcon, 
  DocumentArrowDownIcon, 
  TableCellsIcon 
} from '@heroicons/react/24/outline'

const MOCK_DATA = [
  { date: '1 Mar', type: '', desc: 'Opening balance', debit: '—', credit: '—', balance: '₹48,700' },
  { date: '5 Mar', type: 'School fee', tag: 'fee', desc: 'Term 2 tuition — Navodaya School', debit: '₹12,000', credit: '—', balance: '₹36,700' },
  { date: '8 Mar', type: 'Materials', tag: 'materials', desc: 'Science textbooks & stationery', debit: '₹2,400', credit: '—', balance: '₹34,300' },
  { date: '12 Mar', type: 'Deposit', tag: 'deposit', desc: 'Circle deposit received', debit: '—', credit: '₹10,000', balance: '₹44,300' },
  { date: '15 Mar', type: 'School fee', tag: 'fee', desc: 'Exam registration fee', debit: '₹4,000', credit: '—', balance: '₹40,300' },
  { date: '18 Mar', type: 'Deposit', tag: 'deposit', desc: 'Circle deposit received', debit: '—', credit: '₹8,000', balance: '₹48,300' },
  { date: '28 Mar', type: 'Interest', tag: 'interest', desc: 'Bank interest credited to circle', debit: '—', credit: '₹1,200', balance: '₹49,500' },
  { date: '30 Mar', type: 'School fee', tag: 'fee', desc: 'Transport allowance — Term 2', debit: '₹2,000', credit: '—', balance: '₹47,500' },
]

export default function SCStatementView() {
  const [showExport, setShowExport] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowExport(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const exportCSV = () => {
    const headers = ['Date', 'Type', 'Description', 'Debit', 'Credit', 'Balance']
    const rows = MOCK_DATA.map(r => [
      r.date, 
      r.type || 'N/A', 
      `"${r.desc}"`, 
      `"${r.debit}"`, 
      `"${r.credit}"`, 
      `"${r.balance}"`
    ])
    
    // Add summary row
    rows.push(['31 Mar 2026', 'Total', 'Closing balance', '₹18,400', '₹19,200', '₹47,500'])

    const csvContent = [
      headers.join(','),
      ...rows.map(e => e.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `ZENK_Statement_March_2026.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setShowExport(false)
  }

  const exportPDF = () => {
    // For a high-fidelity first pass, we trigger the print dialog which generates quality PDFs
    window.print()
    setShowExport(false)
  }

  return (
    <div className="sc-statement-view">
      {/* Header Actions */}
      <div className="sc-statement-controls">
        <select className="sc-month-select" defaultValue="March 2026" disabled>
          <option>March 2026</option>
          <option>February 2026</option>
          <option>January 2026</option>
        </select>
        
        <div className="sc-export-container" ref={dropdownRef}>
          <button className="sc-btn-outline" onClick={() => setShowExport(!showExport)}>
            <ArrowDownTrayIcon className="w-4 h-4" />
            Download Statement
          </button>
          
          {showExport && (
            <div className="sc-export-dropdown">
              <button className="sc-export-option" onClick={exportPDF}>
                <DocumentArrowDownIcon />
                Export as PDF
              </button>
              <button className="sc-export-option" onClick={exportCSV}>
                <TableCellsIcon />
                Export as Excel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="sc-summary-grid">
        <div className="sc-summary-item">
          <div className="sc-summary-label">Total collected (FY to date)</div>
          <div className="sc-summary-val green">₹1,24,500</div>
        </div>
        <div className="sc-summary-item">
          <div className="sc-summary-label">Total spent this month</div>
          <div className="sc-summary-val coral">₹18,400</div>
        </div>
        <div className="sc-summary-item">
          <div className="sc-summary-label">Closing balance</div>
          <div className="sc-summary-val dark">₹30,300</div>
        </div>
      </div>

      {/* Transaction Table */}
      <div className="sc-statement-table-wrapper">
        <table className="sc-statement-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Description</th>
              <th style={{ textAlign: 'right' }}>Debit</th>
              <th style={{ textAlign: 'right' }}>Credit</th>
              <th style={{ textAlign: 'right' }}>Balance</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_DATA.map((row, idx) => (
              <tr key={idx}>
                <td>{row.date}</td>
                <td>
                  {row.type && (
                    <span className={`sc-tag sc-tag-${row.tag}`}>
                      {row.type}
                    </span>
                  )}
                </td>
                <td style={{ color: 'var(--sc-text)', fontWeight: 500 }}>{row.desc}</td>
                <td style={{ textAlign: 'right', fontWeight: 600 }}>{row.debit}</td>
                <td style={{ textAlign: 'right', color: row.credit !== '—' ? 'var(--sc-green-dark)' : 'inherit', fontWeight: 600 }}>{row.credit}</td>
                <td style={{ textAlign: 'right', fontWeight: 700 }}>{row.balance}</td>
              </tr>
            ))}
            <tr className="closing-row">
              <td colSpan={3} style={{ fontWeight: 800 }}>Closing balance — 31 Mar 2026</td>
              <td style={{ textAlign: 'right' }}>₹18,400</td>
              <td style={{ textAlign: 'right' }}>₹19,200</td>
              <td style={{ textAlign: 'right' }}>₹47,500</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Footer Note */}
      <p className="sc-statement-footer" style={{ marginTop: '20px' }}>
        <i>All transactions verified by Sponsor Coordinator. Individual depositor names are kept private. Interest credited directly to the circle fund.</i>
      </p>
    </div>
  )
}
