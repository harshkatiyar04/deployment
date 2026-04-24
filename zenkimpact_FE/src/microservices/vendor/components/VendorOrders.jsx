import React, { useState } from 'react';
import apiClient from '../../../utils/apiClient';
import { ClipboardDocumentListIcon } from '@heroicons/react/24/outline';

const STATUS_OPTIONS = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];

export default function VendorOrders({ orders, loading, onRefresh, showToast }) {
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = statusFilter === 'all'
    ? (orders || [])
    : (orders || []).filter(o => o.status === statusFilter);

  const handleStatusChange = async (orderId, newStatus) => {
    try {
      await apiClient.put(`/vendor/orders/${orderId}/status`, { status: newStatus });
      showToast(`✅ Order status updated to ${newStatus}`);
      onRefresh();
    } catch (err) {
      showToast(`❌ ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="vp-page-header"><div><h1>Orders</h1><p>Loading order history...</p></div></div>
        <div className="vp-card">
          <div className="vp-card-body" style={{ padding: 20 }}>
            {[1,2,3,4].map(i => <div key={i} className="vp-skeleton" style={{ width: '100%', height: 48, marginBottom: 8, borderRadius: 8 }} />)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="vp-page-header">
        <div>
          <h1>Order Management</h1>
          <p>{filtered.length} orders {statusFilter !== 'all' ? `(${statusFilter})` : 'total'}</p>
        </div>
      </div>

      {/* Status Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {['all', ...STATUS_OPTIONS].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`vp-btn vp-btn-sm ${statusFilter === s ? 'vp-btn-primary' : 'vp-btn-outline'}`}
          >{s.charAt(0).toUpperCase() + s.slice(1)}</button>
        ))}
      </div>

      <div className="vp-card">
        {filtered.length === 0 ? (
          <div className="vp-empty">
            <ClipboardDocumentListIcon />
            <h4>No orders found</h4>
            <p>{statusFilter !== 'all' ? 'Try selecting a different status filter.' : 'Orders will appear here once customers start purchasing.'}</p>
          </div>
        ) : (
          <div className="vp-card-body">
            <table className="vp-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Product</th>
                  <th>Buyer</th>
                  <th>Circle</th>
                  <th>Qty</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(order => (
                  <React.Fragment key={order.id}>
                    <tr>
                      <td style={{ fontFamily: 'monospace', fontSize: 11, color: '#94a3b8' }}>
                        {order.id.slice(0, 8)}...
                      </td>
                      <td style={{ fontWeight: 600 }}>{order.product_name || '—'}</td>
                      <td>{order.buyer_name}</td>
                      <td>{order.circle_name || '—'}</td>
                      <td>{order.quantity}</td>
                      <td style={{ fontWeight: 700 }}>₹{order.total_amount?.toLocaleString('en-IN')}</td>
                      <td><span className={`vp-badge ${order.status}`}>{order.status}</span></td>
                      <td>
                        <select
                          value={order.status}
                          onChange={e => handleStatusChange(order.id, e.target.value)}
                          style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #e2e8f0', cursor: 'pointer', outline: 'none' }}
                        >
                          {STATUS_OPTIONS.map(s => (
                            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                    <tr>
                      <td colSpan="8" style={{ backgroundColor: '#f8fafc', padding: '14px 20px', borderBottom: '1px solid #e2e8f0' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', fontSize: '12px', color: '#475569' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div><span style={{ fontWeight: 800, color: '#64748b', textTransform: 'uppercase', fontSize: '10px' }}>Logistics</span></div>
                            <div><span style={{ fontWeight: 600 }}>Type:</span> {order.order_type === 'student' ? '🎓 Student Fund' : '👤 Personal'}</div>
                            <div><span style={{ fontWeight: 600 }}>Phone:</span> {order.phone_number || 'N/A'}</div>
                            <div><span style={{ fontWeight: 600 }}>Address:</span> {order.delivery_address || 'N/A'}</div>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div><span style={{ fontWeight: 800, color: '#64748b', textTransform: 'uppercase', fontSize: '10px' }}>Transaction</span></div>
                            <div><span style={{ fontWeight: 600 }}>Ordered On:</span> {new Date(order.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</div>
                            <div><span style={{ fontWeight: 600 }}>Payment Method:</span> <span style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>{order.payment_method || 'UPI'}</span></div>
                            {order.discount_amount > 0 && <div><span style={{ fontWeight: 600, color: '#f97316' }}>Discount Applied:</span> ₹{order.discount_amount}</div>}
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div><span style={{ fontWeight: 800, color: '#64748b', textTransform: 'uppercase', fontSize: '10px' }}>Customer Info</span></div>
                            <div><span style={{ fontWeight: 600 }}>Buyer:</span> {order.buyer_name}</div>
                            <div><span style={{ fontWeight: 600 }}>Circle:</span> {order.circle_name || 'Individual'}</div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
