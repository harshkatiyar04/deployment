import React, { useState, useEffect } from 'react';
import apiClient from '../../../utils/apiClient';
import {
  MegaphoneIcon,
  PlusIcon,
  CalendarIcon,
  TagIcon,
  TrashIcon,
  SparklesIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';

const TEAL = '#0f766e';

export default function VendorPromotions({ products, showToast }) {
  const [promotions, setPromotions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [form, setForm] = useState({
    title: '',
    discount_percentage: 10,
    start_date: '',
    end_date: '',
    scope: 'all',
    target_product_ids: [],
    target_audience: 'all'
  });
  const [promoLogs, setPromoLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const loadPromos = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/vendor/promotions');
      setPromotions(res || []);
    } catch (err) {
      showToast('❌ Failed to load promotions');
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await apiClient.get('/vendor/promotions/log');
      setPromoLogs(res || []);
    } catch (err) {
      console.error('Failed to load logs', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => { 
    loadPromos(); 
    loadLogs();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/vendor/promotions', form);
      showToast('✅ Promotion created successfully!');
      setIsCreating(false);
      loadPromos();
      setForm({ title: '', discount_percentage: 10, start_date: '', end_date: '', scope: 'all', target_product_ids: [], target_audience: 'all' });
    } catch (err) {
      showToast(`❌ Error: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this promotion?')) return;
    try {
      await apiClient.delete(`/vendor/promotions/${id}`);
      showToast('🗑️ Promotion deleted');
      loadPromos();
    } catch (err) {
      showToast(`❌ Error: ${err.message}`);
    }
  };

  const getStatus = (promo) => {
    const now = new Date();
    const start = new Date(promo.start_date);
    const end = new Date(promo.end_date);
    if (!promo.is_active) return { label: 'Expired', color: '#94a3b8', bg: '#f1f5f9' };
    if (now < start) return { label: 'Scheduled', color: '#3b82f6', bg: '#eff6ff' };
    if (now > end) return { label: 'Expired', color: '#ef4444', bg: '#fef2f2' };
    return { label: 'Active', color: '#10b981', bg: '#ecfdf5' };
  };

  if (loading && !isCreating) return <div className="vp-skeleton" style={{ height: 400, borderRadius: 16 }} />;

  return (
    <div style={{ padding: '2px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', margin: 0 }}>Marketing & Promotions</h1>
          <p style={{ fontSize: 14, color: '#64748b', margin: '4px 0 0' }}>Manage your store's discount campaigns and special offers.</p>
        </div>
        {!isCreating && (
          <button 
            onClick={() => setIsCreating(true)}
            style={{ background: TEAL, color: 'white', border: 'none', borderRadius: 10, padding: '10px 18px', fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', boxShadow: '0 4px 12px rgba(15, 118, 110, 0.2)' }}
          >
            <PlusIcon style={{ width: 18, height: 18 }} /> Create Promotion
          </button>
        )}
      </div>

      {isCreating ? (
        <div style={{ background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', padding: 32, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>New Promotion Campaign</h2>
            <button onClick={() => setIsCreating(false)} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, padding: '6px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
          </div>
          
          <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Promotion Title</label>
                <input required type="text" placeholder="e.g. Summer Flash Sale" value={form.title} onChange={e => setForm({...form, title: e.target.value})} style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }} />
              </div>

              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Discount %</label>
                  <input required type="number" min="1" max="99" value={form.discount_percentage} onChange={e => setForm({...form, discount_percentage: parseInt(e.target.value)})} style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Scope</label>
                  <select value={form.scope} onChange={e => setForm({...form, scope: e.target.value, target_product_ids: []})} style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', background: 'white' }}>
                    <option value="all">Entire Store</option>
                    <option value="specific">Select Products</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Active Period</label>
                <div style={{ display: 'flex', gap: 12 }}>
                  <input required type="datetime-local" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} style={{ flex: 1, padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }} />
                  <input required type="datetime-local" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} style={{ flex: 1, padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }} />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Target Audience</label>
                <div style={{ display: 'flex', gap: 12 }}>
                  {[
                    { id: 'all', label: 'Both' },
                    { id: 'student', label: 'Students' },
                    { id: 'sponsor', label: 'Members' }
                  ].map(aud => (
                    <button
                      key={aud.id}
                      type="button"
                      onClick={() => setForm({...form, target_audience: aud.id})}
                      style={{
                        flex: 1, padding: '10px', borderRadius: 10, border: '1px solid',
                        borderColor: form.target_audience === aud.id ? TEAL : '#e2e8f0',
                        background: form.target_audience === aud.id ? '#f0fdfa' : 'white',
                        color: form.target_audience === aud.id ? TEAL : '#64748b',
                        fontSize: 13, fontWeight: 700, cursor: 'pointer', transition: 'all .2s'
                      }}
                    >
                      {aud.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {form.scope === 'specific' ? (
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Target Products</label>
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 12, maxHeight: 240, overflowY: 'auto', background: '#f8fafc' }}>
                    {products.map(p => (
                      <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', cursor: 'pointer', borderBottom: '1px solid #f1f5f9' }}>
                        <input type="checkbox" checked={form.target_product_ids.includes(p.id)} onChange={e => {
                          const ids = form.target_product_ids;
                          if (e.target.checked) setForm({...form, target_product_ids: [...ids, p.id]});
                          else setForm({...form, target_product_ids: ids.filter(i => i !== p.id)});
                        }} style={{ accentColor: TEAL }} />
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{p.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ background: '#f0fdfa', border: '1px solid #ccfbf1', borderRadius: 12, padding: 24, textAlign: 'center' }}>
                  <SparklesIcon style={{ width: 40, height: 40, color: TEAL, margin: '0 auto 16px' }} />
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#0f172a' }}>Global Discount Active</h3>
                  <p style={{ margin: '8px 0 0', fontSize: 13, color: '#0d9488', lineHeight: 1.5 }}>This promotion will be applied to every product in your inventory during the specified time period.</p>
                </div>
              )}

              <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                <button type="submit" style={{ background: TEAL, color: 'white', border: 'none', borderRadius: 10, padding: '12px 24px', fontWeight: 700, fontSize: 14, cursor: 'pointer', flex: 1 }}>Launch Campaign</button>
              </div>
            </div>
          </form>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 20 }}>
            {promotions.length === 0 ? (
              <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '80px 0', background: 'white', borderRadius: 20, border: '1px solid #e2e8f0' }}>
                <MegaphoneIcon style={{ width: 48, height: 48, color: '#cbd5e1', margin: '0 auto 16px' }} />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#475569' }}>No promotions found</h3>
                <p style={{ margin: '4px 0 0', fontSize: 14, color: '#94a3b8' }}>Create your first campaign to boost your sales.</p>
              </div>
            ) : (
              promotions.map(promo => {
                const status = getStatus(promo);
                return (
                  <div key={promo.id} style={{ background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, position: 'relative', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <div style={{ background: status.bg, color: status.color, padding: '4px 10px', borderRadius: 99, fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.5px' }}>{status.label}</div>
                        {promo.expires_in_hours > 0 && promo.expires_in_hours <= 24 && (
                          <div style={{ background: '#fff7ed', color: '#ea580c', padding: '4px 10px', borderRadius: 99, fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <ClockIcon style={{ width: 12, height: 12 }} />
                            Expiring in {promo.expires_in_hours}h
                          </div>
                        )}
                      </div>
                      <button onClick={() => handleDelete(promo.id)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }} onMouseEnter={e => e.currentTarget.style.color = '#ef4444'} onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}><TrashIcon style={{ width: 18, height: 18 }} /></button>
                    </div>
                    <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>{promo.title}</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '8px 0 16px' }}>
                      <TagIcon style={{ width: 14, height: 14, color: TEAL }} />
                      <span style={{ fontSize: 14, fontWeight: 800, color: TEAL }}>{promo.discount_percentage}% OFF</span>
                      <span style={{ fontSize: 12, color: '#94a3b8' }}>• {promo.scope === 'all' ? 'All Products' : 'Selected items'}</span>
                    </div>
                    
                    {promo.scope === 'specific' && promo.target_product_names?.length > 0 && (
                      <div style={{ marginBottom: 12, padding: '0 4px' }}>
                        <p style={{ fontSize: 11, color: '#64748b', margin: 0, fontWeight: 600 }}>Applied to:</p>
                        <p style={{ fontSize: 11, color: '#94a3b8', margin: '2px 0 0', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {promo.target_product_names.join(', ')}
                        </p>
                      </div>
                    )}
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
                      <UsersIcon style={{ width: 14, height: 14, color: '#64748b' }} />
                      <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600 }}>
                        Target: {promo.target_audience === 'all' ? 'Both' : promo.target_audience === 'student' ? 'Students' : 'Members'}
                      </span>
                    </div>

                    <div style={{ background: '#f8fafc', borderRadius: 10, padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b' }}>
                        <CalendarIcon style={{ width: 14, height: 14 }} />
                        <span>Starts: {new Date(promo.start_date).toLocaleString()}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b' }}>
                        <ClockIcon style={{ width: 14, height: 14 }} />
                        <span>Ends: {new Date(promo.end_date).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div style={{ background: 'white', borderRadius: 20, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Promotion & Discount Log</h2>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>History of orders where promotions were applied.</p>
              </div>
              <button onClick={loadLogs} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '6px 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Refresh Log</button>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    <th style={{ padding: '12px 24px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Date</th>
                    <th style={{ padding: '12px 24px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Product</th>
                    <th style={{ padding: '12px 24px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Qty</th>
                    <th style={{ padding: '12px 24px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Discount Given</th>
                    <th style={{ padding: '12px 24px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Final Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {promoLogs.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ padding: '40px 0', textAlign: 'center', color: '#94a3b8', fontSize: 14 }}>No promotion logs found yet.</td>
                    </tr>
                  ) : (
                    promoLogs.map(log => (
                      <tr key={log.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '16px 24px', fontSize: 13, color: '#0f172a' }}>{new Date(log.created_at).toLocaleDateString()}</td>
                        <td style={{ padding: '16px 24px', fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{log.product_name}</td>
                        <td style={{ padding: '16px 24px', fontSize: 13, color: '#64748b' }}>{log.quantity}</td>
                        <td style={{ padding: '16px 24px', fontSize: 13, fontWeight: 700, color: '#ef4444' }}>-₹{log.discount_amount?.toFixed(2)}</td>
                        <td style={{ padding: '16px 24px', fontSize: 13, fontWeight: 700, color: '#0f172a' }}>₹{log.total_amount?.toFixed(2)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
