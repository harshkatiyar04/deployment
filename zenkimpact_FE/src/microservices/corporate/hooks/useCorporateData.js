import { useState, useEffect, useCallback } from 'react';

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
  if (hostname.includes('vercel.app') || hostname.includes('zenk') || hostname.includes('railway.app')) {
    return 'https://deployment-production-27bd.up.railway.app';
  }
  return 'http://localhost:8000';
};
const API_BASE = getApiBase();
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};

export function useCorporateData(fy = '2025-26') {
  const [profile, setProfile] = useState(null);
  const [zenqOverview, setZenqOverview] = useState(null);
  const [allocations, setAllocations] = useState(null);
  const [circlesPerf, setCirclesPerf] = useState(null);
  const [employees, setEmployees] = useState(null);
  const [csrAccount, setCsrAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async (fiscalYear = fy) => {
    setLoading(true);
    setError(null);
    try {
      const headers = getAuthHeaders();
      const [profRes, zenqRes, allocRes, perfRes, empRes, csrRes] = await Promise.all([
        fetch(`${API_BASE}/corporate/profile`, { headers }),
        fetch(`${API_BASE}/corporate/zenq-overview?fy=${fiscalYear}`, { headers }),
        fetch(`${API_BASE}/corporate/allocations`, { headers }),
        fetch(`${API_BASE}/corporate/circles-performance`, { headers }),
        fetch(`${API_BASE}/corporate/employees`, { headers }),
        fetch(`${API_BASE}/corporate/csr-account`, { headers }),
      ]);

      if (!profRes.ok) throw new Error('Unauthorized or session expired');

      const [profData, zenqData, allocData, perfData, empData, csrData] = await Promise.all([
        profRes.json(), zenqRes.json(), allocRes.json(),
        perfRes.json(), empRes.json(), csrRes.json(),
      ]);

      setProfile(profData);
      setZenqOverview(zenqData);
      setAllocations(allocData);
      setCirclesPerf(perfData);
      setEmployees(empData);
      setCsrAccount(csrData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [fy]);

  useEffect(() => { fetchAll(fy); }, [fy]);

  const reallocate = async (items) => {
    const res = await fetch(`${API_BASE}/corporate/reallocate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ allocations: items, fiscal_year: fy }),
    });
    if (!res.ok) throw new Error('Reallocation failed');
    return res.json();
  };

  return {
    profile, zenqOverview, allocations, circlesPerf, employees, csrAccount,
    loading, error, refresh: fetchAll, reallocate,
  };
}
