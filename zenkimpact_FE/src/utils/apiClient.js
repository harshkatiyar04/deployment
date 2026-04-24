import axios from 'axios';

/**
 * Custom Axios API Client
 * 
 * Provides a standardized way to make API requests across the application.
 * Automatically handles features like attaching authorization tokens and 
 * standardizing error responses.
 */

const IS_DEV = import.meta.env.DEV;

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
  if (hostname.includes('vercel.app') || hostname.includes('zenk') || hostname.includes('railway.app')) {
    return 'https://deployment-production-27bd.up.railway.app';
  }
  return 'http://localhost:8000';
};

const BASE_URL = getApiBase();

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30 seconds — handles Railway cold start
  headers: {
    'Content-Type': 'application/json',
  },
});

// Warm up Railway server in background (prevents cold-start timeout on first real request)
const isProduction = BASE_URL.includes('railway.app');
if (isProduction) {
  axios.get(`${BASE_URL}/health`, { timeout: 60000 }).catch(() => {});
}

// -------------------------------------------------------------
// REQUEST INTERCEPTOR
// -------------------------------------------------------------
apiClient.interceptors.request.use(
  (config) => {
    // Read from sessionStorage (safer — cleared when tab closes)
    const token = sessionStorage.getItem('zenk_token') || localStorage.getItem('zenk_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Only log in development — never expose URLs/headers in production
    if (IS_DEV) {
      console.log(`[ZenkAPI] Request to: ${config.baseURL}${config.url}`);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// -------------------------------------------------------------
// RESPONSE INTERCEPTOR
// -------------------------------------------------------------
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const status = error.response.status;

      if (status === 401) {
        // Token expired — clear it so next request forces re-login
        sessionStorage.removeItem('zenk_token');
        localStorage.removeItem('zenk_token');
      }

      const cleanError = error.response.data?.message || error.response.data?.detail || 'An unexpected server error occurred.';
      return Promise.reject(new Error(cleanError));
    } else if (error.request) {
      return Promise.reject(new Error('Unable to connect to the server. Please check your internet connection.'));
    } else {
      return Promise.reject(error);
    }
  }
);

export default apiClient;
