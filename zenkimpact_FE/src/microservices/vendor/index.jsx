import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import apiClient from '../../utils/apiClient';
import './vendor-portal.css';
import VendorOverview from './components/VendorOverview';
import VendorProducts from './components/VendorProducts';
import VendorOrders from './components/VendorOrders';
import VendorRequests from './components/VendorRequests';
import VendorPromotions from './components/VendorPromotions';
import VendorReports from './components/VendorReports';
import VendorSettings from './components/VendorSettings';
import VendorNotifications from './components/VendorNotifications';
import {
  ChartBarSquareIcon,
  CubeIcon,
  ClipboardDocumentListIcon,
  InboxArrowDownIcon,
  MegaphoneIcon,
  DocumentChartBarIcon,
  Cog6ToothIcon,
  ArrowLeftOnRectangleIcon,
  PlusCircleIcon,
  BellIcon,
} from '@heroicons/react/24/outline';

const TABS = [
  { id: 'overview', label: 'Overview', Icon: ChartBarSquareIcon },
  { id: 'products', label: 'Products', Icon: CubeIcon },
  { id: 'orders', label: 'Orders', Icon: ClipboardDocumentListIcon },
  { id: 'requests', label: 'Requests', Icon: InboxArrowDownIcon },
  { id: 'promotions', label: 'Promotions', Icon: MegaphoneIcon },
  { id: 'reports', label: 'Reports', Icon: DocumentChartBarIcon },
  { id: 'settings', label: 'Settings', Icon: Cog6ToothIcon },
  { id: 'notifications', label: 'Notifications', Icon: BellIcon },
];

export default function VendorDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'overview';
  const setActiveTab = (tab) => setSearchParams({ tab });
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [toast, setToast] = useState(null);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch everything in one single roundtrip to prevent cold-start bottlenecks
      const bundle = await apiClient.get('/vendor/dashboard-bundle');
      
      setStats(bundle.stats);
      setProducts(bundle.products || []);
      setOrders(bundle.orders || []);
      setRequests(bundle.requests || []);
      setUnreadNotifications(bundle.stats?.unread_notifications || 0);

    } catch (err) {
      console.error('Failed to load vendor data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleBack = () => {
    window.location.href = '/dashboard';
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'overview':
        return <VendorOverview stats={stats} orders={orders} requests={requests} products={products} loading={loading} onNavigate={setActiveTab} showToast={showToast} />;
      case 'products':
        return <VendorProducts products={products} loading={loading} onRefresh={loadData} showToast={showToast} />;
      case 'orders':
        return <VendorOrders orders={orders} loading={loading} onRefresh={loadData} showToast={showToast} />;
      case 'requests':
        return <VendorRequests requests={requests} loading={loading} onRefresh={loadData} showToast={showToast} />;
      case 'promotions':
        return <VendorPromotions products={products} showToast={showToast} />;
      case 'reports':
        return <VendorReports orders={orders} showToast={showToast} />;
      case 'settings':
        return <VendorSettings showToast={showToast} />;
      case 'notifications':
        return <VendorNotifications showToast={showToast} />;
      default:
        return null;
    }
  };

  return (
    <div className="vendor-portal">
      <div className="vp-shell">
        {/* Sidebar */}
        <aside className="vp-sidebar">
          <div className="vp-sidebar-header">
            <img
              src="/assets/zenk-logo.png"
              alt="ZenK"
              style={{ height: 24, objectFit: 'contain', marginBottom: 28 }}
            />
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: '50%', background: '#f1f5f9', border: '2px solid #fff', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                 <img src="https://ui-avatars.com/api/?name=Aman+Kumar&background=f97316&color=fff" alt="Profile" style={{ width: '100%', height: '100%' }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 14, fontWeight: 800, color: '#0f172a', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Aman Kumar</p>
                <span style={{ fontSize: 10, fontWeight: 700, color: '#f97316', background: '#fff7ed', padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase' }}>Vendor Partner</span>
              </div>
            </div>
            
            <p style={{ fontSize: 12, fontWeight: 600, color: '#64748b', margin: '4px 0 0' }}>Sunrise Stationery & Books</p>
          </div>
          <nav className="vp-nav">
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                className={`vp-nav-item ${activeTab === id ? 'active' : ''}`}
                onClick={() => setActiveTab(id)}
              >
                <Icon />
                <span>{label}</span>
                {id === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                  <span className="vp-nav-badge">
                    {requests.filter(r => r.status === 'pending').length}
                  </span>
                )}
                {id === 'orders' && orders.filter(o => o.status === 'pending').length > 0 && (
                  <span className="vp-nav-badge">
                    {orders.filter(o => o.status === 'pending').length}
                  </span>
                )}
                {id === 'notifications' && unreadNotifications > 0 && (
                  <span className="vp-nav-badge" style={{ background: '#ef4444' }}>
                    {unreadNotifications}
                  </span>
                )}
              </button>
            ))}
          </nav>
          <div style={{ padding: '0 12px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button
              onClick={() => setActiveTab('products')}
              style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid #e2e8f0', background: 'white', color: '#1e293b', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', transition: 'all .2s', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#f97316'; e.currentTarget.style.background = '#fff7ed'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.background = 'white'; }}
            >
              <PlusCircleIcon style={{ width: 18, height: 18, color: '#f97316' }} />
              <span>Add New Product</span>
            </button>
          </div>
          <div style={{ padding: '16px 12px', borderTop: '1px solid #f1f5f9' }}>
            <button className="vp-nav-item" onClick={handleBack}>
              <ArrowLeftOnRectangleIcon />
              <span>Back to Dashboard</span>
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="vp-main">
          {renderTab()}
        </main>
      </div>

      {/* Toast Notification */}
      {toast && <div className="vp-toast">{toast}</div>}
    </div>
  );
}
