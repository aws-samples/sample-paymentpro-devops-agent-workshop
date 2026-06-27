import React, { createContext, useContext, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import './index.css';
import { CheckoutPage } from './pages/CheckoutPage';
import { MerchantPortal } from './pages/MerchantPortal';
import { Dashboard } from './pages/Dashboard';

// Auth context for persistent session across pages
interface AuthState {
  sessionId: string | null;
  merchantId: string | null;
  merchantName: string | null;
}

interface AuthContextType {
  auth: AuthState;
  login: (sessionId: string, merchantId: string, merchantName: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType>({
  auth: { sessionId: null, merchantId: null, merchantName: null },
  login: () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(() => {
    const stored = localStorage.getItem('merchant_session');
    return stored ? JSON.parse(stored) : { sessionId: null, merchantId: null, merchantName: null };
  });

  const login = (sessionId: string, merchantId: string, merchantName: string) => {
    const state = { sessionId, merchantId, merchantName };
    setAuth(state);
    localStorage.setItem('merchant_session', JSON.stringify(state));
  };

  const logout = () => {
    setAuth({ sessionId: null, merchantId: null, merchantName: null });
    localStorage.removeItem('merchant_session');
  };

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function NavBar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <nav>
      <Link to="/" className={location.pathname === '/' ? 'active' : ''} data-testid="nav-home">
        💳 PaymentPro
      </Link>
      <Link to="/checkout/demo" className={isActive('/checkout') ? 'active' : ''} data-testid="nav-checkout">
        Payment Gateway
      </Link>
      <Link to="/merchant" className={isActive('/merchant') ? 'active' : ''} data-testid="nav-merchant">
        Merchant Portal
      </Link>
      <Link to="/admin/dashboard" className={isActive('/admin') ? 'active' : ''} data-testid="nav-dashboard">
        Admin Dashboard
      </Link>
    </nav>
  );
}

function Home() {
  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>💳 PaymentPro Platform</h1>
        <p style={{ color: '#64748b', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto' }}>
          A microservices-based payment gateway supporting UPI, Credit/Debit Cards, and Digital Wallets.
        </p>
      </div>

      {/* Quick Links */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
        <div className="card">
          <h3>💳 Payment Gateway</h3>
          <p style={{ color: '#64748b', margin: '0.5rem 0 1rem' }}>Embeddable checkout — process payments for any merchant</p>
          <Link to="/checkout/demo">Open Gateway →</Link>
        </div>
        <div className="card">
          <h3>🏪 Merchant Portal</h3>
          <p style={{ color: '#64748b', margin: '0.5rem 0 1rem' }}>Register, manage API keys, view analytics & transactions</p>
          <Link to="/merchant">Go to Portal →</Link>
        </div>
        <div className="card">
          <h3>📊 Admin Dashboard</h3>
          <p style={{ color: '#64748b', margin: '0.5rem 0 1rem' }}>Platform-wide analytics, merchant stats, service health</p>
          <Link to="/admin/dashboard">Go to Dashboard →</Link>
        </div>
      </div>

      {/* How It Works */}
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>How Payments Work</h2>
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', textAlign: 'center', padding: '1rem 0' }}>
          <div><div style={{ fontSize: '2rem' }}>🛒</div><p style={{ fontSize: '0.8rem', fontWeight: 600 }}>1. Customer</p><p style={{ fontSize: '0.75rem', color: '#64748b' }}>Selects payment method</p></div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', color: '#4f46e5' }}>→</div>
          <div><div style={{ fontSize: '2rem' }}>🔒</div><p style={{ fontSize: '0.8rem', fontWeight: 600 }}>2. Validate</p><p style={{ fontSize: '0.75rem', color: '#64748b' }}>Fraud checks & input validation</p></div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', color: '#4f46e5' }}>→</div>
          <div><div style={{ fontSize: '2rem' }}>✅</div><p style={{ fontSize: '0.8rem', fontWeight: 600 }}>3. Process</p><p style={{ fontSize: '0.75rem', color: '#64748b' }}>Route & settle payment</p></div>
        </div>
      </div>

      {/* Architecture */}
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>System Architecture</h2>
      <div className="card" style={{ fontFamily: 'monospace', fontSize: '0.75rem', whiteSpace: 'pre', overflowX: 'auto', lineHeight: '1.6', padding: '1.5rem', marginBottom: '2rem' }}>
{`                    ┌──────────────────────┐
                    │   CloudFront (CDN)   │
                    │   + React Frontend   │
                    └──────────┬───────────┘
                               │ /api/*
                               ▼
                    ┌──────────────────────┐
                    │   Payment Service    │◄── Orchestrator
                    │      (FastAPI)       │    Processes payments
                    └───┬──────┬──────┬───┘
                        │      │      │
              ┌─────────┘      │      └─────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    Fraud     │  │   Routing    │  │  Merchant    │
    │   Service    │  │   Service    │  │   Service    │
    │  (Validate)  │  │ (Rule Engine)│  │  (Auth/Keys) │
    └──────────────┘  └──────────────┘  └──────────────┘
                               │
                    ┌──────────────────────┐
                    │  Analytics Service   │◄── Read-only
                    │  (Dashboard Metrics) │    queries
                    └──────────┬───────────┘
                               │
                    ┌──────────────────────┐
                    │   RDS PostgreSQL     │◄── Persistent
                    │   (Shared Database)  │    storage
                    └──────────────────────┘`}
      </div>

      {/* Tech Stack */}
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Technology Stack</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ textAlign: 'center' }}><h3>Backend</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>Python 3.12 • FastAPI • SQLAlchemy • Pydantic</p></div>
        <div className="card" style={{ textAlign: 'center' }}><h3>Frontend</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>React 18 • TypeScript • Vite • CSS</p></div>
        <div className="card" style={{ textAlign: 'center' }}><h3>Database</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>PostgreSQL 15 • RDS • Auto-scaling storage</p></div>
        <div className="card" style={{ textAlign: 'center' }}><h3>Infrastructure</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>AWS CDK • ECS Fargate • CloudFront • ALB</p></div>
        <div className="card" style={{ textAlign: 'center' }}><h3>Security</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>Service auth • bcrypt • Secrets Manager</p></div>
        <div className="card" style={{ textAlign: 'center' }}><h3>Observability</h3><p style={{ color: '#64748b', fontSize: '0.85rem' }}>structlog • CloudWatch • Health checks</p></div>
      </div>

      {/* Features */}
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Key Features</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card"><strong>🔐 Fraud Detection</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>Luhn validation, card expiry checks, UPI format verification, wallet balance validation</p></div>
        <div className="card"><strong>🔀 Smart Routing</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>Priority-based rule engine routes payments to optimal providers per merchant</p></div>
        <div className="card"><strong>📊 Real-time Analytics</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>Transaction volume, success rates, payment distribution, merchant performance</p></div>
        <div className="card"><strong>🔑 API Key Management</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>Generate, rotate, and revoke API keys for programmatic payment processing</p></div>
        <div className="card"><strong>⚡ Auto-scaling</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>ECS Fargate scales 1-3 instances per service based on CPU utilization</p></div>
        <div className="card"><strong>🏗️ Microservices</strong><p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>5 independent services — deploy, scale, and update each independently</p></div>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/checkout/:merchantId" element={<CheckoutPage />} />
            <Route path="/merchant" element={<MerchantPortal />} />
            <Route path="/admin/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
