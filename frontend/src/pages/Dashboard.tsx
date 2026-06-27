import { useEffect, useState } from 'react';
import type { DashboardSummary, SuccessRateData, PaymentDistributionItem } from '../types';
import { api } from '../api/client';

type DashTab = 'payments' | 'merchants' | 'services';

export function Dashboard() {
  const [tab, setTab] = useState<DashTab>('payments');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [rates, setRates] = useState<SuccessRateData | null>(null);
  const [distribution, setDistribution] = useState<PaymentDistributionItem[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [merchantStats, setMerchantStats] = useState<any>(null);
  const [merchants, setMerchants] = useState<any[]>([]);
  const [serviceHealth, setServiceHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [s, r, d, t, ms, m] = await Promise.all([
        api.getSummary() as Promise<DashboardSummary>,
        api.getSuccessRates() as Promise<SuccessRateData>,
        api.getDistribution() as Promise<{ data: PaymentDistributionItem[]; total: number }>,
        api.listTransactions('limit=15') as Promise<{ items: any[] }>,
        api.getMerchantStats().catch(() => null),
        api.listMerchants().catch(() => []),
      ]);
      setSummary(s); setRates(r); setDistribution(d.data); setTransactions(t.items || []);
      setMerchantStats(ms); setMerchants(m as any[]);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load'); }
    finally { setLoading(false); }
  };

  const loadHealth = async () => {
    try { const h = await api.getServiceHealth(); setServiceHealth(h); } catch {}
  };

  useEffect(() => { if (tab === 'services') loadHealth(); }, [tab]);

  if (loading) return <p style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>⏳ Loading dashboard...</p>;
  if (error) return <div className="result-box error">{error}</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h1>📊 Admin Dashboard</h1>
          <p style={{ color: '#64748b' }}>Platform-wide monitoring for administrators</p>
        </div>
        <button onClick={loadAll} className="btn-small">↻ Refresh All</button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
        {(['payments', 'merchants', 'services'] as DashTab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#eef2ff' : 'transparent', color: tab === t ? '#4f46e5' : '#64748b', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', fontWeight: tab === t ? 600 : 400 }}>
            {t === 'payments' && '💰 Payments'}
            {t === 'merchants' && '🏪 Merchants'}
            {t === 'services' && '🖥️ Services'}
          </button>
        ))}
      </div>

      {/* PAYMENTS TAB */}
      {tab === 'payments' && (
        <div>
          {/* Simulate Traffic Panel */}
          <div className="card" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <strong>🤖 Traffic Simulator</strong>
              <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '0.25rem 0 0' }}>Generate test payments to populate analytics</p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <select id="sim-count" defaultValue="20" style={{ width: '80px', padding: '0.4rem' }}>
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
              <select id="sim-profile" defaultValue="mixed" style={{ width: '120px', padding: '0.4rem' }}>
                <option value="mixed">Mixed</option>
                <option value="cards_only">Cards Only</option>
                <option value="upi_heavy">UPI Heavy</option>
                <option value="burst">Even Split</option>
              </select>
              <button
                className="btn-small"
                disabled={simulating}
                onClick={async () => {
                  setSimulating(true); setSimResult(null);
                  const count = parseInt((document.getElementById('sim-count') as HTMLSelectElement).value);
                  const profile = (document.getElementById('sim-profile') as HTMLSelectElement).value;
                  const merchantId = merchants.length > 0 ? merchants[0].id : 'demo';
                  try {
                    const r = await api.simulateTraffic(count, profile, merchantId);
                    setSimResult(r);
                    await loadAll(); // Refresh data
                  } catch (e) { setError('Simulation failed'); }
                  setSimulating(false);
                }}
              >
                {simulating ? '⏳ Generating...' : '▶️ Generate'}
              </button>
            </div>
            {simResult && (
              <div style={{ width: '100%', fontSize: '0.85rem', color: '#10b981' }}>
                ✅ Generated {(simResult as any).total} payments — {(simResult as any).success} success, {(simResult as any).failed} failed
              </div>
            )}
          </div>

          {summary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
              <div className="card stat-card"><h3>Total Transactions</h3><p className="stat-value">{summary.total_transactions}</p></div>
              <div className="card stat-card"><h3>Success Rate</h3><p className="stat-value" style={{ color: '#10b981' }}>{summary.success_rate}%</p></div>
              <div className="card stat-card"><h3>Total Volume</h3><p className="stat-value">₹{Number(summary.total_volume).toLocaleString()}</p></div>
              <div className="card stat-card"><h3>Payment Types</h3><p className="stat-value">{summary.payment_types}</p></div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            {rates && (
              <div>
                <h2>Status Breakdown</h2>
                <div className="card">
                  <div className="rate-bar">
                    <div className="rate-segment success" style={{ width: `${rates.total > 0 ? (rates.success_count / rates.total * 100) : 0}%` }}>{rates.success_count > 0 && `✅ ${rates.success_count}`}</div>
                    <div className="rate-segment failed" style={{ width: `${rates.total > 0 ? (rates.failure_count / rates.total * 100) : 0}%` }}>{rates.failure_count > 0 && `❌ ${rates.failure_count}`}</div>
                    <div className="rate-segment pending" style={{ width: `${rates.total > 0 ? (rates.pending_count / rates.total * 100) : 0}%` }}>{rates.pending_count > 0 && `⏳ ${rates.pending_count}`}</div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.85rem', color: '#64748b' }}>
                    <span>Success: {rates.success_count}</span><span>Failed: {rates.failure_count}</span><span>Pending: {rates.pending_count}</span>
                  </div>
                </div>
              </div>
            )}
            {distribution.length > 0 && (
              <div>
                <h2>Payment Methods</h2>
                <div className="card">
                  {distribution.map(item => (
                    <div key={item.payment_type} style={{ marginBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span>{item.payment_type}</span><span style={{ fontWeight: 600 }}>{item.count} ({item.percentage}%)</span>
                      </div>
                      <div style={{ background: '#e2e8f0', borderRadius: '4px', height: '8px' }}>
                        <div style={{ background: '#4f46e5', borderRadius: '4px', height: '8px', width: `${item.percentage}%`, transition: 'width 0.5s' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <h2 style={{ marginTop: '2rem' }}>Recent Transactions</h2>
          {transactions.length === 0 ? <p style={{ color: '#64748b' }}>No transactions.</p> : (
            <table>
              <thead><tr><th>Status</th><th>Amount</th><th>Type</th><th>Merchant</th><th>Time</th></tr></thead>
              <tbody>
                {transactions.map((txn: any) => (
                  <tr key={txn.id}>
                    <td><span className={`status-badge ${txn.status.toLowerCase()}`}>{txn.status}</span></td>
                    <td style={{ fontWeight: 600 }}>₹{txn.amount}</td>
                    <td>{txn.payment_type}</td>
                    <td><code style={{ fontSize: '0.75rem' }}>{txn.merchant_id.substring(0, 8)}...</code></td>
                    <td style={{ fontSize: '0.85rem', color: '#64748b' }}>{new Date(txn.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* MERCHANTS TAB */}
      {tab === 'merchants' && (
        <div>
          {merchantStats && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                <div className="card stat-card"><h3>Total Merchants</h3><p className="stat-value">{merchantStats.total_merchants}</p></div>
                <div className="card stat-card"><h3>Active</h3><p className="stat-value" style={{ color: '#10b981' }}>{merchantStats.active_merchants}</p></div>
                <div className="card stat-card"><h3>Last Hour</h3><p className="stat-value">{merchantStats.last_hour}</p></div>
                <div className="card stat-card"><h3>Last 24h</h3><p className="stat-value">{merchantStats.last_24h}</p></div>
              </div>

              {merchantStats.daily_signups && merchantStats.daily_signups.length > 0 && (
                <div>
                  <h2>Daily Signups (Last 7 Days)</h2>
                  <div className="card">
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '120px', padding: '0.5rem 0' }}>
                      {merchantStats.daily_signups.map((d: any) => {
                        const max = Math.max(...merchantStats.daily_signups.map((x: any) => x.count), 1);
                        const height = (d.count / max) * 100;
                        return (
                          <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                            <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>{d.count}</span>
                            <div style={{ width: '100%', background: '#4f46e5', borderRadius: '4px 4px 0 0', height: `${Math.max(height, 5)}%`, transition: 'height 0.5s' }} />
                            <span style={{ fontSize: '0.65rem', color: '#64748b' }}>{d.date.slice(5)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <h2 style={{ marginTop: '2rem' }}>All Merchants</h2>
          {merchants.length === 0 ? <p style={{ color: '#64748b' }}>No merchants registered.</p> : (
            <table>
              <thead><tr><th>Business</th><th>Email</th><th>Status</th><th>Joined</th></tr></thead>
              <tbody>
                {merchants.map((m: any) => (
                  <tr key={m.id}>
                    <td style={{ fontWeight: 600 }}>{m.business_name}</td>
                    <td>{m.email}</td>
                    <td><span className={`status-badge ${m.status.toLowerCase() === 'active' ? 'success' : 'pending'}`}>{m.status}</span></td>
                    <td style={{ fontSize: '0.85rem', color: '#64748b' }}>{new Date(m.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* SERVICES TAB */}
      {tab === 'services' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Service Health</h2>
            <button onClick={loadHealth} className="btn-small">↻ Check Now</button>
          </div>
          <div className="info-box">
            <strong>ℹ️ Service Health Monitoring</strong>
            <p>Shows real-time health status of all microservices. Green = healthy, Red = unreachable. Latency shows response time of health check endpoint.</p>
          </div>

          {serviceHealth ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              {Object.entries(serviceHealth.services || {}).map(([name, svc]: [string, any]) => (
                <div key={name} className="card" style={{ borderLeft: `4px solid ${svc.status === 'healthy' ? '#10b981' : svc.status === 'unhealthy' ? '#f59e0b' : '#ef4444'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ textTransform: 'capitalize', margin: 0 }}>{name}</h3>
                    <span className={`status-badge ${svc.status === 'healthy' ? 'success' : 'failed'}`}>{svc.status}</span>
                  </div>
                  {svc.latency_ms != null && (
                    <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.5rem' }}>
                      Latency: <strong>{svc.latency_ms.toFixed(0)}ms</strong>
                    </p>
                  )}
                  <div style={{ marginTop: '0.5rem', background: '#e2e8f0', borderRadius: '4px', height: '4px' }}>
                    <div style={{ background: svc.status === 'healthy' ? '#10b981' : '#ef4444', borderRadius: '4px', height: '4px', width: svc.status === 'healthy' ? '100%' : '30%' }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#64748b' }}>Click "Check Now" to test service health.</p>
          )}

          <div style={{ marginTop: '2rem' }}>
            <h2>Architecture</h2>
            <div className="card" style={{ fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre', overflowX: 'auto', lineHeight: '1.8' }}>
{`┌─────────────────────────────────────────────┐
│           CloudFront (Frontend)              │
└──────────────────┬──────────────────────────┘
                   │ /api/*
                   ▼
┌─────────────────────────────────────────────┐
│         Payment Service (8001)              │
│              Orchestrator                    │
└───────┬──────────┬──────────┬───────────────┘
        │          │          │
        ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Fraud   │ │ Routing  │ │ Merchant │
│  (8004)  │ │  (8003)  │ │  (8002)  │
└──────────┘ └──────────┘ └──────────┘
                                    
┌─────────────────────────────────────────────┐
│         Analytics Service (8005)            │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           RDS PostgreSQL                    │
└─────────────────────────────────────────────┘`}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
