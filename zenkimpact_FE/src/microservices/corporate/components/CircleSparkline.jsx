import React from 'react';

export default function CircleSparkline({ data, width = 150, height = 40, color = "#0CBEAA" }) {
  if (!data || data.length === 0) return null;

  // Normalize data for SVG
  const min = Math.min(...data) - 5;
  const max = Math.max(...data) + 5;
  const range = max - min;

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  // For the gradient fill area
  const fillPathD = `${pathD} L ${width},${height} L 0,${height} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`spark-grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fillPathD} fill={`url(#spark-grad-${color.replace('#', '')})`} />
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Last point dot */}
      <circle 
        cx={points[points.length - 1].split(',')[0]} 
        cy={points[points.length - 1].split(',')[1]} 
        r="3" 
        fill="white" 
        stroke={color} 
        strokeWidth="2" 
      />
    </svg>
  );
}
