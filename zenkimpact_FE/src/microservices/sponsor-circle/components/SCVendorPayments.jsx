import { useState } from 'react'
import { VENDOR_PAYMENTS } from '../data/placeholders'
import {
  BanknotesIcon,
  CheckCircleIcon,
  ClockIcon,
  PlusIcon,
  XMarkIcon,
} from '@heroicons/react/24/solid'

const fmt = (n) => '₹' + n.toLocaleString('en-IN')

const CATEGORY_COLORS = {
  'School Fees': { bg: '#dcfce7', text: '#166534' },
  'Supplies': { bg: '#e0e7ff', text: '#3730a3' },
  'Books': { bg: '#fef3c7', text: '#92400e' },
  'Uniform': { bg: '#fce7f3', text: '#9d174d' },
}

export default function SCVendorPayments() {
  const [payments, setPayments] = useState(VENDOR_PAYMENTS)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ vendor: '', amount: '', category: 'School Fees', description: '' })

  const totalPaid = payments.filter(p => p.status === 'Paid').reduce((s, p) => s + p.amount, 0)
  const totalPending = payments.filter(p => p.status === 'Pending').reduce((s, p) => s + p.amount, 0)

  const handleSubmit = (e) => {
    e.preventDefault()
    const newPayment = {
      id: payments.length + 1,
      date: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
      vendor: form.vendor,
      amount: parseInt(form.amount),
      status: 'Pending',
      category: form.category,
    }
    setPayments([newPayment, ...payments])
    setForm({ vendor: '', amount: '', category: 'School Fees', description: '' })
    setShowModal(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="sc-card" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCircleIcon style={{ width: 22, color: '#16a34a' }} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)', fontWeight: 600 }}>Total Disbursed</div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--sc-green-dark)' }}>{fmt(totalPaid)}</div>
          </div>
        </div>
        <div className="sc-card" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ClockIcon style={{ width: 22, color: '#f59e0b' }} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)', fontWeight: 600 }}>Pending Payments</div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#f59e0b' }}>{fmt(totalPending)}</div>
          </div>
        </div>
        <div className="sc-card" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: '#e0e7ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <BanknotesIcon style={{ width: 22, color: '#4f46e5' }} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)', fontWeight: 600 }}>Vendors Served</div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#4f46e5' }}>{new Set(payments.map(p => p.vendor.split('—')[0].trim())).size}</div>
          </div>
        </div>
      </div>

      {/* Make Payment + Deposit Alert */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch">
        <button
          onClick={() => setShowModal(true)}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            padding: '14px 24px', borderRadius: '12px', border: '2px dashed var(--sc-green)',
            background: 'var(--sc-green-bg)', color: 'var(--sc-green-dark)',
            fontSize: '14px', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s',
          }}
        >
          <PlusIcon style={{ width: 18 }} />
          Make Vendor Payment
        </button>
        <div style={{
          flex: 2, padding: '14px 20px', borderRadius: '12px',
          background: 'linear-gradient(90deg, #fef2f2, #fff1f2)',
          border: '1px solid #fecaca', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444', animation: 'pulse 2s infinite', flexShrink: 0 }}></div>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#991b1b', lineHeight: 1.4 }}>
              Deposit request: ₹8,000 · Due 31 Mar · School fees — Term 2
            </span>
          </div>
          <button style={{ fontSize: '12px', fontWeight: 700, padding: '6px 16px', borderRadius: '8px', background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: '12px' }}>View →</button>
        </div>
      </div>

      {/* Payment History Table */}
      <div className="sc-card overflow-hidden">
        <div className="sc-card-title p-4 sm:p-0 pb-0 sm:pb-4 mb-2 sm:mb-4">Payment History</div>
        <div className="overflow-x-auto sc-vendor-table-wrap px-4 sm:px-0">
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: '550px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 120px 100px 100px', gap: '12px', padding: '8px 0', borderBottom: '1px solid var(--sc-border)', fontSize: '11px', fontWeight: 700, color: 'var(--sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              <span>Date</span>
              <span>Vendor</span>
              <span>Category</span>
              <span>Status</span>
              <span style={{ textAlign: 'right' }}>Amount</span>
            </div>
            {payments.map((p) => {
              const catStyle = CATEGORY_COLORS[p.category] || { bg: '#f3f4f6', text: '#374151' }
              return (
                <div key={p.id} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 120px 100px 100px', gap: '12px', padding: '12px 0', borderBottom: '1px solid var(--sc-border)', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', color: 'var(--sc-text-muted)' }}>{p.date}</span>
                  <span style={{ fontSize: '13px', fontWeight: 600 }}>{p.vendor}</span>
                  <span>
                    <span style={{ fontSize: '10px', fontWeight: 600, padding: '3px 8px', borderRadius: '4px', background: catStyle.bg, color: catStyle.text, whiteSpace: 'nowrap' }}>{p.category}</span>
                  </span>
                  <span>
                    <span style={{
                      fontSize: '10px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px',
                      background: p.status === 'Paid' ? '#dcfce7' : '#fef3c7',
                      color: p.status === 'Paid' ? '#166534' : '#92400e',
                    }}>{p.status}</span>
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#dc2626', textAlign: 'right' }}>-{fmt(p.amount)}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Internal Chat Integration Card */}
      <div className="sc-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '18px', fontWeight: 700 }}>Z</div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700 }}>Ashoka Rising Circle — Internal Chat</div>
            <div style={{ fontSize: '12px', color: 'var(--sc-text-muted)' }}>6 members · Notifications on</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}></div>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#22c55e' }}>Active</span>
        </div>
      </div>

      {/* Payment Modal */}
      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{ background: '#fff', borderRadius: '16px', padding: '28px', width: '420px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Make Vendor Payment</h3>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <XMarkIcon style={{ width: 20, color: '#6b7280' }} />
              </button>
            </div>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text-muted)', display: 'block', marginBottom: '4px' }}>Vendor Name</label>
                <input
                  required
                  value={form.vendor}
                  onChange={(e) => setForm({ ...form, vendor: e.target.value })}
                  placeholder="e.g. ABC School"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--sc-border)', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text-muted)', display: 'block', marginBottom: '4px' }}>Amount (₹)</label>
                <input
                  required
                  type="number"
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  placeholder="e.g. 42000"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--sc-border)', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text-muted)', display: 'block', marginBottom: '4px' }}>Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--sc-border)', fontSize: '14px', boxSizing: 'border-box' }}
                >
                  <option>School Fees</option>
                  <option>Supplies</option>
                  <option>Books</option>
                  <option>Uniform</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--sc-text-muted)', display: 'block', marginBottom: '4px' }}>Description (Optional)</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="e.g. Term 3 fees for Ananya"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--sc-border)', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>
              <button
                type="submit"
                style={{
                  marginTop: '8px', padding: '12px', borderRadius: '10px', border: 'none',
                  background: 'var(--sc-green)', color: '#fff', fontSize: '14px', fontWeight: 700,
                  cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                Submit Payment
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
