import { useState, useEffect } from 'react';

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
  if (hostname.includes('vercel.app') || hostname.includes('zenk') || hostname.includes('railway.app')) {
    return 'https://deployment-production-27bd.up.railway.app';
  }
  return 'http://localhost:8000';
};
const API_BASE = getApiBase();

export function useCirclePerformanceLive(initialCircles) {
  const [liveData, setLiveData] = useState({});

  useEffect(() => {
    if (!initialCircles || initialCircles.length === 0) return;

    const token = localStorage.getItem('access_token');
    const headers = { Authorization: `Bearer ${token}` };

    const fetchLive = async () => {
      try {
        const res = await fetch(`${API_BASE}/corporate/circles-performance/live`, { headers });
        if (res.ok) {
          const data = await res.json();
          const newLiveData = {};
          data.circles.forEach(c => {
            newLiveData[c.circle_name] = c.live_zenq;
          });
          setLiveData(newLiveData);
        }
      } catch (err) {
        console.error('Failed to fetch live ZenQ:', err);
      }
    };

    fetchLive();
    const interval = setInterval(fetchLive, 30000); // 30s poll
    return () => clearInterval(interval);
  }, [initialCircles]);

  return liveData;
}
