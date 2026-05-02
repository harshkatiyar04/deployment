import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid } from 'recharts';
import '../csr_styles.css';

const fmt = (n) => `₹${(n || 0).toLocaleString('en-IN')}`;

export default function CorpCSRAccount({ csrAccount, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [showDisbursementModal, setShowDisbursementModal] = useState(false);
  const [newDisbursement, setNewDisbursement] = useState({
    circle_name: '', amount: '', due_date: '', status: 'scheduled', tranche: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const itemsPerPage = 5;

  if (!csrAccount) return <div className="c-skeleton" style={{ height: 400 }} />;

  // Ledger Search and Pagination
  const filteredTxns = useMemo(() => {
    if (!csrAccount.transactions) return [];
    if (!searchTerm) return csrAccount.transactions;
    const lower = searchTerm.toLowerCase();
    return csrAccount.transactions.filter(t => 
      t.description.toLowerCase().includes(lower) || 
      t.category.toLowerCase().includes(lower) ||
      (t.reference && t.reference.toLowerCase().includes(lower))
    );
  }, [csrAccount.transactions, searchTerm]);

  const totalPages = Math.ceil(filteredTxns.length / itemsPerPage);
  const currentTxns = filteredTxns.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const CustomPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', padding: '10px', borderRadius: '8px', color: '#fff' }}>
          <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '4px' }}>{payload[0].name}</div>
          <div style={{ fontWeight: 'bold' }}>{fmt(payload[0].value)}</div>
        </div>
      );
    }
    return null;
  };

  const CustomAreaTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', padding: '10px', borderRadius: '8px', color: '#fff' }}>
          <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '4px' }}>{label}</div>
          <div style={{ fontWeight: 'bold', color: '#F54A4A' }}>Burn: {fmt(payload[0].value)}</div>
        </div>
      );
    }
    return null;
  };

  const handleDownloadLedger = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://deployment-production-27bd.up.railway.app');
      const response = await fetch(`${API_BASE}/corporate/impact/annual-report`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to download report');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ZenK_Corporate_Ledger_${new Date().getFullYear()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Could not download ledger. Ensure you are authenticated.');
    }
  };

  const handleAddDisbursement = async () => {
    if (!newDisbursement.circle_name || !newDisbursement.amount || !newDisbursement.due_date) {
      alert("Please fill all required fields.");
      return;
    }
    try {
      setIsSubmitting(true);
      const token = localStorage.getItem('access_token');
      const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://deployment-production-27bd.up.railway.app');
      
      const payload = { ...newDisbursement, amount: parseInt(newDisbursement.amount) || 0 };
      const response = await fetch(`${API_BASE}/corporate/csr-account/disbursements`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        setShowDisbursementModal(false);
        setNewDisbursement({ circle_name: '', amount: '', due_date: '', status: 'scheduled', tranche: '' });
        if (onRefresh) onRefresh();
      } else {
        alert("Failed to add disbursement");
      }
    } catch (err) {
      console.error(err);
      alert("Error adding disbursement");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteDisbursement = async (index) => {
    if (!window.confirm("Are you sure you want to delete this disbursement?")) return;
    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://deployment-production-27bd.up.railway.app');
      
      const response = await fetch(`${API_BASE}/corporate/csr-account/disbursements/${index}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        if (onRefresh) onRefresh();
      } else {
        alert("Failed to delete disbursement");
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="csr-grid">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        <div className="csr-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ margin: '0 0 4px 0', fontSize: '24px', fontWeight: '600', color: '#1a1a1a' }}>Account Overview</h2>
            <div style={{ color: '#6c757d', fontSize: '14px', marginBottom: '24px' }}>
              Account #: {csrAccount.account_number} • {csrAccount.fy_label}
              <span style={{ marginLeft: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px', color: csrAccount.compliance_status === 'on_track' ? '#0CBEAA' : '#F0A500' }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                Compliance {csrAccount.compliance_status.replace('_', ' ')}
              </span>
            </div>
            
            <div className="csr-stat-row">
              <div className="csr-stat-box">
                <div className="csr-stat-label">Total Received</div>
                <div className="csr-stat-value">{fmt(csrAccount.total_received)}</div>
              </div>
              <div className="csr-stat-box">
                <div className="csr-stat-label">Total Deployed</div>
                <div className="csr-stat-value">{fmt(csrAccount.total_deployed)}</div>
              </div>
              <div className="csr-stat-box">
                <div className="csr-stat-label">Current Balance</div>
                <div className="csr-stat-value" style={{ color: '#F0A500' }}>{fmt(csrAccount.balance)}</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#6c757d', marginBottom: '8px' }}>
              <span style={{ fontWeight: '500' }}>Mandate Progress</span>
              <span style={{ fontWeight: '600' }}>{csrAccount.mandate_used_pct}% deployed of {fmt(csrAccount.mandate_amount)}</span>
            </div>
            <div className="csr-mandate-track">
              <div className="csr-mandate-fill" style={{ width: `${csrAccount.mandate_used_pct}%` }} />
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="csr-card">
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#1a1a1a' }}>Quick Actions</h3>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="csr-btn-primary" style={{ flex: 1 }} onClick={() => setShowTopUpModal(true)}>
                + Add Funds / Top-up
              </button>
              <button className="csr-btn-secondary" style={{ flex: 1 }} onClick={handleDownloadLedger}>
                Download Ledger (PDF)
              </button>
            </div>
          </div>

          <div className="csr-card" style={{ flex: 1 }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#1a1a1a' }}>Notifications</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {csrAccount.alerts && csrAccount.alerts.map((a, i) => {
                const isObj = typeof a === 'object';
                const type = isObj ? a.type : 'info';
                const message = isObj ? a.message : a;
                return (
                  <div key={i} style={{ 
                    padding: '12px 16px', 
                    background: type === 'info' ? '#f0f4ff' : '#fff8e5', 
                    color: '#1a1a1a', 
                    borderRadius: '8px', 
                    fontSize: '13px', 
                    lineHeight: '1.4',
                    borderLeft: `4px solid ${type === 'info' ? '#4A72F5' : '#F0A500'}` 
                  }}>
                    {message}
                  </div>
                );
              })}
              {(!csrAccount.alerts || csrAccount.alerts.length === 0) && (
                <div style={{ color: '#6c757d', fontSize: '13px' }}>No new notifications.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="csr-charts-grid">
        <div className="csr-card">
          <div className="c-card-title">Allocation by Category</div>
          <div style={{ height: '240px', marginTop: '16px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={csrAccount.spend_by_category}
                  cx="50%" cy="50%"
                  innerRadius={60} outerRadius={80}
                  paddingAngle={5}
                  dataKey="amount"
                  nameKey="category"
                  stroke="none"
                >
                  {csrAccount.spend_by_category.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', marginTop: '16px' }}>
            {csrAccount.spend_by_category.map((cat, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#6c757d' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: cat.color }} />
                {cat.category}
              </div>
            ))}
          </div>
        </div>

        <div className="csr-card">
          <div className="c-card-title">Monthly Burn Rate</div>
          <div style={{ height: '240px', marginTop: '16px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={csrAccount.monthly_burn} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorBurn" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F54A4A" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#F54A4A" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" stroke="#a0a0a0" fontSize={12} tickMargin={10} />
                <YAxis stroke="#a0a0a0" fontSize={12} tickFormatter={(val) => `₹${val/1000}k`} />
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <RechartsTooltip content={<CustomAreaTooltip />} />
                <Area type="monotone" dataKey="amount" stroke="#F54A4A" strokeWidth={2} fillOpacity={1} fill="url(#colorBurn)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="csr-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div className="c-card-title" style={{ margin: 0 }}>Upcoming Scheduled Disbursements</div>
          <button className="csr-btn-secondary" style={{ padding: '6px 12px', fontSize: '13px' }} onClick={() => setShowDisbursementModal(true)}>
            + Add Disbursement
          </button>
        </div>
        
        {(!csrAccount.upcoming_disbursements || csrAccount.upcoming_disbursements.length === 0) ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#888', background: '#f8f9fa', borderRadius: '12px' }}>
            No upcoming disbursements scheduled.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {csrAccount.upcoming_disbursements.map((d, i) => (
              <div key={i} style={{ background: '#f8f9fa', padding: '16px', borderRadius: '12px', border: '1px solid #e8e8e4', position: 'relative' }}>
                <button 
                  onClick={() => handleDeleteDisbursement(i)}
                  style={{ position: 'absolute', top: '12px', right: '12px', background: 'none', border: 'none', color: '#F54A4A', cursor: 'pointer', opacity: 0.6 }}
                  title="Delete Disbursement"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', paddingRight: '24px' }}>
                  <span style={{ fontWeight: '600', color: '#1a1a1a' }}>{d.circle_name}</span>
                  <span style={{ color: '#F0A500', fontWeight: 'bold' }}>{fmt(d.amount)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#6c757d' }}>
                  <span>{d.tranche} • Due: {d.due_date}</span>
                  <span style={{ color: d.status === 'scheduled' ? '#4A72F5' : '#888' }}>{d.status.replace('_', ' ')}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="csr-card">
        <div className="csr-table-controls">
          <div className="c-card-title" style={{ margin: 0 }}>Transaction Ledger</div>
          <input 
            type="text" 
            className="csr-search-input" 
            placeholder="Search by ref, category or description..." 
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          />
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <table className="csr-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Reference</th>
                <th>Description</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Running Balance</th>
              </tr>
            </thead>
            <tbody>
              {currentTxns.map((t, i) => (
                <tr key={i}>
                  <td style={{ whiteSpace: 'nowrap' }}>{t.date}</td>
                  <td style={{ color: '#6c757d', fontSize: '13px' }}>{t.reference || '—'}</td>
                  <td>
                    <div style={{ color: '#1a1a1a', fontWeight: '500' }}>{t.description}</div>
                    {t.circle && <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>Circle: {t.circle}</div>}
                  </td>
                  <td>{t.category}</td>
                  <td>
                    <span className={`csr-badge ${t.type}`}>
                      {t.type === 'credit' ? '+' : t.type === 'debit' ? '−' : '+'}{fmt(t.amount)}
                    </span>
                  </td>
                  <td style={{ fontWeight: 'bold', color: '#333' }}>
                    {t.running_balance !== undefined ? fmt(t.running_balance) : '—'}
                  </td>
                </tr>
              ))}
              {currentTxns.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: '#6c757d' }}>No transactions found for "{searchTerm}"</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="csr-pagination">
            <button className="csr-page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}>&lsaquo;</button>
            {Array.from({ length: totalPages }).map((_, i) => (
              <button 
                key={i} 
                className={`csr-page-btn ${currentPage === i + 1 ? 'active' : ''}`}
                onClick={() => setCurrentPage(i + 1)}
              >
                {i + 1}
              </button>
            ))}
            <button className="csr-page-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}>&rsaquo;</button>
          </div>
        )}
      </div>

      {showTopUpModal && (
        <div className="c-modal-overlay">
          <div className="c-modal" style={{ maxWidth: 450 }}>
            <div className="c-modal-header">
              <h3>Top-Up Escrow Account</h3>
              <button onClick={() => setShowTopUpModal(false)}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
            </div>
            <div className="c-modal-body" style={{ padding: '24px' }}>
              <p style={{ color: '#666', fontSize: 14, marginBottom: 24, lineHeight: 1.5 }}>
                Top-ups to the ZenK CSR Escrow are facilitated via secure RTGS/NEFT transfers.
              </p>
              <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '8px', border: '1px solid #eee', marginBottom: 24 }}>
                <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>Virtual Account Number</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', letterSpacing: '1px' }}>{csrAccount.account_number}</div>
                <div style={{ fontSize: 13, color: '#888', marginTop: 12, marginBottom: 4 }}>IFSC Code</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#1a1a1a' }}>HDFC0000ZNK</div>
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="csr-btn-secondary" style={{ flex: 1 }} onClick={() => setShowTopUpModal(false)}>Cancel</button>
                <button className="csr-btn-primary" style={{ flex: 1 }} onClick={() => {
                  alert("Transfer details copied. Proceed via your corporate banking portal.");
                  setShowTopUpModal(false);
                }}>Copy Details</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDisbursementModal && (
        <div className="c-modal-overlay">
          <div className="c-modal" style={{ maxWidth: 500 }}>
            <div className="c-modal-header">
              <h3>Add Disbursement</h3>
              <button onClick={() => setShowDisbursementModal(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div className="c-modal-body" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Circle Name</label>
                <input type="text" className="csr-search-input" style={{ width: '100%', marginBottom: 0 }}
                  value={newDisbursement.circle_name} onChange={e => setNewDisbursement({...newDisbursement, circle_name: e.target.value})} placeholder="e.g. Ashoka Rising Circle" />
              </div>
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Amount (₹)</label>
                  <input type="number" className="csr-search-input" style={{ width: '100%', marginBottom: 0 }}
                    value={newDisbursement.amount} onChange={e => setNewDisbursement({...newDisbursement, amount: e.target.value})} placeholder="20000" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Due Date</label>
                  <input type="text" className="csr-search-input" style={{ width: '100%', marginBottom: 0 }}
                    value={newDisbursement.due_date} onChange={e => setNewDisbursement({...newDisbursement, due_date: e.target.value})} placeholder="e.g. Apr 1, 2026" />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Tranche</label>
                  <input type="text" className="csr-search-input" style={{ width: '100%', marginBottom: 0 }}
                    value={newDisbursement.tranche} onChange={e => setNewDisbursement({...newDisbursement, tranche: e.target.value})} placeholder="e.g. Q1 FY26-27" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Status</label>
                  <select className="csr-search-input" style={{ width: '100%', marginBottom: 0 }}
                    value={newDisbursement.status} onChange={e => setNewDisbursement({...newDisbursement, status: e.target.value})}>
                    <option value="scheduled">Scheduled</option>
                    <option value="pending_approval">Pending Approval</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button className="csr-btn-secondary" style={{ flex: 1 }} onClick={() => setShowDisbursementModal(false)}>Cancel</button>
                <button className="csr-btn-primary" style={{ flex: 1 }} onClick={handleAddDisbursement} disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Save Disbursement'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
