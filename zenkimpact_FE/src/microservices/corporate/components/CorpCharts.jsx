import React, { useState } from 'react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
  AreaChart, Area,
} from 'recharts';

/* ── Shared Tooltip ─────────────────────────────────────────────────────── */
function CTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff', border: '1px solid #e8e8e4', borderRadius: 8,
      padding: '10px 14px', fontSize: 12, color: '#444', boxShadow: '0 4px 16px rgba(0,0,0,0.1)'
    }}>
      <div style={{ fontWeight: 700, marginBottom: 6, color: '#888', fontSize: 11 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 3 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
          <span style={{ color: '#888' }}>{p.name}:</span>
          <span style={{ fontWeight: 700, color: p.color }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ── ZenQ SVG Gauge ─────────────────────────────────────────────────────── */
export function ZenQGauge({ score = 78.4, size = 140 }) {
  const r = (size - 20) / 2;
  const circ = Math.PI * r;
  const fill = (score / 100) * circ;
  const cx = size / 2, cy = size / 2 + 10;
  return (
    <svg width={size} height={size * 0.75}>
      <defs>
        <linearGradient id="gG" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#0CBEAA" />
          <stop offset="100%" stopColor="#4A72F5" />
        </linearGradient>
      </defs>
      <path d={`M10 ${cy} A ${r} ${r} 0 0 1 ${size-10} ${cy}`} fill="none" stroke="#e8e8e4" strokeWidth="12" strokeLinecap="round" />
      <path d={`M10 ${cy} A ${r} ${r} 0 0 1 ${size-10} ${cy}`} fill="none" stroke="url(#gG)" strokeWidth="12" strokeLinecap="round"
        strokeDasharray={`${fill} ${circ}`} />
      <text x={cx} y={cy - 2} textAnchor="middle" fill="#4A72F5" fontSize="28" fontWeight="800" fontFamily="Inter">{score}</text>
      <text x={cx} y={cy + 18} textAnchor="middle" fill="#888" fontSize="10" fontFamily="Inter" letterSpacing="1.5" fontWeight="600">CORP ZENQ</text>
    </svg>
  );
}

/* ── ZenQ Trend Chart ───────────────────────────────────────────────────── */
export function ZenQTrendChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: -22 }}>
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4A72F5" stopOpacity={1} />
            <stop offset="100%" stopColor="#4A72F5" stopOpacity={0.6} />
          </linearGradient>
          <filter id="barShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#4A72F5" floodOpacity="0.2" />
          </filter>
        </defs>
        <CartesianGrid strokeDasharray="4 4" stroke="#eaeaec" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: '#888', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} dy={8} />
        <YAxis domain={[0, 100]} tick={{ fill: '#888', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} />
        <Tooltip content={<CTooltip />} cursor={{ fill: '#f8f9fa' }} />
        <Bar dataKey="corporate_score" name="Corp ZenQ" fill="url(#barGrad)" radius={[6, 6, 0, 0]} maxBarSize={36}
          label={{ position: 'top', fontSize: 11, fill: '#666', fontWeight: 600, formatter: v => v, dy: -6 }}
          filter="url(#barShadow)" />
        <Line dataKey="national_avg" name="National Avg" type="monotone" stroke="#F0A500"
          strokeWidth={2} strokeDasharray="6 4" dot={false} activeDot={{ r: 6, fill: '#F0A500', stroke: '#fff', strokeWidth: 2 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ── Allocation Donut ───────────────────────────────────────────────────── */
export function AllocationDonut({ circles = [] }) {
  const data = circles.map(c => ({ name: c.circle_name, value: c.allocation_pct, color: c.color }));
  return (
    <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <ResponsiveContainer width={220} height={220}>
        <PieChart>
          <defs>
            <filter id="pieShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="6" stdDeviation="8" floodColor="#000" floodOpacity="0.08" />
            </filter>
          </defs>
          <Pie data={data} cx="50%" cy="50%" innerRadius={65} outerRadius={90}
            paddingAngle={4} dataKey="value" stroke="none" filter="url(#pieShadow)">
            {data.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Pie>
          <Tooltip formatter={(v, n) => [`${v}%`, n]} contentStyle={{
            background: '#fff', border: '1px solid #e8e8e4', borderRadius: 8, fontSize: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.12)'
          }} />
        </PieChart>
      </ResponsiveContainer>
      <div style={{ position: 'absolute', textAlign: 'center', pointerEvents: 'none' }}>
        <div style={{ fontSize: 18, fontWeight: 900, color: '#1a1a1a', letterSpacing: '-0.02em' }}>₹1,00,000</div>
        <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 600, marginTop: 2 }}>Total CSR</div>
      </div>
    </div>
  );
}

/* ── Employee Hours Chart ───────────────────────────────────────────────── */
export function EmpHoursChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
        <defs>
          <linearGradient id="eG" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4A72F5" stopOpacity={0.15} />
            <stop offset="100%" stopColor="#4A72F5" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0ee" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: '#b0b0b0', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#b0b0b0', fontSize: 10 }} axisLine={false} tickLine={false} />
        <Tooltip content={<CTooltip />} />
        <Area type="monotone" dataKey="hours" name="Volunteer Hours" stroke="#4A72F5" fill="url(#eG)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
