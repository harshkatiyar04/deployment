import React, { useState, useEffect } from 'react';
import apiClient from '../../../utils/apiClient';
import {
  UserCircleIcon,
  BellIcon,
  ShieldCheckIcon,
  CreditCardIcon,
  BuildingStorefrontIcon,
  EnvelopeIcon,
  PhoneIcon,
  LockClosedIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

const ORANGE = '#f97316';
const ORANGE_DARK = '#ea580c';
const ORANGE_LIGHT = '#fff7ed';

export default function VendorSettings({ showToast }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState('profile');
  const [form, setForm] = useState({
    business_name: 'Sunrise Stationery & Books',
    full_name: 'Aman Kumar',
    contact_email: 'vendor@sunrise.com',
    phone_number: '+91 98765 43210',
    email_notifications: true,
    sms_alerts: false,
    auto_accept_orders: false,
    low_stock_threshold: 5,
    monthly_revenue_target: 50000
  });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await apiClient.get('/vendor/settings');
        setForm(prev => ({ ...prev, ...res }));
      } catch (err) {
        showToast('❌ Failed to load settings');
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.put('/vendor/settings', form);
      showToast('✅ Settings saved successfully!');
    } catch (err) {
      showToast('❌ Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  const menuItems = [
    { id: 'profile', label: 'Store Profile', icon: BuildingStorefrontIcon },
    { id: 'notifications', label: 'Notifications', icon: BellIcon },
    { id: 'security', label: 'Security & Access', icon: ShieldCheckIcon },
    { id: 'billing', label: 'Billing & Payouts', icon: CreditCardIcon },
  ];

  if (loading) return <div className="vp-skeleton" style={{ height: 500, borderRadius: 16 }} />;

  return (
    <div style={{ padding: '2px 0' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', margin: 0 }}>Portal Settings</h1>
        <p style={{ fontSize: 14, color: '#64748b', margin: '4px 0 0' }}>Manage your account preferences and store configuration.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 32, alignItems: 'start' }}>
        {/* Navigation */}
        <div style={{ background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', padding: '12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                borderRadius: 10, border: 'none', background: activeSection === item.id ? ORANGE_LIGHT : 'transparent',
                color: activeSection === item.id ? ORANGE : '#475569',
                fontWeight: 700, fontSize: 14, cursor: 'pointer', transition: 'all .2s', textAlign: 'left'
              }}
            >
              <item.icon style={{ width: 20, height: 20 }} />
              {item.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div style={{ background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: 32 }}>
            {activeSection === 'profile' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 12 }}>
                  <div style={{ width: 80, height: 80, borderRadius: '50%', background: ORANGE_LIGHT, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', border: '2px solid white', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
                    <img src={`https://ui-avatars.com/api/?name=${form.full_name}&background=f97316&color=fff`} alt="Avatar" style={{ width: '100%', height: '100%', borderRadius: '50%' }} />
                    <button style={{ position: 'absolute', bottom: -2, right: -2, background: ORANGE, color: 'white', border: '2px solid white', borderRadius: '50%', width: 28, height: 28, fontSize: 16, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>+</button>
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>{form.full_name}</h3>
                    <p style={{ margin: '2px 0 0', fontSize: 14, color: '#64748b', fontWeight: 500 }}>{form.business_name}</p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Vendor Name</label>
                    <div style={{ position: 'relative' }}>
                      <UserCircleIcon style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, color: '#94a3b8' }} />
                      <input type="text" value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} style={{ width: '100%', padding: '12px 16px 12px 42px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Business Name</label>
                    <div style={{ position: 'relative' }}>
                      <BuildingStorefrontIcon style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, color: '#94a3b8' }} />
                      <input type="text" value={form.business_name} onChange={e => setForm({...form, business_name: e.target.value})} style={{ width: '100%', padding: '12px 16px 12px 42px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Contact Email</label>
                    <div style={{ position: 'relative' }}>
                      <EnvelopeIcon style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, color: '#94a3b8' }} />
                      <input type="email" value={form.contact_email} onChange={e => setForm({...form, contact_email: e.target.value})} style={{ width: '100%', padding: '12px 16px 12px 42px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Phone Number</label>
                    <div style={{ position: 'relative' }}>
                      <PhoneIcon style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, color: '#94a3b8' }} />
                      <input type="text" value={form.phone_number} onChange={e => setForm({...form, phone_number: e.target.value})} style={{ width: '100%', padding: '12px 16px 12px 42px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Monthly Revenue Target (₹)</label>
                    <div style={{ position: 'relative' }}>
                      <CurrencyDollarIcon style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, color: '#94a3b8' }} />
                      <input type="number" value={form.monthly_revenue_target} onChange={e => setForm({...form, monthly_revenue_target: parseFloat(e.target.value)})} style={{ width: '100%', padding: '12px 16px 12px 42px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Inventory Threshold</label>
                    <input type="number" value={form.low_stock_threshold} onChange={e => setForm({...form, low_stock_threshold: parseInt(e.target.value)})} style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
                  </div>
                </div>
              </div>
            )}

            {activeSection === 'notifications' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Communication Preferences</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    { key: 'email_notifications', label: 'Order Confirmation Emails', sub: 'Receive details for every new order received.' },
                    { key: 'sms_alerts', label: 'SMS Stock Alerts', sub: 'Get text messages when items drop below threshold.' },
                    { key: 'auto_accept_orders', label: 'Auto-Accept Orders', sub: 'Skip manual confirmation for incoming orders.' },
                  ].map(pref => (
                    <label key={pref.key} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '16px', border: '1px solid #f1f5f9', borderRadius: 12, cursor: 'pointer', transition: 'background .2s' }}>
                      <div style={{ flex: 1 }}>
                        <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{pref.label}</p>
                        <p style={{ margin: '2px 0 0', fontSize: 12, color: '#64748b' }}>{pref.sub}</p>
                      </div>
                      <input 
                        type="checkbox" 
                        checked={form[pref.key]} 
                        onChange={e => setForm({...form, [pref.key]: e.target.checked})} 
                        style={{ width: 20, height: 20, accentColor: ORANGE }} 
                      />
                    </label>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'security' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Security Settings</h3>
                <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, border: '1px dashed #cbd5e1' }}>
                  <p style={{ margin: 0, fontSize: 13, color: '#475569', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <LockClosedIcon style={{ width: 18, height: 18 }} /> Two-Factor Authentication is currently <b>Disabled</b>
                  </p>
                  <button style={{ marginTop: 12, background: ORANGE, color: 'white', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Enable 2FA</button>
                </div>
              </div>
            )}

            {activeSection === 'billing' && (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <CreditCardIcon style={{ width: 48, height: 48, color: '#cbd5e1', margin: '0 auto 16px' }} />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Payout Account</h3>
                <p style={{ margin: '8px 0 20px', fontSize: 14, color: '#64748b' }}>Your current payout account is a Bank Transfer to **** 4291</p>
                <button style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>Update Payout Method</button>
              </div>
            )}
          </div>

          <div style={{ padding: '20px 32px', background: '#f8fafc', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'flex-end' }}>
            <button 
              onClick={handleSave}
              disabled={saving}
              style={{ 
                background: ORANGE, color: 'white', border: 'none', borderRadius: 10, 
                padding: '12px 32px', fontWeight: 700, fontSize: 14, 
                cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.7 : 1,
                boxShadow: '0 4px 12px rgba(249, 115, 22, 0.2)'
              }}
            >
              {saving ? 'Saving...' : 'Save All Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
