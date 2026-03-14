// src/types/index.ts — AGGIORNATO
// FIX: aggiunto 'basic' al tipo Plan (mancava → crash su PlanBadge e checkout)

export type Lang = 'it' | 'en' | 'fr' | 'de' | 'es' | 'pt';
export type Plan = 'free' | 'basic' | 'pro' | 'plus';   // ← 'basic' aggiunto
export type BillingCycle = 'monthly' | 'annual';
export type View =
  | 'landing'
  | 'login'
  | 'register'
  | 'pricing'
  | 'dashboard'
  | 'deepresearch'
  | 'calcola'
  | 'reports'
  | 'history'
  | 'storage'
  | 'payment-success';

export type AuthMode = 'login' | 'register';

export type SidebarItem = {
  id: View;
  labelKey: string;
  icon: string;
  planRequired: Plan | null;
};

export type RenovationLevel = 'conservativo' | 'moderato' | 'premium';

// ─── Auth ───
export interface User {
  id: number;
  email: string;
  name: string;
  plan: Plan;
  deepresearch_count: number;
  calcola_count: number;
  created_at: string;
  storage_used_bytes?: number;
  trial_ends_at?: string | null;
  stripe_subscription_id?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

// ─── Billing ───
export interface PlanPrice {
  monthly: number;
  annual: number;
}

export interface PaymentPayload {
  plan: Plan;
  billing_cycle: BillingCycle;
  card_number: string;
  card_expiry: string;
  card_cvc: string;
  cardholder_name: string;
}

// ─── API Requests ───
export interface RegisterPayload {
  email: string;
  name: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface PropertyInput {
  address: string;
  price: number;
  size_sqm: number;
  rooms: number;
  floor?: number;
  year_built?: number;
  condition?: string;
  notes?: string;
}

export interface DeepResearchRequest {
  query: string;
  properties: PropertyInput[];
}

export interface PropertyCalculationInput {
  purchase_price: number;
  size_sqm: number;
  location: string;
  current_rent?: number;
  target_rent?: number;
  renovation_budget?: number;
  mortgage_rate?: number;
  mortgage_years?: number;
  down_payment_pct?: number;
}

// ─── API Responses ───
export interface PropertyAnalysis {
  address: string;
  estimated_value?: number;
  market_score?: number;
  recommendation: string;
  risks: string[];
  opportunities: string[];
}

export interface DeepResearchResponse {
  summary: string;
  properties_analysis: PropertyAnalysis[];
  market_overview: string;
  investment_recommendation: string;
  remaining_usage: number;
}

export interface RenovationScenario {
  name: string;
  renovation_cost: number;
  duration_months: number;
  estimated_value_after: number;
  estimated_rent_after: number;
  roi_percent: number;
  payback_years: number;
  risk_level: string;
  description: string;
}

export interface CalculationResponse {
  property_summary: string;
  scenarios: RenovationScenario[];
  recommended_scenario: string;
  remaining_usage: number;
}

export interface UserLimits {
  plan: Plan;
  limits: Record<string, number>;
  usage_today: Record<string, number>;
  remaining: Record<string, number>;
}

// ─── Chat / History ───
export type ChatRole = 'user' | 'assistant';
export type ChatFeature = 'deepresearch' | 'calcola';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  feature: ChatFeature;
  docx_filename?: string;
  truncated?: boolean;
}

export interface ChatSession {
  id: string;
  feature: ChatFeature;
  title: string;
  created_at: string;
  messages: ChatMessage[];
  docx_filename?: string;
}

// ─── Storage ───
export const STORAGE_MAX_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB

export interface StorageInfo {
  used_bytes: number;
  max_bytes: number;
  used_percent: number;
  files: StoredFile[];
}

export interface StoredFile {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
  feature: ChatFeature;
  session_id: string;
}

// ─── Plan config ───
export interface PlanConfig {
  id: Plan;
  nameKey: string;
  prices: PlanPrice;
  currency: string;
  features: string[];
  limits: {
    deepresearch: number;
    calcola: number;
  };
  highlighted?: boolean;
}

export const PLAN_CONFIGS: PlanConfig[] = [
  {
    id: 'free',
    nameKey: 'planFree',
    prices: { monthly: 0, annual: 0 },
    currency: '€',
    limits: { deepresearch: 1, calcola: 1 },
    features: ['planFreeF1', 'planFreeF2', 'planFreeF3'],
  },
  {
    id: 'basic',
    nameKey: 'planBasic',
    prices: { monthly: 4.99, annual: 3.74 },
    currency: '€',
    limits: { deepresearch: 3, calcola: 3 },
    features: ['planBasicF1', 'planBasicF2', 'planBasicF3'],
  },
  {
    id: 'pro',
    nameKey: 'planPro',
    prices: { monthly: 29, annual: 21.75 },
    currency: '€',
    limits: { deepresearch: 20, calcola: 20 },
    features: ['planProF1', 'planProF2', 'planProF3', 'planProF4', 'planProF5'],
    highlighted: true,
  },
  {
    id: 'plus',
    nameKey: 'planPlus',
    prices: { monthly: 79, annual: 59.25 },
    currency: '€',
    limits: { deepresearch: 999, calcola: 999 },
    features: ['planPlusF1', 'planPlusF2', 'planPlusF3', 'planPlusF4', 'planPlusF5'],
  },
];

export const SIDEBAR_ITEMS: SidebarItem[] = [
  { id: 'dashboard',    labelKey: 'navOverview',     icon: '◈', planRequired: null },
  { id: 'deepresearch', labelKey: 'navDeepResearch', icon: '⬡', planRequired: null },
  { id: 'calcola',      labelKey: 'navCalcola',      icon: '◎', planRequired: null },
  { id: 'history',      labelKey: 'navHistory',      icon: '◷', planRequired: 'pro' },
  { id: 'storage',      labelKey: 'navStorage',      icon: '▦', planRequired: 'pro' },
];