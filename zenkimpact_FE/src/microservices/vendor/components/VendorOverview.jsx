import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../../../utils/apiClient';
import {
  CubeIcon,
  CurrencyDollarIcon,
  ShoppingCartIcon,
  ClockIcon,
  StarIcon,
  ArrowTrendingUpIcon,
  ArrowUpTrayIcon,
  MegaphoneIcon,
  DocumentChartBarIcon,
  BellIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  EllipsisVerticalIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  FunnelIcon,
  ExclamationTriangleIcon,
  ArrowUturnLeftIcon,
  TruckIcon,
  CalendarIcon,
  ArrowTopRightOnSquareIcon,
  ArrowSmallRightIcon,
} from '@heroicons/react/24/outline';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, Filler);

const ORANGE = '#f97316';
const ORANGE_DARK = '#ea580c';
const ORANGE_LIGHT = '#fff7ed';

// Helper to format relative time
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

function StatusDot({ color, pulse = false }) {
  return (
    <span style={{ position: 'relative', display: 'inline-flex', width: 10, height: 10, flexShrink: 0 }}>
      {pulse && <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: color, opacity: 0.4, animation: 'ping 1.5s cubic-bezier(0,0,0.2,1) infinite' }} />}
      <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'block' }} />
    </span>
  );
}

