/** Shared TypeScript types for the frontend. */

export type PaymentType = 'UPI' | 'CREDIT_CARD' | 'DEBIT_CARD' | 'WALLET';
export type TransactionStatus = 'PENDING' | 'SUCCESS' | 'FAILED';

export interface PaymentRequest {
  payment_type: PaymentType;
  amount: string;
  currency: string;
  merchant_id: string;
  card_number?: string;
  card_expiry?: string;
  cvv?: string;
  upi_id?: string;
  wallet_id?: string;
  wallet_balance?: string;
}

export interface PaymentResponse {
  transaction_id: string;
  status: TransactionStatus;
  message: string;
  route_target?: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  merchant_id: string;
  payment_type: PaymentType;
  amount: string;
  currency: string;
  status: TransactionStatus;
  route_target?: string;
  failure_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface MerchantProfile {
  id: string;
  business_name: string;
  email: string;
  contact?: string;
  status: string;
  created_at: string;
}

export interface LoginResponse {
  session_id: string;
  merchant_id: string;
  expires_at: string;
}

export interface ApiKey {
  id: string;
  merchant_id: string;
  key_value: string;
  label: string;
  status: string;
  created_at: string;
}

export interface DashboardSummary {
  total_transactions: number;
  success_rate: number;
  total_volume: string;
  payment_types: number;
}

export interface SuccessRateData {
  success_count: number;
  failure_count: number;
  pending_count: number;
  total: number;
  success_rate: number;
}

export interface PaymentDistributionItem {
  payment_type: string;
  count: number;
  percentage: number;
}
