/** API client for backend services. */

// In production, set VITE_API_BASE_URL to the Payment Service ALB URL
// For local dev, Vite proxy handles /api/* routing
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

function getBase(path: string): string {
  // If API_BASE already includes /api/v1, use it directly
  if (API_BASE.startsWith('http')) {
    return `${API_BASE}${path}`;
  }
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = getBase(path);
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  // Payments
  createPayment: (data: object) => request<object>('/payments', { method: 'POST', body: JSON.stringify(data) }),
  getTransaction: (id: string) => request<object>(`/payments/${id}`),
  listTransactions: (params?: string) => request<object>(`/payments${params ? `?${params}` : ''}`),

  // Merchants
  register: (data: object) => request<object>('/merchants/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: object) => request<object>('/merchants/login', { method: 'POST', body: JSON.stringify(data) }),
  logout: (sessionId: string) => request<object>(`/merchants/logout?session_id=${sessionId}`, { method: 'POST' }),
  listMerchants: () => request<object[]>('/merchants/list'),
  getMerchant: (merchantId: string) => request<object>(`/merchants/${merchantId}`),
  listApiKeys: (merchantId: string) => request<object[]>(`/merchants/${merchantId}/api-keys`),
  generateApiKey: (merchantId: string) => request<object>(`/merchants/${merchantId}/api-keys`, { method: 'POST' }),
  revokeApiKey: (merchantId: string, keyId: string) => request<void>(`/merchants/${merchantId}/api-keys/${keyId}`, { method: 'DELETE' }),

  // Analytics
  getSummary: (params?: string) => request<object>(`/analytics/summary${params ? `?${params}` : ''}`),
  getSuccessRates: (params?: string) => request<object>(`/analytics/success-rates${params ? `?${params}` : ''}`),
  getDistribution: (params?: string) => request<object>(`/analytics/distribution${params ? `?${params}` : ''}`),
  getVolume: (params?: string) => request<object>(`/analytics/volume${params ? `?${params}` : ''}`),

  // Merchant Analytics (admin)
  getMerchantStats: () => request<object>('/merchants/stats/summary'),

  // Simulate Traffic
  simulateTraffic: (count: number, profile: string, merchantId: string) =>
    request<object>(`/simulate/traffic?count=${count}&profile=${profile}&merchant_id=${merchantId}`, { method: 'POST' }),

  // Service Health
  getServiceHealth: () => request<object>('/services/health'),
};
