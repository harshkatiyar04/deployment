import React, { useState } from 'react';
import apiClient from '../../../utils/apiClient';
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  CubeIcon,
  PhotoIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

export default function VendorProducts({ products, loading, onRefresh, showToast }) {
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '', category: '', sku: '', description: '',
    price: '', mrp: '', student_price: '', student_discount: 0,
    member_discount: 10, stock_quantity: '', image_url: '',
  });

  const categories = ['All', ...new Set((products || []).map(p => p.category))];

  const filtered = (products || []).filter(p => {
    if (categoryFilter !== 'All' && p.category !== categoryFilter) return false;
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const openAdd = () => {
    setEditingProduct(null);
    setFormData({ name: '', category: '', sku: '', description: '', price: '', mrp: '', student_price: '', student_discount: 0, member_discount: 10, stock_quantity: '', image_url: '' });
    setShowAddModal(true);
  };

  const openEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name, category: product.category, sku: product.sku || '',
      description: product.description || '', price: product.price, mrp: product.mrp,
      student_price: product.student_price || '', student_discount: product.student_discount,
      member_discount: product.member_discount, stock_quantity: product.stock_quantity,
      image_url: product.image_url || '',
    });
    setShowAddModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        price: parseFloat(formData.price),
        mrp: parseFloat(formData.mrp),
        student_price: formData.student_price ? parseFloat(formData.student_price) : null,
        stock_quantity: parseInt(formData.stock_quantity) || 0,
      };

      if (editingProduct) {
        await apiClient.put(`/vendor/products/${editingProduct.id}`, payload);
        showToast('✅ Product updated successfully');
      } else {
        await apiClient.post('/vendor/products', payload);
        showToast('✅ Product added successfully');
      }
      setShowAddModal(false);
      onRefresh();
    } catch (err) {
      showToast(`❌ ${err.message}`);
    }
  };

  const handleToggleActive = async (product) => {
    const action = product.is_active ? 'deactivate' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} this product?`)) return;
    try {
      await apiClient.put(`/vendor/products/${product.id}`, { is_active: !product.is_active });
      showToast(product.is_active ? '🗑️ Product deactivated' : '✅ Product activated');
      onRefresh();
    } catch (err) {
      showToast(`❌ ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="vp-page-header"><div><h1>Products</h1><p>Loading inventory...</p></div></div>
        <div className="vp-product-grid">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="vp-product-card">
              <div className="vp-product-img"><div className="vp-skeleton" style={{ width: '100%', height: '100%' }} /></div>
              <div className="vp-product-info">
                <div className="vp-skeleton" style={{ width: '80%', height: 14, marginBottom: 8 }} />
                <div className="vp-skeleton" style={{ width: '50%', height: 12 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="vp-page-header">
        <div>
          <h1>Product Catalog</h1>
          <p>{filtered.length} products in your inventory</p>
        </div>
        <button className="vp-btn vp-btn-primary" onClick={openAdd}>
          <PlusIcon style={{ width: 16, height: 16 }} /> Add Product
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <MagnifyingGlassIcon style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', width: 16, height: 16, color: '#94a3b8' }} />
          <input
            type="text" placeholder="Search products..."
            value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '9px 12px 9px 36px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 13, outline: 'none' }}
          />
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <button key={cat} onClick={() => setCategoryFilter(cat)}
              className={`vp-btn vp-btn-sm ${categoryFilter === cat ? 'vp-btn-primary' : 'vp-btn-outline'}`}
            >{cat}</button>
          ))}
        </div>
      </div>

      {/* Product Grid */}
      {filtered.length === 0 ? (
        <div className="vp-card">
          <div className="vp-empty">
            <CubeIcon />
            <h4>No products found</h4>
            <p>Try adjusting your filters or add a new product.</p>
          </div>
        </div>
      ) : (
        <div className="vp-product-grid" style={{ padding: 0 }}>
          {filtered.map(product => (
            <div key={product.id} className="vp-product-card">
              <div className="vp-product-img">
                {product.image_url ? (
                  <img src={product.image_url} alt={product.name} />
                ) : (
                  <PhotoIcon style={{ width: 40, height: 40, color: '#cbd5e1' }} />
                )}
              </div>
              <div className="vp-product-info">
                <div className="category">{product.category}</div>
                <h4>{product.name}</h4>
                <div className="price">
                  {product.discounted_price && product.discounted_price < product.price ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ color: '#0f766e', fontWeight: 800 }}>₹{product.discounted_price.toLocaleString('en-IN')}</span>
                      <span style={{ fontSize: 11, color: '#94a3b8', textDecoration: 'line-through' }}>₹{product.price.toLocaleString('en-IN')}</span>
                    </div>
                  ) : (
                    `₹${product.price?.toLocaleString('en-IN')}`
                  )}
                </div>
                {product.active_promotion_title && (
                  <div style={{ marginTop: 4 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#b45309', background: '#fffbeb', padding: '2px 6px', borderRadius: 4, border: '1px solid #fde68a' }}>
                      🔥 {product.active_promotion_title}
                    </span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                  <span className={`stock ${product.stock_quantity === 0 ? 'out' : product.stock_quantity <= 10 ? 'low' : 'in'}`}>
                    {product.stock_quantity === 0 ? 'Out of stock' : `${product.stock_quantity} in stock`}
                  </span>
                  {!product.is_active && <span className="vp-badge cancelled">Inactive</span>}
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                  <button className="vp-btn vp-btn-outline vp-btn-sm" onClick={() => openEdit(product)}>
                    <PencilSquareIcon style={{ width: 14, height: 14 }} /> Edit
                  </button>
                  <button 
                    className="vp-btn vp-btn-outline vp-btn-sm" 
                    style={{ color: product.is_active ? '#dc2626' : '#16a34a' }} 
                    onClick={() => handleToggleActive(product)}
                  >
                    {product.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,.4)', backdropFilter: 'blur(4px)' }}>
          <div style={{ background: 'white', borderRadius: 16, width: '100%', maxWidth: 520, maxHeight: '90vh', overflow: 'auto', boxShadow: '0 24px 48px rgba(0,0,0,.15)' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{editingProduct ? 'Edit Product' : 'Add New Product'}</h3>
              <button onClick={() => setShowAddModal(false)} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>✕</button>
            </div>
            <form onSubmit={handleSubmit} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                { label: 'Product Name*', key: 'name', type: 'text', required: true },
                { label: 'Category*', key: 'category', type: 'text', required: true },
                { label: 'SKU', key: 'sku', type: 'text' },
                { label: 'Description', key: 'description', type: 'text' },
                { label: 'MRP (₹)*', key: 'mrp', type: 'number', required: true },
                { label: 'Selling Price (₹)*', key: 'price', type: 'number', required: true },
                { label: 'Student Price (₹)', key: 'student_price', type: 'number' },
                { label: 'Stock Quantity*', key: 'stock_quantity', type: 'number', required: true },
              ].map(field => (
                <div key={field.key}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#64748b', display: 'block', marginBottom: 4 }}>{field.label}</label>
                  <input
                    type={field.type} value={formData[field.key]} required={field.required}
                    onChange={e => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, outline: 'none' }}
                  />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#64748b', display: 'block', marginBottom: 4 }}>Product Image</label>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <input
                    type="text" value={formData.image_url} placeholder="Image URL (or upload a file)"
                    onChange={e => setFormData(prev => ({ ...prev, image_url: e.target.value }))}
                    style={{ flex: 1, padding: '9px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, outline: 'none' }}
                  />
                  <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>OR</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={e => {
                      const file = e.target.files[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onloadend = () => {
                          setFormData(prev => ({ ...prev, image_url: reader.result }));
                        };
                        reader.readAsDataURL(file);
                      }
                    }}
                    style={{ flex: 1, padding: '6px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
                  />
                </div>
                {formData.image_url && (
                   <div style={{ marginTop: 8 }}>
                     <img src={formData.image_url} alt="Preview" style={{ height: 60, borderRadius: 8, objectFit: 'cover' }} />
                   </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
                <button type="button" onClick={() => setShowAddModal(false)} className="vp-btn vp-btn-outline">Cancel</button>
                <button type="submit" className="vp-btn vp-btn-primary">{editingProduct ? 'Save Changes' : 'Add Product'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
