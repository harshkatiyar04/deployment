import React, { useState } from 'react'
import { 
  BellIcon, 
  ShieldCheckIcon, 
  CreditCardIcon, 
  DocumentTextIcon,
  CpuChipIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline'

export default function SCSettings({ isLeader = false }) {
  const [activeTab, setActiveTab] = useState('Notifications')
  const [toggles, setToggles] = useState({
    emailUpdates: true,
    pushMilestones: true,
    publicAmount: false,
    kiaDetailed: true,
    autoPayEnabled: true,
    memberOversight: true,
    vendorApprovalRequired: false
  })
  const [panNumber, setPanNumber] = useState('ABCDE1234F')
  const [monthlyLimit, setMonthlyLimit] = useState('5000')

  const toggleSetting = (key) => setToggles(prev => ({ ...prev, [key]: !prev[key] }))

  const renderTabs = () => {
    const tabs = [
      { id: 'Notifications', icon: BellIcon },
      { id: 'Privacy', icon: ShieldCheckIcon },
      { id: 'Auto-Pay', icon: CreditCardIcon },
      { id: 'Tax Forms (80G)', icon: DocumentTextIcon },
      { id: 'Kia AI', icon: CpuChipIcon }
    ]
    if (isLeader) {
      tabs.push({ id: 'Leader Admin', icon: ShieldCheckIcon })
    }
    return tabs.map(tab => (
      <button 
        key={tab.id}
        className={`sc-settings-tab ${activeTab === tab.id ? 'active' : ''}`}
        onClick={() => setActiveTab(tab.id)}
      >
        <tab.icon className="w-5 h-5"/> {tab.id}
      </button>
    ))
  }

  return (
    <div className="sc-settings-view">
      <div className="sc-settings-header">
        <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>Circle Settings</h2>
        <p style={{ fontSize: '13px', color: 'var(--sc-text-muted)', marginTop: '4px' }}>
          Manage your notifications, privacy, payments, and tax documents.
        </p>
      </div>

      <div className="sc-settings-layout">
        
        {/* Navigation Sidebar for Settings */}
        <div className="sc-settings-sidebar">
          {renderTabs()}
        </div>

        {/* Content Area */}
        <div className="sc-settings-content">
          
          {activeTab === 'Notifications' && (
            <div className="sc-card">
              <div className="sc-card-title">Notification Preferences</div>
              <div className="sc-setting-row">
                <div>
                  <div className="sc-setting-title">Email Updates</div>
                  <div className="sc-setting-desc">Receive monthly statement summaries.</div>
                </div>
                <button className={`sc-toggle ${toggles.emailUpdates ? 'active' : ''}`} onClick={() => toggleSetting('emailUpdates')}><div className="sc-toggle-knob"></div></button>
              </div>
              <div className="sc-setting-row" style={{ borderBottom: 'none' }}>
                <div>
                  <div className="sc-setting-title">Push Milestones</div>
                  <div className="sc-setting-desc">Get notified when Ananya reaches academic goals.</div>
                </div>
                <button className={`sc-toggle ${toggles.pushMilestones ? 'active' : ''}`} onClick={() => toggleSetting('pushMilestones')}><div className="sc-toggle-knob"></div></button>
              </div>
            </div>
          )}

          {activeTab === 'Privacy' && (
            <div className="sc-card">
              <div className="sc-card-title">Privacy Controls</div>
              <div className="sc-setting-row" style={{ borderBottom: 'none' }}>
                <div>
                  <div className="sc-setting-title">Public Contribution Amount</div>
                  <div className="sc-setting-desc">Let other circle members see your exact ₹ contribution in leaderboards.</div>
                </div>
                <button className={`sc-toggle ${toggles.publicAmount ? 'active' : ''}`} onClick={() => toggleSetting('publicAmount')}><div className="sc-toggle-knob"></div></button>
              </div>
            </div>
          )}

          {activeTab === 'Auto-Pay' && (
            <div className="sc-card">
              <div className="sc-card-title">Payment Methods & Auto-Pay</div>
              <p className="sc-setting-desc" style={{ marginBottom: '20px' }}>Automate your contributions to ensure the circle never falls behind.</p>
              
              <div className="sc-payment-card">
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span className="sc-payment-brand">VISA</span>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>•••• 4242</div>
                    <div style={{ fontSize: '11px', color: 'var(--sc-text-muted)' }}>Expires 12/28</div>
                  </div>
                </div>
                <button style={{ background: 'none', border: 'none', color: 'var(--sc-red)', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>Remove</button>
              </div>

              <div className="sc-setting-row">
                <div>
                  <div className="sc-setting-title">Enable Monthly Auto-Pay</div>
                  <div className="sc-setting-desc">Automatically deduct funds when the circle requires capital.</div>
                </div>
                <button className={`sc-toggle ${toggles.autoPayEnabled ? 'active' : ''}`} onClick={() => toggleSetting('autoPayEnabled')}><div className="sc-toggle-knob"></div></button>
              </div>

              {toggles.autoPayEnabled && (
                <div className="sc-input-group" style={{ marginTop: '20px' }}>
                  <label className="sc-input-label">Maximum Monthly Limit (₹)</label>
                  <input 
                    type="number" 
                    className="sc-input" 
                    value={monthlyLimit} 
                    onChange={e => setMonthlyLimit(e.target.value)} 
                    style={{ maxWidth: '200px' }}
                  />
                  <div className="sc-setting-desc mt-1">We will never deduct more than this amount automatically.</div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'Tax Forms (80G)' && (
            <div className="sc-card">
              <div className="sc-card-title">Tax Exemption (80G)</div>
              <p className="sc-setting-desc" style={{ marginBottom: '20px' }}>Your contributions to ZENK Impact are eligible for 50% tax exemption under Section 80G.</p>
              
              <div className="sc-input-group" style={{ maxWidth: '300px', marginBottom: '24px' }}>
                <label className="sc-input-label">PAN Number</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input 
                    type="text" 
                    className="sc-input" 
                    value={panNumber} 
                    onChange={e => setPanNumber(e.target.value.toUpperCase())}
                    maxLength={10}
                    style={{ flex: 1, textTransform: 'uppercase' }}
                  />
                  <button className="sc-btn-outline" style={{ border: '1.5px solid var(--sc-green)', color: 'var(--sc-green-dark)' }}>Save</button>
                </div>
              </div>

              <div className="sc-setting-row" style={{ borderBottom: 'none', padding: '16px 0 0 0', borderTop: '1px solid var(--sc-border)' }}>
                <div>
                  <div className="sc-setting-title">Financial Year 2024-2025</div>
                  <div className="sc-setting-desc">Total Eligible Amount: ₹45,000</div>
                </div>
                <button className="sc-btn-primary" onClick={() => window.print()}>
                  <ArrowDownTrayIcon className="w-4 h-4"/> Download 80G Form
                </button>
              </div>
            </div>
          )}

          {activeTab === 'Kia AI' && (
            <div className="sc-card">
              <div className="sc-card-title">Kia AI Preferences</div>
              <div className="sc-setting-row" style={{ borderBottom: 'none' }}>
                <div>
                  <div className="sc-setting-title">Detailed Analysis</div>
                  <div className="sc-setting-desc">Kia will provide comprehensive financial breakdown instead of brief summaries.</div>
                </div>
                <button className={`sc-toggle ${toggles.kiaDetailed ? 'active' : ''}`} onClick={() => toggleSetting('kiaDetailed')}><div className="sc-toggle-knob"></div></button>
              </div>
            </div>
          )}

          {activeTab === 'Leader Admin' && isLeader && (
            <div className="sc-card">
              <div className="sc-card-title">Coordinator Preferences</div>
              <div className="sc-setting-row">
                <div>
                  <div className="sc-setting-title">Member Oversight Mode</div>
                  <div className="sc-setting-desc">Enable detailed tracking of other members' contributions and engagement levels.</div>
                </div>
                <button className={`sc-toggle ${toggles.memberOversight ? 'active' : ''}`} onClick={() => toggleSetting('memberOversight')}><div className="sc-toggle-knob"></div></button>
              </div>
              <div className="sc-setting-row" style={{ borderBottom: 'none' }}>
                <div>
                  <div className="sc-setting-title">Vendor Payment Approvals</div>
                  <div className="sc-setting-desc">Require coordinator approval before circle members can disburse funds to vendors.</div>
                </div>
                <button className={`sc-toggle ${toggles.vendorApprovalRequired ? 'active' : ''}`} onClick={() => toggleSetting('vendorApprovalRequired')}><div className="sc-toggle-knob"></div></button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
