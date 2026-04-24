import React, { useState } from 'react';
import apiClient from '../../../utils/apiClient';
import { InboxArrowDownIcon } from '@heroicons/react/24/outline';

const STATUS_OPTIONS = ['pending', 'accepted', 'fulfilled', 'rejected'];

export default function VendorRequests({ requests, loading, onRefresh, showToast }) {
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = statusFilter === 'all'
    ? (requests || [])
    : (requests || []).filter(r => r.status === statusFilter);

  const handleStatusChange = async (requestId, newStatus) => {
    const notes = newStatus === 'rejected'
      ? window.prompt('Reason for rejection (optional):') || ''
      : '';
    try {
      await apiClient.put(`/vendor/requests/${requestId}/status`, {
        status: newStatus,
        vendor_notes: notes || undefined,
      });
      showToast(`✅ Request ${newStatus}`);
      onRefresh();
    } catch (err) {
      showToast(`❌ ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="vp-page-header"><div><h1>Product Requests</h1><p>Loading leader requests...</p></div></div>
        <div className="vp-card">
          <div className="vp-card-body" style={{ padding: 20 }}>
            {[1,2,3].map(i => <div key={i} className="vp-skeleton" style={{ width: '100%', height: 48, marginBottom: 8, borderRadius: 8 }} />)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="vp-page-header">
        <div>
          <h1>Product Requests</h1>
          <p>{filtered.length} requests from Circle Leaders</p>
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
            <InboxArrowDownIcon />
            <h4>No requests found</h4>
            <p>Product requests from Circle Leaders will appear here.</p>
          </div>
        ) : (
          <div className="vp-card-body">
            <table className="vp-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Requester</th>
                  <th>Circle</th>
                  <th>Qty</th>
                  <th>Budget/Unit</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(req => (
                  <tr key={req.id}>
                    <td>
                      <div style={{ fontWeight: 700 }}>{req.title}</div>
                      {req.description && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{req.description}</div>}
                    </td>
                    <td>{req.requester_name || '—'}</td>
                    <td>{req.circle_name || '—'}</td>
                    <td>{req.quantity_needed}</td>
                    <td>{req.budget_per_unit ? `₹${req.budget_per_unit.toLocaleString('en-IN')}` : '—'}</td>
                    <td><span className={`vp-badge ${req.priority}`}>{req.priority}</span></td>
                    <td><span className={`vp-badge ${req.status}`}>{req.status}</span></td>
                    <td>
                      {req.status === 'pending' && (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="vp-btn vp-btn-primary vp-btn-sm" onClick={() => handleStatusChange(req.id, 'accepted')}>
                            Accept
                          </button>
                          <button className="vp-btn vp-btn-outline vp-btn-sm" style={{ color: '#dc2626' }} onClick={() => handleStatusChange(req.id, 'rejected')}>
                            Reject
                          </button>
                        </div>
                      )}
                      {req.status === 'accepted' && (
                        <button className="vp-btn vp-btn-primary vp-btn-sm" onClick={() => handleStatusChange(req.id, 'fulfilled')}>
                          Mark Fulfilled
                        </button>
                      )}
                      {(req.status === 'fulfilled' || req.status === 'rejected') && (
                        <span style={{ fontSize: 11, color: '#94a3b8' }}>Completed</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
