import React, { useState } from 'react';

export default function AllocationModal({ circle, available, onClose, onConfirm }) {
  const [amount, setAmount] = useState(5000);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    await onConfirm([{ circle_name: circle.circle_name, amount }]);
    setLoading(false);
    onClose();
  };

  return (
    <div className="c-modal-overlay">
      <div className="c-modal">
        <div className="c-modal-header">
          <h3>Increase Allocation</h3>
          <button className="c-btn-icon" onClick={onClose}>×</button>
        </div>
        <div className="c-modal-body">
          <p>You are increasing funding for <strong>{circle.circle_name}</strong>.</p>
          <div className="c-modal-info">
            <span>Available Unallocated:</span>
            <strong>₹{available.toLocaleString()}</strong>
          </div>
          
          <div className="c-input-group" style={{ marginTop: 20 }}>
            <label>Amount to allocate (₹)</label>
            <input 
              type="number" 
              value={amount} 
              onChange={e => setAmount(Number(e.target.value))}
              min={1000}
              max={available}
              step={1000}
              className="c-input"
            />
          </div>
          
          <div className="c-modal-insight">
            <div className="c-k-avatar">K</div>
            <span>Increasing by ₹{amount.toLocaleString()} is predicted to raise their ZenQ by +{(amount/5000).toFixed(1)} pts over 3 months.</span>
          </div>
        </div>
        <div className="c-modal-footer">
          <button className="c-btn c-btn-outline" onClick={onClose} disabled={loading}>Cancel</button>
          <button className="c-btn c-btn-primary" onClick={handleSubmit} disabled={loading || amount <= 0 || amount > available}>
            {loading ? 'Processing...' : `Confirm ₹${amount.toLocaleString()}`}
          </button>
        </div>
      </div>
    </div>
  );
}