function KPICard({ label, value, sub, subColor = '#059669', Icon, iconBg, iconColor, onClick }) {
  return (
    <div className="vp-kpi-card" onClick={onClick} style={{ position: 'relative', overflow: 'hidden', border: '1px solid #f1f5f9', cursor: onClick ? 'pointer' : 'default', transition: 'all 0.2s' }}>
      {/* Subtle Orange Dot Grid Pattern */}
      <div style={{ 
        position: 'absolute', 
        inset: 0, 
        opacity: 0.1, 
        backgroundImage: `radial-gradient(${ORANGE} 1.2px, transparent 1.2px)`, 
        backgroundSize: '18px 18px',
        pointerEvents: 'none'
      }} />

      {/* Uniform Orange Theme Glow */}
      <div style={{ 
        position: 'absolute', 
        top: '-20px', 
        right: '-20px', 
        width: '100px', 
        height: '100px', 
        background: ORANGE, 
        opacity: 0.08, 
        filter: 'blur(35px)',
        borderRadius: '50%',
        pointerEvents: 'none'
      }} />

      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div style={{ background: iconBg, padding: 10, borderRadius: 12, display: 'flex', boxShadow: `0 4px 10px ${iconColor}15` }}>
            <Icon style={{ width: 22, height: 22, color: iconColor }} />
          </div>
          {onClick && (
            <div style={{ background: '#f8fafc', padding: 6, borderRadius: 8, display: 'flex', transition: 'all 0.2s', border: '1px solid #f1f5f9' }} className="kpi-arrow">
              <ArrowSmallRightIcon style={{ width: 16, height: 16, color: '#94a3b8' }} />
            </div>
          )}
        </div>
        <div>
          <p className="label" style={{ margin: 0, fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</p>
          <p className="value" style={{ margin: '6px 0', fontSize: 26, fontWeight: 800, color: '#0f172a', letterSpacing: '-1px' }}>{value}</p>
          {sub && <p style={{ fontSize: 12, fontWeight: 700, color: subColor, margin: '8px 0 0', display: 'flex', alignItems: 'center', gap: 4 }}>{sub}</p>}
        </div>
      </div>
      <style>{`
        .vp-kpi-card:hover .kpi-arrow {
          background: ${ORANGE}15 !important;
          border-color: ${ORANGE}33 !important;
          transform: translateX(3px);
        }
        .vp-kpi-card:hover .kpi-arrow svg {
          color: ${ORANGE} !important;
        }
      `}</style>
    </div>
  );
}

export default function VendorOverview({ stats, orders, requests, products, loading, onNavigate, showToast }) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All Statuses');
  const [doneTasks, setDoneTasks] = useState({});
  const [activeModal, setActiveModal] = useState(null);
  const [chartType, setChartType] = useState('line');
  
  const [settingsForm, setSettingsForm] = useState({ email_notifications: true, sms_alerts: false, auto_accept_orders: false, low_stock_threshold: 5 });
  const searchRef = useRef(null);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  // Handle click outside for search dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSearchDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Calculate dynamic pending tasks
  const dynamicTasks = [];
  if (stats?.pending_orders > 0) {
    dynamicTasks.push({ 
      id: 'task-orders', 
      urgent: true, 
      title: `${stats.pending_orders} pending orders`, 
      sub: 'Action required to fulfill customer purchases' 
    });
  }
  
  const lowStockCount = (products || []).filter(p => p.stock_quantity <= (settingsForm.low_stock_threshold || 5)).length;
  if (lowStockCount > 0) {
    dynamicTasks.push({ 
      id: 'task-stock', 
      urgent: true, 
      title: `${lowStockCount} items low on stock`, 
      sub: 'Consider restocking soon to avoid lost sales' 
    });
  }

  if (stats?.pending_requests > 0) {
    dynamicTasks.push({ 
      id: 'task-requests', 
      urgent: false, 
      title: `${stats.pending_requests} product requests`, 
      sub: 'New requests from students/members' 
    });
  }

  // Fallback/Default tasks if list is short
  if (dynamicTasks.length < 3) {
    dynamicTasks.push({ id: 'task-promo', urgent: false, title: 'No active promotions?', sub: 'Boost sales by creating a new discount campaign' });
    dynamicTasks.push({ id: 'task-profile', urgent: false, title: 'Review store profile', sub: 'Ensure your banner and description are up to date' });
  }

  // Calculate dynamic live activity from orders AND requests
  const dynamicActivity = [
    ...(orders || []).map(o => ({
      id: `act-order-${o.id}`,
      type: 'order',
      date: new Date(o.updated_at || o.created_at),
      color: o.status === 'delivered' ? '#10b981' : o.status === 'cancelled' ? '#ef4444' : ORANGE,
      icon: o.status === 'cancelled' ? ArrowUturnLeftIcon : ShoppingCartIcon,
      msg: o.status === 'pending' ? `New order for ${o.product_name || 'Product'}` : `Order #${o.id.slice(0,4)} moved to ${o.status}`,
      time: formatTimeAgo(o.updated_at || o.created_at)
    })),
    ...(requests || []).map(r => ({
      id: `act-req-${r.id}`,
      type: 'request',
      date: new Date(r.updated_at || r.created_at),
      color: r.status === 'accepted' ? '#10b981' : r.status === 'rejected' ? '#ef4444' : '#6366f1',
      icon: r.status === 'pending' ? MegaphoneIcon : r.status === 'accepted' ? CheckCircleIcon : ExclamationCircleIcon,
      msg: r.status === 'pending' ? `New request from ${r.requester_name || 'User'}` : `Request "${r.title.slice(0,20)}..." ${r.status}`,
      time: formatTimeAgo(r.updated_at || r.created_at)
    })),
    ...(products || []).filter(p => new Date(p.updated_at) > new Date(p.created_at)).map(p => ({
      id: `act-prod-${p.id}`,
      type: 'product',
      date: new Date(p.updated_at),
      color: p.is_active ? '#10b981' : '#94a3b8',
      icon: CubeIcon,
      msg: `Product "${p.name.slice(0,20)}..." set to ${p.is_active ? 'Active' : 'Inactive'}`,
      time: formatTimeAgo(p.updated_at)
    }))
  ]
  .sort((a, b) => b.date - a.date);

  // Search Suggestions (detailed overlay)
  const searchSuggestions = search.length > 1 ? [
    ...(orders || []).filter(o => 
      o.id.toLowerCase().includes(search.toLowerCase()) || 
      (o.product_name || '').toLowerCase().includes(search.toLowerCase()) ||
      o.buyer_name.toLowerCase().includes(search.toLowerCase())
    ).map(o => ({ type: 'Order', id: o.id, title: o.product_name || 'Order', sub: `By ${o.buyer_name}`, icon: ShoppingCartIcon, tab: 'orders' })),
    ...(products || []).filter(p => 
      p.name.toLowerCase().includes(search.toLowerCase()) || 
      (p.sku || '').toLowerCase().includes(search.toLowerCase())
    ).map(p => ({ type: 'Product', id: p.id, title: p.name, sub: `SKU: ${p.sku || 'N/A'}`, icon: CubeIcon, tab: 'products' })),
    ...(requests || []).filter(r => 
      r.title.toLowerCase().includes(search.toLowerCase()) || 
      (r.requester_name || '').toLowerCase().includes(search.toLowerCase())
    ).map(r => ({ type: 'Request', id: r.id, title: r.title, sub: `From ${r.requester_name || 'User'}`, icon: MegaphoneIcon, tab: 'requests' }))
  ].slice(0, 8) : [];

  // Keep dashboard lists stable (don't filter the main UI)
  const filteredTasks = dynamicTasks;
  const filteredActivity = dynamicActivity.slice(0, 6);

  const [promoForm, setPromoForm] = useState({ title: '', discount_percentage: 10, start_date: '', end_date: '', scope: 'all', target_product_ids: [] });
  const [bulkFile, setBulkFile] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        if (activeModal === 'settings') setModalLoading(true);
        const res = await apiClient.get('/vendor/settings');
        setSettingsForm(res);
      } catch (err) {
        if (activeModal === 'settings') showToast && showToast('Failed to load settings');
      } finally {
        setModalLoading(false);
      }
    };
    loadSettings();
  }, [activeModal]);

  const handleSaveSettings = async () => {
    try {
      setModalLoading(true);
      await apiClient.put('/vendor/settings', settingsForm);
      showToast && showToast('Settings saved successfully!');
      setActiveModal(null);
    } catch (e) {
      showToast && showToast('Error saving settings.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleCreatePromo = async () => {
    try {
      setModalLoading(true);
      await apiClient.post('/vendor/promotions', promoForm);
      showToast && showToast('Promotion created successfully!');
      setActiveModal(null);
    } catch (e) {
      showToast && showToast('Error creating promotion.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleUploadBulk = async () => {
    if (!bulkFile) return showToast && showToast('Please select a CSV file.');
    try {
      setModalLoading(true);
      const formData = new FormData();
      formData.append('file', bulkFile);
      const res = await apiClient.post('/vendor/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      showToast && showToast(res.message || 'Inventory uploaded');
      setActiveModal(null);
      setBulkFile(null);
    } catch (e) {
      showToast && showToast(e.message || 'Error uploading inventory.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      setModalLoading(true);
      const res = await apiClient.get('/vendor/report', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'vendor_report.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      showToast && showToast('Report downloaded successfully!');
      setActiveModal(null);
    } catch (e) {
      showToast && showToast('Error generating report.');
    } finally {
      setModalLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 8 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 20 }}>
          {[1,2,3].map(i => <div key={i} className="vp-skeleton" style={{ height: 130, borderRadius: 14 }} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 20 }}>
          {[1,2,3].map(i => <div key={i} className="vp-skeleton" style={{ height: 130, borderRadius: 14 }} />)}
        </div>
        <div className="vp-skeleton" style={{ height: 300, borderRadius: 14 }} />
      </div>
    );
  }

  const totalRevenue = stats?.total_revenue ?? 0;
  const totalOrders = stats?.total_orders ?? 0;
  const avgOrderValue = totalOrders > 0 ? (totalRevenue / totalOrders) : 0;
  const recentOrders = (orders || []).slice(0, 5);

  // Chart data
  const revTrend = stats?.revenue_trend || [];
  const chartLabels = revTrend.length > 0
    ? revTrend.map(d => d.date)
    : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const chartData = revTrend.length > 0
    ? revTrend.map(d => d.amount)
    : [0, 0, 0, 0, 0, 0, 0];

  const salesChartData = {
    labels: chartLabels,
    datasets: [
      {
        label: 'Actual Sales',
        data: chartData,
        borderColor: ORANGE,
        backgroundColor: chartType === 'bar' 
          ? chartLabels.map((_, i) => i === chartLabels.length - 1 ? ORANGE : `${ORANGE}88`)
          : (context) => {
              const ctx = context.chart.ctx;
              const gradient = ctx.createLinearGradient(0, 0, 0, 300);
              gradient.addColorStop(0, `${ORANGE}44`);
              gradient.addColorStop(1, `${ORANGE}00`);
              return gradient;
            },
        fill: chartType === 'line',
        tension: 0.4,
        pointRadius: chartType === 'line' ? 4 : 0,
        pointBackgroundColor: 'white',
        pointBorderColor: ORANGE,
        pointBorderWidth: 2,
        pointHoverRadius: 6,
        borderWidth: chartType === 'line' ? 3 : 0,
        borderRadius: chartType === 'bar' ? 8 : 0,
      },
      {
        label: 'Target',
        data: chartLabels.map(() => (settingsForm.monthly_revenue_target || 50000) / (chartLabels.length || 30)),
        borderColor: '#94a3b8',
        backgroundColor: chartType === 'bar' ? '#e2e8f0' : 'transparent',
        borderDash: chartType === 'line' ? [5, 5] : [],
        fill: false,
        tension: 0, // Keep target line straight
        pointRadius: 0,
        borderWidth: 2,
        borderRadius: chartType === 'bar' ? 8 : 0,
      }
    ],
  };

  const salesChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e293b',
        padding: 12,
        titleFont: { size: 14, weight: 'bold' },
        bodyFont: { size: 13 },
        cornerRadius: 10,
        callbacks: {
          label: ctx => `${ctx.dataset.label}: ₹${ctx.raw.toLocaleString('en-IN')}`
        }
      }
    },
    scales: {
      y: {
        border: { display: false },
        grid: { color: '#f1f5f9' },
        ticks: {
          callback: val => `₹${val >= 1000 ? (val/1000) + 'k' : val}`,
          font: { size: 11, weight: '600' },
          color: '#64748b'
        }
      },
      x: {
        border: { display: false },
        grid: { display: false },
        ticks: {
          font: { size: 11, weight: '600' },
          color: '#64748b'
        }
      },
    },
  };

  const filteredOrders = recentOrders.filter(o => {
    const matchSearch = !search || (o.product_name || '').toLowerCase().includes(search.toLowerCase()) || (o.buyer_name || '').toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'All Statuses' || o.status === statusFilter.toLowerCase();
    return matchSearch && matchStatus;
  });

  const statusBadgeStyle = (status) => {
    const map = {
      pending:    { bg: '#fef3c7', color: '#92400e', dot: '#f59e0b' },
      processing: { bg: '#e0e7ff', color: '#3730a3', dot: '#6366f1' },
      shipped:    { bg: '#dbeafe', color: '#1e40af', dot: '#3b82f6' },
      delivered:  { bg: '#d1fae5', color: '#065f46', dot: '#10b981' },
      cancelled:  { bg: '#fee2e2', color: '#991b1b', dot: '#ef4444' },
    };
    return map[status] || { bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' };
  };

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Topbar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, gap: 16, flexWrap: 'wrap', position: 'relative' }}>
        <div 
          ref={searchRef}
          style={{ flex: 1, maxWidth: 360, position: 'relative' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', background: 'white', border: `1px solid ${showSearchDropdown ? ORANGE : '#e2e8f0'}`, borderRadius: 10, padding: '8px 14px', gap: 8, boxShadow: showSearchDropdown ? `0 0 0 2px ${ORANGE}22` : '0 1px 3px rgba(0,0,0,.04)', transition: 'all 0.2s' }}>
            <MagnifyingGlassIcon style={{ width: 17, height: 17, color: showSearchDropdown ? ORANGE : '#94a3b8', flexShrink: 0 }} />
            <input 
              value={search} 
              onFocus={() => setShowSearchDropdown(true)}
              onChange={e => {
                setSearch(e.target.value);
                setShowSearchDropdown(true);
              }} 
              placeholder="Search orders, products, or requests..." 
              style={{ border: 'none', outline: 'none', width: '100%', fontSize: 13, color: '#0f172a', background: 'transparent' }} 
            />
          </div>

          {/* Search Dropdown */}
          {showSearchDropdown && search.length > 1 && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 8, background: 'white', borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)', zIndex: 100, overflow: 'hidden' }}>
              <div style={{ padding: '8px 12px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9' }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Quick Results</span>
              </div>
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                {searchSuggestions.length > 0 ? (
                  searchSuggestions.map((item, idx) => (
                    <button
                      key={`${item.type}-${item.id}`}
                      onClick={() => {
                        onNavigate(item.tab);
                        setShowSearchDropdown(false);
                        setSearch('');
                      }}
                      style={{ width: '100%', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12, border: 'none', background: 'white', cursor: 'pointer', textAlign: 'left', borderBottom: idx === searchSuggestions.length - 1 ? 'none' : '1px solid #f1f5f9', transition: 'background 0.2s' }}
                      onMouseEnter={e => e.currentTarget.style.background = '#fef3c7'}
                      onMouseLeave={e => e.currentTarget.style.background = 'white'}
                    >
                      <div style={{ width: 32, height: 32, borderRadius: 8, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <item.icon style={{ width: 16, height: 16, color: ORANGE }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</p>
                          <span style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', background: '#f1f5f9', padding: '1px 5px', borderRadius: 4 }}>{item.type}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: 11, color: '#64748b' }}>{item.sub}</p>
                      </div>
                    </button>
                  ))
                ) : (
                  <div style={{ padding: '20px 14px', textAlign: 'center' }}>
                    <p style={{ margin: 0, fontSize: 13, color: '#64748b' }}>No direct matches for "{search}"</p>
                    <p style={{ margin: '2px 0 0', fontSize: 11, color: '#94a3b8' }}>Try searching by name or SKU</p>
                  </div>
                )}
              </div>
              <div style={{ padding: '8px 14px', background: '#f8fafc', borderTop: '1px solid #f1f5f9', textAlign: 'center' }}>
                <p style={{ margin: 0, fontSize: 11, color: '#64748b' }}>Press Enter to see all results</p>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={() => showToast && showToast('Date range set to Last 30 Days')} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: '8px 16px', fontSize: 13, fontWeight: 600, color: '#334155', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <CalendarIcon style={{ width: 16, height: 16 }} /> Last 30 Days
          </button>
          <button onClick={() => onNavigate && onNavigate('reports')} style={{ background: ORANGE, border: 'none', borderRadius: 10, padding: '8px 16px', fontSize: 13, fontWeight: 700, color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <ArrowTopRightOnSquareIcon style={{ width: 16, height: 16 }} /> Export Report
          </button>
          <button onClick={() => onNavigate && onNavigate('notifications')} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 8, cursor: 'pointer', display: 'flex', position: 'relative' }}>
            <BellIcon style={{ width: 18, height: 18, color: '#64748b' }} />
            {stats?.unread_notifications > 0 && (
              <span style={{ position: 'absolute', top: -4, right: -4, width: 14, height: 14, borderRadius: '50%', background: '#ef4444', color: 'white', fontSize: 9, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid white' }}>
                {stats.unread_notifications}
              </span>
            )}
          </button>
          <button onClick={() => onNavigate && onNavigate('settings')} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 8, cursor: 'pointer', display: 'flex' }}>
            <Cog6ToothIcon style={{ width: 18, height: 18, color: '#64748b' }} />
          </button>
        </div>
      </div>

      {/* Premium 3D Banner */}
      <div className="vp-banner" style={{ 
        position: 'relative', 
        overflow: 'hidden', 
        borderRadius: 24, 
        backgroundColor: '#f97316',
        backgroundImage: `
          linear-gradient(to right, rgba(15, 23, 42, 0.4) 0%, transparent 60%),
          linear-gradient(30deg, #ea580c 6%, transparent 6.5%, transparent 93%, #ea580c 93.5%, #ea580c),
          linear-gradient(150deg, #ea580c 6%, transparent 6.5%, transparent 93%, #ea580c 93.5%, #ea580c),
          linear-gradient(30deg, #ea580c 6%, transparent 6.5%, transparent 93%, #ea580c 93.5%, #ea580c),
          linear-gradient(150deg, #ea580c 6%, transparent 6.5%, transparent 93%, #ea580c 93.5%, #ea580c),
          linear-gradient(60deg, #d24e01 20%, transparent 20.5%, transparent 79%, #d24e01 79%, #d24e01),
          linear-gradient(60deg, #d24e01 20%, transparent 20.5%, transparent 79%, #d24e01 79%, #d24e01)
        `,
        backgroundSize: '100% 100%, 80px 140px, 80px 140px, 80px 140px, 80px 140px, 80px 140px, 80px 140px',
        backgroundPosition: '0 0, 0 0, 0 0, 40px 70px, 40px 70px, 0 0, 40px 70px',
        padding: '28px 48px', 
        marginBottom: 32, 
        boxShadow: '0 20px 40px -12px rgba(15, 23, 42, 0.2)' 
      }}>
        {/* Floating 3D Decoration */}
        <div style={{ position: 'absolute', right: -40, top: -40, width: 380, height: 380, opacity: 0.5, pointerEvents: 'none', animation: 'float 6s ease-in-out infinite' }}>
          <img src="/premium_3d_vendor_banner_1776972823675.png" alt="3D Decor" style={{ width: '100%', height: '100%', objectFit: 'contain', filter: 'drop-shadow(0 25px 35px rgba(0,0,0,0.4))' }} />
        </div>
        
        <div style={{ 
          position: 'relative', 
          zIndex: 2, 
          maxWidth: '65%',
          background: 'rgba(15, 23, 42, 0.15)',
          backdropFilter: 'blur(10px)',
          padding: '24px 32px',
          borderRadius: '20px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)'
        }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: ORANGE, padding: '4px 12px', borderRadius: 99, marginBottom: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
            <StarIcon style={{ width: 12, height: 12, color: 'white', fill: 'white' }} />
            <span style={{ color: 'white', fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>Top 5% Global Seller</span>
          </div>
          
          <h2 style={{ margin: 0, fontSize: 32, fontWeight: 900, color: 'white', letterSpacing: '-1.5px', lineHeight: 1, textShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
            Sunrise Stationery & Books
          </h2>
          <p style={{ margin: '12px 0 0', fontSize: 15, color: 'rgba(255,255,255,0.9)', fontWeight: 500, lineHeight: 1.5, maxWidth: 460 }}>
            Welcome back, <span style={{ fontWeight: 800, color: 'white' }}>Aman Kumar</span>. Performance is <span style={{ fontWeight: 800, background: 'white', color: '#0f172a', padding: '1px 6px', borderRadius: 4 }}>12% better</span> this month.
          </p>
        </div>

        {/* Floating Action Button (Solid White) */}
        <div style={{ position: 'absolute', top: '50%', transform: 'translateY(-50%)', right: 48, zIndex: 10 }}>
           <button 
             onClick={() => onNavigate('reports')} 
             style={{ background: 'white', color: ORANGE, border: 'none', padding: '14px 28px', borderRadius: 16, fontWeight: 800, fontSize: 14, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.15)', transition: 'all 0.3s' }}
             onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 12px 32px rgba(0,0,0,0.2)'; }}
             onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)'; }}
           >
             View Deep Insights 
             <div style={{ background: ORANGE_LIGHT, padding: 6, borderRadius: 8, display: 'flex' }}>
               <ArrowTrendingUpIcon style={{ width: 18, height: 18 }} />
             </div>
           </button>
        </div>

        {/* CSS for float animation */}
        <style>{`
          @keyframes float {
            0% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(2deg); }
            100% { transform: translateY(0px) rotate(0deg); }
          }
        `}</style>
      </div>

      {/* Quick Action Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 24 }}>
        {[
          { Icon: ArrowUpTrayIcon, color: '#3b82f6', bg: '#eff6ff', title: 'Upload Bulk Inventory', sub: 'Update multiple SKUs via CSV', type: 'modal', action: 'bulk' },
          { Icon: MegaphoneIcon,   color: '#f97316', bg: '#fff7ed', title: 'Create Promotion',      sub: 'Setup a new discount campaign', type: 'nav', action: 'promotions' },
          { Icon: DocumentChartBarIcon, color: ORANGE, bg: ORANGE_LIGHT, title: 'Generate Weekly Report', sub: 'Compile sales and traffic data', type: 'nav', action: 'reports' },
        ].map(({ Icon, color, bg, title, sub, action, type }) => (
          <button key={title} onClick={() => type === 'nav' ? onNavigate(action) : setActiveModal(action)} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 14, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', textAlign: 'left', transition: 'all .15s', boxShadow: '0 1px 3px rgba(0,0,0,.04)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = color; e.currentTarget.style.boxShadow = `0 4px 12px ${color}22`; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,.04)'; }}
          >
            <div style={{ background: bg, padding: 10, borderRadius: 10, flexShrink: 0 }}>
              <Icon style={{ width: 20, height: 20, color }} />
            </div>
            <div>
              <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{title}</p>
              <p style={{ margin: '2px 0 0', fontSize: 12, color: '#64748b' }}>{sub}</p>
            </div>
          </button>
        ))}
      </div>

      {/* KPI Row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 14 }}>
        <KPICard label="Total Revenue"  value={`₹${totalRevenue.toLocaleString('en-IN')}`} sub="↑ +12.5% vs last month" iconBg={ORANGE_LIGHT} iconColor={ORANGE} Icon={CurrencyDollarIcon} onClick={() => onNavigate('reports')} />
        <KPICard label="Total Orders"   value={totalOrders.toLocaleString()} sub="↑ +8.2% vs last month" iconBg="#dbeafe" iconColor="#2563eb" Icon={ShoppingCartIcon} onClick={() => onNavigate('orders')} />
        <KPICard label="Avg Order Value" value={`₹${Math.round(avgOrderValue).toLocaleString('en-IN')}`} sub="↓ -2.1% vs last month" subColor="#ef4444" iconBg="#e0e7ff" iconColor="#7c3aed" Icon={ArrowTrendingUpIcon} onClick={() => onNavigate('reports')} />
      </div>

      {/* KPI Row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 24 }}>
        <KPICard label="Active Products"   value={stats?.active_products ?? 0} sub={`${stats?.total_products ?? 0} total listed`} subColor="#64748b" iconBg="#f0fdf4" iconColor="#16a34a" Icon={CubeIcon} onClick={() => onNavigate('products')} />
        <KPICard label="Pending Orders"    value={stats?.pending_orders ?? 0} sub="Action required" subColor="#f59e0b" iconBg="#fef3c7" iconColor="#b45309" Icon={ClockIcon} onClick={() => onNavigate('orders')} />
        <KPICard label="ZenK Rating"       value="4.8/5" sub="↑ +0.1 vs last month" iconBg="#fef9c3" iconColor="#ca8a04" Icon={StarIcon} onClick={() => onNavigate('reports')} />
      </div>

      {/* Chart + Pending Tasks */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 20, marginBottom: 20 }}>
        {/* Sales Performance Chart - Elaborative */}
        <div style={{ background: 'white', borderRadius: 20, border: '1px solid #e2e8f0', padding: 24, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Sales Performance</h3>
              <p style={{ margin: '2px 0 0', fontSize: 13, color: '#64748b' }}>Revenue vs Target Comparison</p>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              {/* Chart Toggle */}
              <div style={{ background: '#f1f5f9', padding: 4, borderRadius: 10, display: 'flex', gap: 4 }}>
                <button 
                  onClick={() => setChartType('line')}
                  style={{ padding: '6px 14px', borderRadius: 7, border: 'none', background: chartType === 'line' ? 'white' : 'transparent', color: chartType === 'line' ? ORANGE : '#64748b', fontSize: 12, fontWeight: 800, cursor: 'pointer', boxShadow: chartType === 'line' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none', transition: 'all 0.2s' }}
                >
                  Line
                </button>
                <button 
                  onClick={() => setChartType('bar')}
                  style={{ padding: '6px 14px', borderRadius: 7, border: 'none', background: chartType === 'bar' ? 'white' : 'transparent', color: chartType === 'bar' ? ORANGE : '#64748b', fontSize: 12, fontWeight: 800, cursor: 'pointer', boxShadow: chartType === 'bar' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none', transition: 'all 0.2s' }}
                >
                  Bar
                </button>
              </div>

              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#64748b' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: ORANGE }} /> Actual
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#cbd5e1' }} /> Target
                </span>
              </div>
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: 32 }}>
            <div style={{ height: 320, position: 'relative' }}>
              {chartType === 'line' ? (
                <Line data={salesChartData} options={salesChartOptions} />
              ) : (
                <Bar data={salesChartData} options={salesChartOptions} />
              )}
            </div>

            {/* In-Chart Insights */}
            <div style={{ borderLeft: '1px solid #f1f5f9', paddingLeft: 32, display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <p style={{ margin: 0, fontSize: 11, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '.5px' }}>Peak Revenue</p>
                <p style={{ margin: '4px 0 0', fontSize: 20, fontWeight: 800, color: '#0f172a' }}>₹{Math.max(...chartData).toLocaleString('en-IN')}</p>
                <p style={{ margin: '2px 0 0', fontSize: 12, color: '#059669', fontWeight: 600 }}>↑ 12.5% vs avg</p>
              </div>

              <div>
                <p style={{ margin: 0, fontSize: 11, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '.5px' }}>Avg. Order Value</p>
                <p style={{ margin: '4px 0 0', fontSize: 20, fontWeight: 800, color: '#0f172a' }}>₹1,240</p>
                <p style={{ margin: '2px 0 0', fontSize: 12, color: '#64748b' }}>Stable trend</p>
              </div>

              <div style={{ marginTop: 'auto', padding: 16, background: ORANGE_LIGHT, borderRadius: 14, border: '1px solid #fed7aa' }}>
                <p style={{ margin: 0, fontSize: 12, fontWeight: 800, color: ORANGE_DARK }}>Performance Tip</p>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#7c2d12', lineHeight: 1.4 }}>Your {chartLabels[chartData.indexOf(Math.max(...chartData))] || 'peak'} sales are strong. Try a flash sale on weekends.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Pending Tasks */}
        <div style={{ background: 'white', borderRadius: 14, border: '1px solid #e2e8f0', padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,.04)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>Pending Tasks</h3>
            <span style={{ background: '#fef3c7', color: '#92400e', fontSize: 10, fontWeight: 800, padding: '3px 10px', borderRadius: 99, textTransform: 'uppercase', letterSpacing: '.5px' }}>
              {filteredTasks.filter(t => !doneTasks[t.id]).length} TO-DO
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {filteredTasks.map(task => (
              <div key={task.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', opacity: doneTasks[task.id] ? 0.4 : 1, transition: 'opacity .2s' }}>
                <button onClick={() => setDoneTasks(d => ({ ...d, [task.id]: !d[task.id] }))} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, flexShrink: 0, marginTop: 1 }}>
                  {doneTasks[task.id]
                    ? <CheckCircleIcon style={{ width: 22, height: 22, color: ORANGE }} />
                    : <div style={{ width: 20, height: 20, border: `2px solid ${task.urgent ? '#ef4444' : '#cbd5e1'}`, borderRadius: 6, background: 'white' }} />
                  }
                </button>
                <div>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: task.urgent ? '#ef4444' : '#0f172a', textDecoration: doneTasks[task.id] ? 'line-through' : 'none' }}>{task.title}</p>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: task.urgent ? '#f87171' : '#64748b' }}>{task.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Live Activity + Recent Orders */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 }}>
        {/* Live Activity */}
        <div style={{ background: 'white', borderRadius: 14, border: '1px solid #e2e8f0', padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,.04)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>Live Activity</h3>
            <StatusDot color="#10b981" pulse />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {filteredActivity.map(item => (
              <div key={item.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: `${item.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <item.icon style={{ width: 18, height: 18, color: item.color }} />
                </div>
                <div>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{item.msg}</p>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: '#94a3b8' }}>{item.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Orders */}
        <div style={{ background: 'white', borderRadius: 14, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,.04)' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>Recent Orders</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '5px 10px', fontSize: 12 }}>
                <FunnelIcon style={{ width: 13, height: 13, color: '#64748b' }} />
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: 12, fontWeight: 600, color: '#334155', cursor: 'pointer' }}>
                  {['All Statuses', 'Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'].map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <button onClick={() => onNavigate && onNavigate('orders')} style={{ background: ORANGE_LIGHT, border: 'none', borderRadius: 8, padding: '5px 12px', fontSize: 12, fontWeight: 700, color: ORANGE_DARK, cursor: 'pointer' }}>
                View All
              </button>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8fafc' }}>
                {['ORDER ID', 'CUSTOMER', 'PRODUCT', 'AMOUNT', 'STATUS', 'ACTION'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', fontSize: 11, fontWeight: 700, color: '#94a3b8', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px', borderBottom: '1px solid #e2e8f0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>No orders found.</td></tr>
              ) : filteredOrders.map(order => {
                const badge = statusBadgeStyle(order.status);
                return (
                  <tr key={order.id} style={{ transition: 'background .15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#f8fafb'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color: ORANGE }}>
                        #{order.id.slice(0, 8).toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 30, height: 30, borderRadius: '50%', background: ORANGE_LIGHT, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800, color: ORANGE, flexShrink: 0 }}>
                          {(order.buyer_name || 'U')[0].toUpperCase()}
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{order.buyer_name || '—'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9', fontSize: 13, color: '#334155', maxWidth: 160 }}>
                      <span style={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{order.product_name || '—'}</span>
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9', fontSize: 14, fontWeight: 800, color: '#0f172a' }}>
                      ₹{(order.total_amount || 0).toLocaleString('en-IN')}
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9' }}>
                      <span style={{ background: badge.bg, color: badge.color, fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 99, display: 'inline-flex', alignItems: 'center', gap: 5, textTransform: 'uppercase', letterSpacing: '.3px' }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: badge.dot, display: 'inline-block' }} />
                        {order.status}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f1f5f9' }}>
                      <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, borderRadius: 6, color: '#94a3b8' }}
                        onMouseEnter={e => e.currentTarget.style.background = '#f1f5f9'}
                        onMouseLeave={e => e.currentTarget.style.background = 'none'}
                      >
                        <EllipsisVerticalIcon style={{ width: 18, height: 18 }} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
      `}</style>

      {/* Dynamic Modals Overlay */}
      {activeModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)' }}>
          <div style={{ background: 'white', padding: '32px', borderRadius: '24px', width: '95%', maxWidth: '500px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', animation: 'fadeInUp 0.2s ease-out forwards', boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#0f172a', letterSpacing: '-0.5px' }}>
                {activeModal === 'settings' && 'Dashboard Settings'}
                {activeModal === 'bulk' && 'Upload Bulk Inventory'}
                {activeModal === 'promo' && 'Create Promotion'}
                {activeModal === 'report' && 'Generate Report'}
              </h2>
            </div>
            <p style={{ margin: '0 0 24px', fontSize: 14, color: '#64748b', lineHeight: 1.6 }}>
                {activeModal === 'settings' && 'Manage your vendor portal preferences, API keys, and notification alerts.'}
                {activeModal === 'bulk' && 'Upload a CSV file containing your product SKUs, inventory counts, and prices.'}
                {activeModal === 'promo' && 'Set up a new discount campaign or coupon code for your catalog items.'}
                {activeModal === 'report' && 'Select date range and parameters to compile sales and traffic data.'}
            </p>
            
            {activeModal === 'bulk' && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ border: '2px dashed #cbd5e1', borderRadius: 12, background: '#f8fafc', padding: '24px', textAlign: 'center', cursor: 'pointer' }} onClick={() => document.getElementById('bulk-file-input').click()}>
                  <ArrowUpTrayIcon style={{ width: 32, height: 32, color: '#94a3b8', margin: '0 auto 12px' }} />
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#475569' }}>{bulkFile ? bulkFile.name : 'Click to select or drag CSV file'}</p>
                  <input id="bulk-file-input" type="file" accept=".csv" onChange={e => setBulkFile(e.target.files[0])} style={{ display: 'none' }} />
                </div>
                <p style={{ margin: '12px 0 0', fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>Required columns: name, category, price, mrp, stock_quantity, sku</p>
              </div>
            )}

            {activeModal === 'settings' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Monthly Revenue Target (₹)</label>
                  <input 
                    type="number" 
                    value={settingsForm.monthly_revenue_target || ''} 
                    onChange={e => setSettingsForm({ ...settingsForm, monthly_revenue_target: parseInt(e.target.value) })}
                    style={{ width: '100%', padding: '12px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', transition: 'border-color 0.2s' }}
                    onFocus={e => e.target.style.borderColor = ORANGE}
                    onBlur={e => e.target.style.borderColor = '#e2e8f0'}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: '#f8fafc', borderRadius: 10 }}>
                   <div>
                     <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: '#0f172a' }}>Email Notifications</p>
                     <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>Receive alerts for new orders</p>
                   </div>
                   <input type="checkbox" checked={settingsForm.email_notifications} onChange={e => setSettingsForm({ ...settingsForm, email_notifications: e.target.checked })} style={{ accentColor: ORANGE, width: 18, height: 18 }} />
                </div>
              </div>
            )}

            {activeModal === 'promo' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Promotion Title</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Summer Sale 2026"
                    value={promoForm.title} 
                    onChange={e => setPromoForm({ ...promoForm, title: e.target.value })}
                    style={{ width: '100%', padding: '12px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Discount (%)</label>
                    <input 
                      type="number" 
                      value={promoForm.discount_percentage} 
                      onChange={e => setPromoForm({ ...promoForm, discount_percentage: parseInt(e.target.value) })}
                      style={{ width: '100%', padding: '12px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Scope</label>
                    <select 
                      value={promoForm.scope} 
                      onChange={e => setPromoForm({ ...promoForm, scope: e.target.value })}
                      style={{ width: '100%', padding: '12px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', background: 'white' }}
                    >
                      <option value="all">Entire Catalog</option>
                      <option value="specific">Specific Products</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeModal === 'report' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 24 }}>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                   <p style={{ margin: '0 0 12px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Financial Summary (MTD)</p>
                   <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                      <div>
                        <p style={{ margin: 0, fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Gross</p>
                        <p style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#0f172a' }}>₹{totalRevenue.toLocaleString('en-IN')}</p>
                      </div>
                      <div>
                        <p style={{ margin: 0, fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Fees (2%)</p>
                        <p style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#ef4444' }}>-₹{Math.round(totalRevenue * 0.02).toLocaleString('en-IN')}</p>
                      </div>
                      <div>
                        <p style={{ margin: 0, fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Net Payout</p>
                        <p style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#10b981' }}>₹{Math.round(totalRevenue * 0.98).toLocaleString('en-IN')}</p>
                      </div>
                   </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 10, textTransform: 'uppercase' }}>Recent Payment History</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '200px', overflowY: 'auto', paddingRight: '4px' }}>
                    {orders?.filter(o => o.status === 'completed' || o.status === 'shipped').slice(0, 5).map(o => (
                      <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: 'white', border: '1px solid #f1f5f9', borderRadius: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ width: 32, height: 32, borderRadius: '10px', background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <CurrencyDollarIcon style={{ width: 18, height: 18, color: '#16a34a' }} />
                          </div>
                          <div>
                             <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: '#0f172a' }}>{o.payment_method || 'UPI'} Payment</p>
                             <p style={{ margin: 0, fontSize: 11, color: '#94a3b8' }}>Order #{o.id.slice(0,6).toUpperCase()}</p>
                          </div>
                        </div>
                        <p style={{ margin: 0, fontSize: 14, fontWeight: 800, color: '#0f172a' }}>+₹{o.total_amount.toLocaleString('en-IN')}</p>
                      </div>
                    ))}
                    {(!orders || orders.filter(o => o.status === 'completed' || o.status === 'shipped').length === 0) && (
                      <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: 12, margin: '20px 0' }}>No payment transactions found.</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
              <button onClick={() => setActiveModal(null)} disabled={modalLoading} style={{ padding: '12px 22px', borderRadius: '12px', border: '1px solid #e2e8f0', background: 'white', color: '#475569', fontSize: 14, fontWeight: 700, cursor: 'pointer', opacity: modalLoading ? 0.5 : 1, transition: 'all 0.2s' }} onMouseEnter={e => !modalLoading && (e.currentTarget.style.background = '#f8fafc')} onMouseLeave={e => !modalLoading && (e.currentTarget.style.background = 'white')}>Cancel</button>
              <button 
                onClick={() => {
                  if (activeModal === 'bulk') handleUploadBulk();
                  if (activeModal === 'settings') handleSaveSettings();
                  if (activeModal === 'promo') handleCreatePromo();
                  if (activeModal === 'report') handleGenerateReport();
                }}
                disabled={modalLoading}
                style={{ padding: '12px 22px', borderRadius: '12px', border: 'none', background: ORANGE, color: 'white', fontSize: 14, fontWeight: 700, cursor: modalLoading ? 'wait' : 'pointer', opacity: modalLoading ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 12px rgba(249, 115, 22, 0.2)', transition: 'all 0.2s' }}
                onMouseEnter={e => !modalLoading && (e.currentTarget.style.background = ORANGE_DARK)}
                onMouseLeave={e => !modalLoading && (e.currentTarget.style.background = ORANGE)}
              >
                {modalLoading ? 'Processing...' : 
                 activeModal === 'report' ? 'Download Report' : 
                 activeModal === 'settings' ? 'Save Changes' : 
                 activeModal === 'promo' ? 'Create Promotion' : 
                 'Confirm Action'}
              </button>
            </div>
          </div>
          <style>{`
            @keyframes fadeInUp {
              from { opacity: 0; transform: translateY(16px) scale(0.95); }
              to { opacity: 1; transform: translateY(0) scale(1); }
            }
          `}</style>
        </div>
      )}
    </div>
  );
}
