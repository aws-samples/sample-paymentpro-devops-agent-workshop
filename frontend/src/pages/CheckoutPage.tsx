import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import type { PaymentType, PaymentResponse } from '../types';
import { api } from '../api/client';

interface RecentPayment {
  amount: string;
  paymentType: PaymentType;
  merchantId: string;
  timestamp: number;
}

export function CheckoutPage() {
  const { merchantId: urlMerchantId } = useParams<{ merchantId: string }>();
  const [selectedMerchant, setSelectedMerchant] = useState(urlMerchantId || 'demo');
  const [merchants, setMerchants] = useState<any[]>([]);
  const [paymentType, setPaymentType] = useState<PaymentType>('CREDIT_CARD');
  const [amount, setAmount] = useState('100.00');
  const [cardNumber, setCardNumber] = useState('4111111111111111');
  const [cardExpiry, setCardExpiry] = useState('12/30');
  const [cvv, setCvv] = useState('123');
  const [upiId, setUpiId] = useState('user@paytm');
  const [walletId, setWalletId] = useState('wallet12345678');
  const [walletBalance, setWalletBalance] = useState('5000.00');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PaymentResponse | null>(null);
  const [error, setError] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState('');
  const [recentPayments, setRecentPayments] = useState<RecentPayment[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);

  // Clear result when payment type changes
  useEffect(() => {
    setResult(null);
    setError('');
    setDuplicateWarning('');
  }, [paymentType]);

  // Load merchants from DB
  useEffect(() => {
    api.listMerchants()
      .then((data: any) => setMerchants(data || []))
      .catch(() => {});
  }, []);

  // Load recent transactions
  useEffect(() => {
    if (selectedMerchant && selectedMerchant !== 'demo') {
      api.listTransactions(`merchant_id=${selectedMerchant}&limit=5`)
        .then((data: any) => setTransactions(data.items || []))
        .catch(() => {});
    }
  }, [selectedMerchant, result]);

  const checkDuplicate = (): boolean => {
    const now = Date.now();
    const fiveMinAgo = now - 5 * 60 * 1000;
    const duplicate = recentPayments.find(
      p => p.amount === amount && p.paymentType === paymentType && p.merchantId === selectedMerchant && p.timestamp > fiveMinAgo
    );
    if (duplicate) {
      setDuplicateWarning(`⚠️ A similar payment (₹${amount} via ${paymentType}) was made ${Math.round((now - duplicate.timestamp) / 1000)}s ago. Are you sure?`);
      return true;
    }
    return false;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check for duplicate (show warning but allow proceed)
    if (!duplicateWarning && checkDuplicate()) {
      return; // Show warning first, user submits again to confirm
    }

    setLoading(true);
    setError('');
    setResult(null);
    setDuplicateWarning('');

    try {
      const payload: Record<string, string | undefined> = {
        payment_type: paymentType,
        amount,
        currency: 'INR',
        merchant_id: selectedMerchant,
      };

      if (paymentType === 'CREDIT_CARD' || paymentType === 'DEBIT_CARD') {
        payload.card_number = cardNumber;
        payload.card_expiry = cardExpiry;
        payload.cvv = cvv;
      } else if (paymentType === 'UPI') {
        payload.upi_id = upiId;
      } else if (paymentType === 'WALLET') {
        payload.wallet_id = walletId;
        payload.wallet_balance = walletBalance;
      }

      const response = await api.createPayment(payload) as PaymentResponse;
      setResult(response);
      setRecentPayments([...recentPayments, { amount, paymentType, merchantId: selectedMerchant, timestamp: Date.now() }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', maxWidth: '900px' }}>
      <div>
        <h1>Payment Gateway</h1>
        <p className="info-text">ℹ️ This is a demo of the embeddable payment page that merchants integrate into their websites. Customers use this to pay.</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="merchant">Merchant <span className="tooltip" title="The business receiving the payment. In production, this is set automatically based on whose checkout page the customer is on.">ℹ️</span></label>
            <select id="merchant" data-testid="checkout-merchant" value={selectedMerchant} onChange={(e) => setSelectedMerchant(e.target.value)}>
              <option value="demo">Demo Merchant</option>
              {merchants.map((m: any) => (
                <option key={m.id} value={m.id}>{m.business_name} ({m.email})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="payment-type">Payment Method</label>
            <select id="payment-type" data-testid="checkout-payment-type" value={paymentType} onChange={(e) => setPaymentType(e.target.value as PaymentType)}>
              <option value="CREDIT_CARD">💳 Credit Card</option>
              <option value="DEBIT_CARD">💳 Debit Card</option>
              <option value="UPI">📱 UPI</option>
              <option value="WALLET">👛 Wallet</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="amount">Amount (₹)</label>
            <input id="amount" data-testid="checkout-amount" type="text" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>

          {(paymentType === 'CREDIT_CARD' || paymentType === 'DEBIT_CARD') && (
            <>
              <div className="form-group">
                <label htmlFor="card-number">Card Number</label>
                <input id="card-number" data-testid="checkout-card-number" type="text" value={cardNumber} onChange={(e) => setCardNumber(e.target.value)} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label htmlFor="card-expiry">Expiry (MM/YY)</label>
                  <input id="card-expiry" data-testid="checkout-card-expiry" type="text" value={cardExpiry} onChange={(e) => setCardExpiry(e.target.value)} />
                </div>
                <div className="form-group">
                  <label htmlFor="cvv">CVV</label>
                  <input id="cvv" data-testid="checkout-cvv" type="password" value={cvv} onChange={(e) => setCvv(e.target.value)} />
                </div>
              </div>
            </>
          )}

          {paymentType === 'UPI' && (
            <div className="form-group">
              <label htmlFor="upi-id">UPI ID</label>
              <input id="upi-id" data-testid="checkout-upi-id" type="text" value={upiId} onChange={(e) => setUpiId(e.target.value)} placeholder="user@paytm" />
            </div>
          )}

          {paymentType === 'WALLET' && (
            <>
              <div className="form-group">
                <label htmlFor="wallet-id">Wallet ID</label>
                <input id="wallet-id" data-testid="checkout-wallet-id" type="text" value={walletId} onChange={(e) => setWalletId(e.target.value)} />
              </div>
              <div className="form-group">
                <label htmlFor="wallet-balance">Wallet Balance (₹)</label>
                <input id="wallet-balance" data-testid="checkout-wallet-balance" type="text" value={walletBalance} onChange={(e) => setWalletBalance(e.target.value)} />
              </div>
            </>
          )}

          {duplicateWarning && (
            <div className="warning-box" data-testid="checkout-duplicate-warning">
              {duplicateWarning}
              <br /><small>Click "Pay" again to confirm.</small>
            </div>
          )}

          <button type="submit" data-testid="checkout-submit-button" disabled={loading} style={{ marginTop: '1.5rem' }}>
            {loading ? '⏳ Processing...' : `Pay ₹${amount}`}
          </button>
        </form>

        {result && (
          <div className={`result-box ${result.status === 'SUCCESS' ? 'success' : 'error'}`} data-testid="checkout-result">
            <strong>{result.status === 'SUCCESS' ? '✅' : '❌'} {result.status}</strong>
            <p>{result.message}</p>
            <p style={{ fontSize: '0.85rem', color: '#64748b' }}>
              Transaction: {result.transaction_id}<br />
              {result.route_target && `Route: ${result.route_target}`}
            </p>
          </div>
        )}

        {error && <div className="result-box error" data-testid="checkout-error">{error}</div>}
      </div>

      <div>
        <h2>Recent Transactions</h2>
        {transactions.length === 0 ? (
          <p style={{ color: '#64748b' }}>No transactions yet. Make a payment to see history.</p>
        ) : (
          <div className="transaction-list">
            {transactions.map((txn: any) => (
              <div key={txn.id} className="transaction-item">
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className={`status-badge ${txn.status.toLowerCase()}`}>{txn.status}</span>
                  <span style={{ fontWeight: 600 }}>₹{txn.amount}</span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
                  {txn.payment_type} • {new Date(txn.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
