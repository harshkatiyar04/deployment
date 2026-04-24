import React, { useState } from 'react';
import apiClient from '../../utils/apiClient';
import {
  ShoppingBagIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  BuildingStorefrontIcon,
  CheckBadgeIcon,
  TruckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

const mockOrders = [
  { id: '#ORD-9921', item: 'Class 9 Science (NCERT)', buyer: 'Student Fund (Ashoka Rising)', amount: '₹360', status: 'Processing', date: '2 hours ago' },
  { id: '#ORD-9920', item: 'Scientific Calculator', buyer: 'Member Purchase', amount: '₹1,080', status: 'Shipped', date: '5 hours ago' },
  { id: '#ORD-9919', item: 'Premium Stationery Pack', buyer: 'Student Fund (Sunrise Circle)', amount: '₹520', status: 'Delivered', date: 'Yesterday' },
  { id: '#ORD-9918', item: 'Jio 6-Month Data Plan', buyer: 'Student Fund (Ashoka Rising)', amount: '₹1,440', status: 'Active', date: '2 days ago' },
];

export default function VendorDashboardView() {
  const [activeModal, setActiveModal] = useState(null);
  
  // Leader Request State
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestFormData, setRequestFormData] = useState({
    title: '', category: 'Stationery', quantity_needed: 1, 
    budget_per_unit: '', target_audience: '', priority: 'medium', description: ''
  });
  const [requestStatus, setRequestStatus] = useState(null);

  const handleRequestSubmit = async (e) => {
    e.preventDefault();
    setRequestStatus('submitting');
    try {
      const payload = {
        ...requestFormData,
        quantity_needed: parseInt(requestFormData.quantity_needed) || 1,
        budget_per_unit: requestFormData.budget_per_unit ? parseFloat(requestFormData.budget_per_unit) : null,
      };
      
      await apiClient.post('/vendor/requests/submit', payload);
      
      setRequestStatus('success');
      setTimeout(() => {
        setShowRequestModal(false);
        setRequestStatus(null);
        setRequestFormData({ title: '', category: 'Stationery', quantity_needed: 1, budget_per_unit: '', target_audience: '', priority: 'medium', description: '' });
      }, 2000);
    } catch (err) {
      console.error(err);
      setRequestStatus('error');
    }
  };
  
  const kpiCards = [
    { title: 'Total Orders', value: '142', icon: ShoppingBagIcon, color: 'blue', change: '+12%' },
    { title: 'Revenue (CSR Fund)', value: '₹45,200', icon: CurrencyDollarIcon, color: 'green', change: '+8%' },
    { title: 'Active Products', value: '18', icon: BuildingStorefrontIcon, color: 'purple' },
    { title: 'ZenK Rating', value: '4.7', icon: ChartBarIcon, color: 'yellow' }
  ];

  return (
    <div className="flex flex-col min-h-0 bg-[#f8fafc] overflow-y-auto w-full">
      <div className="p-6 max-w-7xl mx-auto w-full">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">Vendor Management</h1>
              <span className="flex items-center gap-1 text-xs uppercase tracking-wider font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                <CheckBadgeIcon className="w-4 h-4" /> ZenK Verified Vendor
              </span>
            </div>
            <p className="text-gray-600">Manage your educational marketplace products and circle orders.</p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => setShowRequestModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg font-bold text-sm shadow-sm transition-colors flex items-center justify-center"
            >
              Request Custom Product
            </button>
            <button 
              onClick={() => setActiveModal({ title: 'Add New Product', content: 'The product listing wizard will open here to guide you through adding educational items.' })}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-lg font-bold text-sm shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              Add New Product
            </button>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {kpiCards.map((card) => {
            const Icon = card.icon;
            const colorClasses = {
              blue: 'bg-blue-50 text-blue-600 border-blue-100',
              green: 'bg-emerald-50 text-emerald-600 border-emerald-100',
              purple: 'bg-purple-50 text-purple-600 border-purple-100',
              yellow: 'bg-orange-50 text-orange-600 border-orange-100'
            };
            return (
              <div key={card.title} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-gray-500">{card.title}</p>
                  <div className={`p-2 rounded-lg border ${colorClasses[card.color]}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-gray-900 mb-1">{card.value}</p>
                {card.change && <p className="text-xs font-medium text-emerald-600">{card.change} from last month</p>}
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Recent Orders */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Recent Orders</h2>
              <button onClick={() => setActiveModal({ title: 'All Orders', content: 'Full historical order database view goes here, with filtering and exports.' })} className="text-sm font-bold text-emerald-600 hover:text-emerald-700">View All</button>
            </div>
            <div className="divide-y divide-gray-100">
              {mockOrders.map(order => (
                <div key={order.id} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-gray-50 transition-colors">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-mono text-sm font-bold text-gray-500">{order.id}</span>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${order.status === 'Processing' ? 'bg-orange-100 text-orange-700' : order.status === 'Shipped' ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700'}`}>
                        {order.status}
                      </span>
                    </div>
                    <p className="font-bold text-gray-900 text-sm mb-1">{order.item}</p>
                    <p className="text-xs text-gray-500">{order.buyer} • {order.date}</p>
                  </div>
                  <div className="flex items-center justify-between sm:flex-col sm:items-end gap-2">
                    <p className="font-bold text-lg text-gray-900">{order.amount}</p>
                    <button 
                      onClick={() => setActiveModal({ title: `Order ${order.id}`, content: `Order management view for ${order.item}. You can update tracking info or contact the buyer here.` })}
                      className="text-xs font-bold text-gray-600 border border-gray-200 bg-white hover:bg-gray-50 px-3 py-1.5 rounded-lg shadow-sm"
                    >
                      Manage order
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions & Status */}
          <div className="space-y-6">
            <div className="bg-emerald-600 rounded-xl shadow-sm p-6 text-white relative overflow-hidden">
               <div className="absolute -right-6 -top-6 text-emerald-500 opacity-30">
                 <TruckIcon className="w-32 h-32" />
               </div>
               <div className="relative z-10">
                 <h3 className="text-lg font-bold mb-2">Fast Delivery Promise</h3>
                 <p className="text-emerald-50 text-sm leading-relaxed mb-4">You have maintained a 98% on-time delivery rate. Keep it up to retain your "Fast delivery" profile badge.</p>
                 <button 
                   onClick={() => setActiveModal({ title: 'Performance Metrics', content: 'Detailed breakdown of delivery times, cancellations, and SLA tracking.' })}
                   className="bg-white text-emerald-700 text-sm font-bold px-4 py-2 rounded-lg shadow-sm hover:bg-emerald-50 transition-colors w-full"
                 >
                   Review Shipping Metrics
                 </button>
               </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider">Inventory Alerts</h3>
              
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-red-500 mt-1.5 flex-shrink-0"></div>
                  <div>
                    <p className="text-sm font-bold text-gray-900 mb-0.5">School Bag, 15L</p>
                    <p className="text-xs text-gray-500">Out of stock. 3 students have this in their wishlist.</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-orange-400 mt-1.5 flex-shrink-0"></div>
                  <div>
                    <p className="text-sm font-bold text-gray-900 mb-0.5">Class 9 Science</p>
                    <p className="text-xs text-gray-500">Low stock (4 remaining). High demand expected this week.</p>
                  </div>
                </div>
              </div>
              
              <button 
                onClick={() => setActiveModal({ title: 'Inventory Sync', content: 'Inventory sync initiated. Pulling latest numbers from your connected ERP...' })}
                className="mt-5 text-sm font-bold text-emerald-600 hover:text-emerald-700 w-full text-center border border-emerald-100 bg-emerald-50 py-2 rounded-lg transition-colors"
              >
                Update Inventory
              </button>
            </div>
          </div>

        </div>
      </div>

      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm shadow-2xl transition-opacity animate-in fade-in">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden transform scale-100 transition-transform">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-bold text-gray-900">{activeModal.title}</h3>
              <button onClick={() => setActiveModal(null)} className="text-gray-400 hover:text-gray-600 rounded-full p-1 bg-gray-50 transition-colors">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 bg-gray-50 text-gray-600 text-sm leading-relaxed border-b border-gray-100">
               {activeModal.content}
            </div>
            <div className="p-4 bg-white flex justify-end">
              <button onClick={() => setActiveModal(null)} className="px-5 py-2.5 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-sm rounded-xl transition-colors">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Custom Item Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm shadow-2xl transition-opacity">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden transform scale-100 transition-transform flex flex-col max-h-[90vh]">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div>
                <h3 className="font-bold text-gray-900 flex items-center gap-2">
                  Request Custom Product
                </h3>
                <p className="text-xs text-gray-500 mt-1">Submit a request to the vendor for an item not in the catalog.</p>
              </div>
              <button onClick={() => setShowRequestModal(false)} className="text-gray-400 hover:text-gray-600 rounded-full p-1 bg-gray-50 transition-colors self-start">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleRequestSubmit} className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Item Title*</label>
                <input required type="text" value={requestFormData.title} onChange={e => setRequestFormData({...requestFormData, title: e.target.value})} placeholder="e.g. 50 Science Textbooks for Class 10" className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500" />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Category</label>
                  <select value={requestFormData.category} onChange={e => setRequestFormData({...requestFormData, category: e.target.value})} className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500 bg-white">
                    <option>School Books</option>
                    <option>Stationery</option>
                    <option>Electronics</option>
                    <option>Connectivity</option>
                    <option>Furniture</option>
                    <option>Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Priority</label>
                  <select value={requestFormData.priority} onChange={e => setRequestFormData({...requestFormData, priority: e.target.value})} className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500 bg-white">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Quantity Needed*</label>
                  <input required type="number" min="1" value={requestFormData.quantity_needed} onChange={e => setRequestFormData({...requestFormData, quantity_needed: e.target.value})} className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Budget per unit (₹)</label>
                  <input type="number" min="0" value={requestFormData.budget_per_unit} onChange={e => setRequestFormData({...requestFormData, budget_per_unit: e.target.value})} placeholder="Optional" className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Target Audience / Notes</label>
                <input type="text" value={requestFormData.target_audience} onChange={e => setRequestFormData({...requestFormData, target_audience: e.target.value})} placeholder="e.g. Class 10 Students, Art Club Members" className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500" />
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Description</label>
                <textarea value={requestFormData.description} onChange={e => setRequestFormData({...requestFormData, description: e.target.value})} placeholder="Additional details..." className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:border-blue-500 resize-none h-20" />
              </div>
              
              {requestStatus === 'success' && (
                <div className="bg-green-50 text-green-700 p-3 rounded-xl text-sm font-bold flex items-center gap-2">
                  Request submitted successfully!
                </div>
              )}
              {requestStatus === 'error' && (
                <div className="bg-red-50 text-red-700 p-3 rounded-xl text-sm font-bold">
                  Failed to submit request. Please try again.
                </div>
              )}
            </form>
            <div className="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 shrink-0">
              <button type="button" onClick={() => setShowRequestModal(false)} className="px-5 py-2.5 text-sm font-bold text-gray-600 hover:text-gray-900 bg-white border border-gray-200 shadow-sm rounded-xl transition-colors">Cancel</button>
              <button 
                onClick={handleRequestSubmit} 
                disabled={requestStatus === 'submitting' || requestStatus === 'success'}
                className="px-5 py-2.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm rounded-xl transition-colors disabled:opacity-50"
              >
                {requestStatus === 'submitting' ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
