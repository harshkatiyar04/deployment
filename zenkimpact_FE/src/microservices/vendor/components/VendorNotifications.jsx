import React, { useState, useEffect } from 'react';
import apiClient from '../../../utils/apiClient';
import { 
  BellIcon, 
  CheckCircleIcon, 
  ClockIcon, 
  TrashIcon, 
  ShoppingCartIcon,
  ArchiveBoxIcon,
  TagIcon,
  UserIcon
} from '@heroicons/react/24/outline';

const formatTimeAgo = (date) => {
  if (!date) return 'Just now';
  const d = new Date(date);
  const now = new Date();
  const seconds = Math.floor(Math.max(0, now - d) / 1000);
  
  if (seconds < 10) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString();
};

const TEAL = '#0f766e';

export default function VendorNotifications({ showToast }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/vendor/notifications');
      setNotifications(res);
    } catch (err) {
      showToast && showToast('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const markAsRead = async (id) => {
    try {
      await apiClient.put(`/vendor/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      showToast && showToast('Error marking as read');
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'new_order': return <ShoppingCartIcon style={{ width: 20, height: 20, color: '#3b82f6' }} />;
      case 'promotion_expired': return <TagIcon style={{ width: 20, height: 20, color: '#ef4444' }} />;
      case 'stock_low': return <ArchiveBoxIcon style={{ width: 20, height: 20, color: '#f59e0b' }} />;
      default: return <BellIcon style={{ width: 20, height: 20, color: '#64748b' }} />;
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div style={{ padding: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', margin: 0, letterSpacing: '-0.5px' }}>Notifications</h1>
          <p style={{ fontSize: 14, color: '#64748b', margin: '4px 0 0' }}>You have {unreadCount} unread alerts</p>
        </div>
        {unreadCount > 0 && (
          <button 
            onClick={() => notifications.filter(n => !n.is_read).forEach(n => markAsRead(n.id))}
            style={{ background: 'white', border: '1px solid #e2e8f0', padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600, color: TEAL, cursor: 'pointer' }}
          >
            Mark all as read
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ height: 80, background: '#f8fafc', borderRadius: 12, border: '1px solid #f1f5f9' }} className="vp-skeleton" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', background: 'white', borderRadius: 16, border: '1px solid #e2e8f0' }}>
          <div style={{ background: '#f1f5f9', width: 60, height: 60, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <BellIcon style={{ width: 30, height: 30, color: '#94a3b8' }} />
          </div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#0f172a' }}>All caught up!</h3>
          <p style={{ margin: '8px 0 0', color: '#64748b', fontSize: 14 }}>No new notifications at the moment.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {notifications.map((notif) => (
            <div 
              key={notif.id}
              onClick={() => !notif.is_read && markAsRead(notif.id)}
              style={{ 
                background: 'white', 
                border: `1px solid ${notif.is_read ? '#e2e8f0' : '#dbeafe'}`, 
                borderRadius: 16, 
                padding: '16px 20px', 
                display: 'flex', 
                gap: 16, 
                alignItems: 'center',
                cursor: notif.is_read ? 'default' : 'pointer',
                transition: 'all 0.2s',
                boxShadow: notif.is_read ? 'none' : '0 4px 12px rgba(59, 130, 246, 0.05)',
                position: 'relative'
              }}
              onMouseEnter={e => !notif.is_read && (e.currentTarget.style.borderColor = '#3b82f6')}
              onMouseLeave={e => !notif.is_read && (e.currentTarget.style.borderColor = '#dbeafe')}
            >
              {!notif.is_read && (
                <div style={{ position: 'absolute', top: 20, right: 20, width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }} />
              )}
              
              <div style={{ width: 44, height: 44, borderRadius: 12, background: notif.is_read ? '#f8fafc' : '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                {getIcon(notif.notification_type)}
              </div>
              
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#0f172a' }}>{notif.title}</h4>
                  <span style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <ClockIcon style={{ width: 12, height: 12 }} />
                    {formatTimeAgo(notif.created_at)}
                  </span>
                </div>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b', lineHeight: 1.5 }}>{notif.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
