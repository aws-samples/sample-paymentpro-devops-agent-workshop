import { useState, useEffect } from 'react';
import type { LoginResponse, ApiKey } from '../types';
import { api } from '../api/client';
import { useAuth } from '../main';

type Tab = 'overview' | 'analytics' | 'apikeys' | 'transactions' | 'profile';

export function MerchantPortal() {
  const { auth, login, logout: authLogout } = useAuth();
  const [view, setView] = useState<'login' | 'register' | 'dashboard'>(auth.sessionId ? 'dashboard' : 'login');
  const [tab, setTab] = useState<Tab>('overview');
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copiedKey, setCopiedKey] = useState('');
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

  // Login form
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Register form
  const [businessName, setBusinessName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [contact, setContact] = useState('');

  // Load data when logged in
  useEffect(() => {
    if (auth.merchantId) {
      setView('dashboard');
      loadProfile();
      loadApiKeys();
      loadTransactions();
    }
  }, [auth.merchantId]);

  const loadProfile = async () => {
    if (!auth.merchantId) return;
    try {
      const data = await api.getMerchant(auth.merchantId);
      setProfile(data);
    } catch {}
  };

  const loadApiKeys = async () => {
    if (!auth.merchantId) return;
    try {
      const data = await api.listApiKeys(auth.merchantId) as ApiKey[];
      setApiKeys(data);
    } catch {}
  };

  const loadTransactions = async () => {
    if (!auth.merchantId) return;
    try {
      const data = await api.listTransactions(`merchant_id=${auth.merchantId}&limit=20`) as any;
      setTransactions(data.items || []);
    } catch {}
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const resp = await api.login({ email, password }) as LoginResponse;
      login(resp.session_id, resp.merchant_id, email.split('@')[0]);
      setView('dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.register({ business_name: businessName, email: regEmail, password: regPassword, contact: contact || undefined });
      setSuccess('Registration successful! Please login.');
      setView('login');
      setEmail(regEmail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  const handleGenerateKey = async () => {
    if (!auth.merchantId) return;
    setError('');
    try {
      const key = await api.generateApiKey(auth.merchantId) as ApiKey;
      setApiKeys([...apiKeys, key]);
      setSuccess('API key generated!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate key');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!auth.merchantId) return;
    try {
      await api.revokeApiKey(auth.merchantId, keyId);
      setApiKeys(apiKeys.filter(k => k.id !== keyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke key');
    }
  };

  const handleCopyKey = (keyValue: string) => {
    navigator.clipboard.writeText(keyValue);
    setCopiedKey(keyValue);
    setTimeout(() => setCopiedKey(''), 2000);
  };

  const handleLogout = () => {
    if (auth.sessionId) api.logout(auth.sessionId).catch(() => {});
    authLogout();
    setView('login');
    setApiKeys([]);
    setTransactions([]);
    setProfile(null);
  };

  // Register view
  if (view === 'register') {
    return (
      <div style={{ maxWidth: '450px', margin: '0 auto' }}>
        <h1>Create Merchant Account</h1>
        <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>Register your business to start accepting payments.</p>
        {error && <div className="result-box error">{error}</div>}
        <form onSubmit={handleRegister}>
          <div className="form-group"><label>Business Name</label><input data-testid="register-business-name" placeholder="Your Business Name" value={businessName} onChange={e => setBusinessName(e.target.value)} required /></div>
          <div className="form-group"><label>Email</label><input data-testid="register-email" placeholder="you@business.com" type="email" value={regEmail} onChange={e => setRegEmail(e.target.value)} required /></div>
          <div className="form-group"><label>Password</label><input data-testid="register-password" placeholder="Min 8 characters" type="password" value={regPassword} onChange={e => setRegPassword(e.target.value)} required minLength={8} /></div>
          <div className="form-group"><label>Contact (optional)</label><input data-testid="register-contact" placeholder="+91-9876543210" value={contact} onChange={e => setContact(e.target.value)} /></div>
          <button type="submit" style={{ marginTop: '1.5rem' }}>Create Account</button>
          <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
            <button type="button" onClick={() => { setView('login'); setError(''); }} className="link-button">Already have an account? Login →</button>
          </div>
        </form>
      </div>
    );
  }

  // Dashboard view
  if (view === 'dashboard' && auth.merchantId) {
    return (
      <div>
        {/* Header with profile */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h1>🏪 Merchant Portal</h1>
          <div style={{ position: 'relative' }}>
            <button onClick={() => setShowProfileDropdown(!showProfileDropdown)} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              👤 {auth.merchantName} ▾
            </button>
            {showProfileDropdown && (
              <div style={{ position: 'absolute', right: 0, top: '100%', marginTop: '0.5rem', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', padding: '0.5rem', minWidth: '200px', zIndex: 50 }}>
                <button onClick={() => { setTab('profile'); setShowProfileDropdown(false); }} style={{ width: '100%', textAlign: 'left', background: 'none', color: '#1e293b', padding: '0.5rem 0.75rem', borderRadius: '4px' }}>👤 My Profile</button>
                <button onClick={() => { setTab('apikeys'); setShowProfileDropdown(false); }} style={{ width: '100%', textAlign: 'left', background: 'none', color: '#1e293b', padding: '0.5rem 0.75rem', borderRadius: '4px' }}>🔑 API Keys</button>
                <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid #e2e8f0' }} />
                <button onClick={handleLogout} style={{ width: '100%', textAlign: 'left', background: 'none', color: '#ef4444', padding: '0.5rem 0.75rem', borderRadius: '4px' }}>🚪 Logout</button>
              </div>
            )}
          </div>
        </div>

        {error && <div className="result-box error">{error}</div>}
        {success && <div className="result-box success">{success}</div>}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
          {(['overview', 'analytics', 'transactions', 'apikeys', 'profile'] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#eef2ff' : 'transparent', color: tab === t ? '#4f46e5' : '#64748b', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', fontWeight: tab === t ? 600 : 400, cursor: 'pointer' }}>
              {t === 'overview' && '📊 Overview'}
              {t === 'analytics' && '📈 Analytics'}
              {t === 'transactions' && '💰 Transactions'}
              {t === 'apikeys' && '🔑 API Keys'}
              {t === 'profile' && '👤 Profile'}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {tab === 'overview' && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
              <div className="card stat-card"><h3>Transactions</h3><p className="stat-value">{transactions.length}</p></div>
              <div className="card stat-card"><h3>Successful</h3><p className="stat-value" style={{ color: '#10b981' }}>{transactions.filter((t: any) => t.status === 'SUCCESS').length}</p></div>
              <div className="card stat-card"><h3>Revenue</h3><p className="stat-value">₹{transactions.filter((t: any) => t.status === 'SUCCESS').reduce((s: number, t: any) => s + parseFloat(t.amount), 0).toFixed(0)}</p></div>
              <div className="card stat-card"><h3>API Keys</h3><p className="stat-value">{apiKeys.length}</p></div>
            </div>
            <h2>Recent Transactions</h2>
            {transactions.length === 0 ? <p style={{ color: '#64748b' }}>No transactions yet.</p> : (
              <table>
                <thead><tr><th>Status</th><th>Amount</th><th>Type</th><th>Time</th></tr></thead>
                <tbody>
                  {transactions.slice(0, 5).map((txn: any) => (
                    <tr key={txn.id}>
                      <td><span className={`status-badge ${txn.status.toLowerCase()}`}>{txn.status}</span></td>
                      <td style={{ fontWeight: 600 }}>₹{txn.amount}</td>
                      <td>{txn.payment_type}</td>
                      <td style={{ fontSize: '0.85rem', color: '#64748b' }}>{new Date(txn.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Analytics Tab */}
        {tab === 'analytics' && <MerchantAnalytics merchantId={auth.merchantId!} />}

        {/* Transactions Tab */}
        {tab === 'transactions' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>All Transactions</h2>
              <button onClick={loadTransactions} className="btn-small">↻ Refresh</button>
            </div>
            {transactions.length === 0 ? <p style={{ color: '#64748b' }}>No transactions yet.</p> : (
              <table>
                <thead><tr><th>Status</th><th>Amount</th><th>Type</th><th>Route</th><th>Time</th></tr></thead>
                <tbody>
                  {transactions.map((txn: any) => (
                    <tr key={txn.id}>
                      <td><span className={`status-badge ${txn.status.toLowerCase()}`}>{txn.status}</span></td>
                      <td style={{ fontWeight: 600 }}>₹{txn.amount}</td>
                      <td>{txn.payment_type}</td>
                      <td><code>{txn.route_target || '—'}</code></td>
                      <td style={{ fontSize: '0.85rem', color: '#64748b' }}>{new Date(txn.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* API Keys Tab */}
        {tab === 'apikeys' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>API Keys</h2>
              <button onClick={handleGenerateKey} className="btn-small">+ Generate New Key</button>
            </div>
            <div className="info-box">
              <strong>ℹ️ What are API Keys?</strong>
              <p>API keys let your application process payments programmatically — like how Stripe or Razorpay work. Your backend server includes the key in the <code>X-API-Key</code> header when calling our Payment API. This authenticates your requests without exposing your login credentials.</p>
            </div>
            {apiKeys.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                <p style={{ color: '#64748b' }}>No API keys yet.</p>
                <button onClick={handleGenerateKey} style={{ marginTop: '1rem' }}>Generate Your First Key</button>
              </div>
            ) : (
              <>
                <div className="transaction-list">
                  {apiKeys.map(key => (
                    <div key={key.id} className="transaction-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <code style={{ fontSize: '0.85rem', wordBreak: 'break-all' }}>{key.key_value}</code>
                          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>{key.label} • Created {new Date(key.created_at).toLocaleDateString()}</div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0, marginLeft: '1rem' }}>
                          <button onClick={() => handleCopyKey(key.key_value)} className="btn-tiny">{copiedKey === key.key_value ? '✓ Copied' : '📋 Copy'}</button>
                          <button onClick={() => handleRevokeKey(key.id)} className="btn-tiny btn-danger">🗑 Revoke</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Try API Section */}
                <div style={{ marginTop: '2rem' }}>
                  <h3>🧪 Try Your API Key</h3>
                  <p style={{ color: '#64748b', marginBottom: '0.75rem' }}>Copy this curl command to process a payment from your terminal:</p>
                  <div style={{ background: '#1e293b', color: '#e2e8f0', padding: '1rem', borderRadius: '8px', fontSize: '0.8rem', fontFamily: 'monospace', overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
{`curl -X POST ${window.location.origin}/api/v1/payments \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${apiKeys[0].key_value}" \\
  -d '{
    "payment_type": "UPI",
    "amount": "100.00",
    "merchant_id": "${auth.merchantId}",
    "upi_id": "customer@paytm"
  }'`}
                  </div>
                  <button onClick={() => { navigator.clipboard.writeText(`curl -X POST ${window.location.origin}/api/v1/payments -H "Content-Type: application/json" -H "X-API-Key: ${apiKeys[0].key_value}" -d '{"payment_type":"UPI","amount":"100.00","merchant_id":"${auth.merchantId}","upi_id":"customer@paytm"}'`); setSuccess('Curl command copied!'); setTimeout(() => setSuccess(''), 2000); }} className="btn-small" style={{ marginTop: '0.75rem' }}>📋 Copy Command</button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Profile Tab */}
        {tab === 'profile' && (
          <div style={{ maxWidth: '500px' }}>
            <h2>Merchant Profile</h2>
            {profile ? (
              <div className="card">
                <div className="form-group"><label>Business Name</label><input value={profile.business_name} readOnly style={{ background: '#f8fafc' }} /></div>
                <div className="form-group"><label>Email</label><input value={profile.email} readOnly style={{ background: '#f8fafc' }} /></div>
                <div className="form-group"><label>Contact</label><input value={profile.contact || 'Not provided'} readOnly style={{ background: '#f8fafc' }} /></div>
                <div className="form-group"><label>Status</label><input value={profile.status} readOnly style={{ background: '#f8fafc' }} /></div>
                <div className="form-group"><label>Merchant ID</label><input value={profile.id} readOnly style={{ background: '#f8fafc', fontFamily: 'monospace', fontSize: '0.85rem' }} /></div>
                <div className="form-group"><label>Member Since</label><input value={new Date(profile.created_at).toLocaleDateString()} readOnly style={{ background: '#f8fafc' }} /></div>
              </div>
            ) : (
              <p style={{ color: '#64748b' }}>Loading profile...</p>
            )}
            <div style={{ marginTop: '2rem' }}>
              <h2>Security</h2>
              <div className="card">
                <p style={{ color: '#64748b', marginBottom: '1rem' }}>Change your password to keep your account secure.</p>
                <div className="form-group"><label>Current Password</label><input type="password" placeholder="Enter current password" /></div>
                <div className="form-group"><label>New Password</label><input type="password" placeholder="Enter new password (min 8 chars)" /></div>
                <div className="form-group"><label>Confirm New Password</label><input type="password" placeholder="Confirm new password" /></div>
                <button className="btn-secondary" style={{ marginTop: '0.5rem' }}>Update Password</button>
                <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>Note: Password change is not yet implemented in the backend.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Login view
  return (
    <div style={{ maxWidth: '450px', margin: '0 auto' }}>
      <h1>Merchant Login</h1>
      <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>Sign in to manage your payments and API keys.</p>
      {error && <div className="result-box error">{error}</div>}
      {success && <div className="result-box success">{success}</div>}
      <form onSubmit={handleLogin}>
        <div className="form-group"><label>Email</label><input data-testid="login-email" placeholder="you@business.com" type="email" value={email} onChange={e => setEmail(e.target.value)} required /></div>
        <div className="form-group"><label>Password</label><input data-testid="login-password" placeholder="Your password" type="password" value={password} onChange={e => setPassword(e.target.value)} required /></div>
        <button type="submit" style={{ marginTop: '1.5rem' }}>Login</button>
        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <button type="button" onClick={() => { setView('register'); setError(''); setSuccess(''); }} className="link-button">New merchant? Create an account →</button>
        </div>
      </form>
    </div>
  );
}

// Merchant Analytics sub-component
function MerchantAnalytics({ merchantId }: { merchantId: string }) {
  const [summary, setSummary] = useState<any>(null);
  const [rates, setRates] = useState<any>(null);
  const [distribution, setDistribution] = useState<any[]>([]);
  const [volume, setVolume] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [merchantId]);

  const loadAnalytics = async () => {
    setLoading(true);
    const params = `merchant_id=${merchantId}`;
    try {
      const [s, r, d, v] = await Promise.all([
        api.getSummary(params),
        api.getSuccessRates(params),
        api.getDistribution(params) as Promise<any>,
        api.getVolume(params) as Promise<any>,
      ]);
      setSummary(s); setRates(r); setDistribution(d.data || []); setVolume(v);
    } catch {}
    setLoading(false);
  };

  if (loading) return <p style={{ color: '#64748b', padding: '2rem 0' }}>Loading analytics...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Your Performance</h2>
        <button onClick={loadAnalytics} className="btn-small">↻ Refresh</button>
      </div>

      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
          <div className="card stat-card"><h3>Transactions</h3><p className="stat-value">{(summary as any).total_transactions}</p></div>
          <div className="card stat-card"><h3>Success Rate</h3><p className="stat-value" style={{ color: '#10b981' }}>{(summary as any).success_rate}%</p></div>
          <div className="card stat-card"><h3>Volume</h3><p className="stat-value">₹{Number((summary as any).total_volume).toLocaleString()}</p></div>
          <div className="card stat-card"><h3>Methods Used</h3><p className="stat-value">{(summary as any).payment_types}</p></div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {rates && (
          <div>
            <h3>Success vs Failure</h3>
            <div className="card">
              <div className="rate-bar">
                <div className="rate-segment success" style={{ width: `${(rates as any).total > 0 ? ((rates as any).success_count / (rates as any).total * 100) : 0}%` }}>
                  {(rates as any).success_count > 0 && `✅ ${(rates as any).success_count}`}
                </div>
                <div className="rate-segment failed" style={{ width: `${(rates as any).total > 0 ? ((rates as any).failure_count / (rates as any).total * 100) : 0}%` }}>
                  {(rates as any).failure_count > 0 && `❌ ${(rates as any).failure_count}`}
                </div>
              </div>
            </div>
          </div>
        )}

        {distribution.length > 0 && (
          <div>
            <h3>Payment Method Mix</h3>
            <div className="card">
              {distribution.map((item: any) => (
                <div key={item.payment_type} style={{ marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>{item.payment_type}</span><span>{item.percentage}%</span>
                  </div>
                  <div style={{ background: '#e2e8f0', borderRadius: '4px', height: '6px', marginTop: '2px' }}>
                    <div style={{ background: '#4f46e5', borderRadius: '4px', height: '6px', width: `${item.percentage}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {volume && (volume as any).data && (volume as any).data.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Transaction Volume (Daily)</h3>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '100px' }}>
              {(volume as any).data.map((d: any) => {
                const max = Math.max(...(volume as any).data.map((x: any) => x.count), 1);
                return (
                  <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>{d.count}</span>
                    <div style={{ width: '100%', background: '#4f46e5', borderRadius: '3px 3px 0 0', height: `${Math.max((d.count / max) * 100, 5)}%` }} />
                    <span style={{ fontSize: '0.6rem', color: '#64748b' }}>{d.date.slice(5)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
