export interface CoinData {
  date?: string;
  symbol?: string;
  name?: string;
  price?: number;
  market_cap?: number;
  volume?: number;
}

export interface TopCoinsResponse {
  data: CoinData[];
  total_rows: number;
  dates_queried: number;
}

export interface QuarterDatesResponse {
  dates: string[];
  count: number;
}

export interface SummaryResponse {
  total_quarters: number;
  unique_coins_tracked: number;
  date_range: string;
  top_coin: {
    symbol: string;
    name: string;
    price: number;
    market_cap: number;
  } | null;
  total_data_points: number;
}

export const SECTORS = [
  'Layer 1',
  'Layer 2',
  'DeFi',
  'Exchange',
  'Meme',
  'AI',
  'Payments',
  'RWA',
  'Infrastructure',
  'Other',
] as const;

export interface FilterState {
  topN: number;
  startYear: number;
  endYear: number;
  position: 'start' | 'end' | 'both';
  columns: string[];
  quarters: string;
  excludeSectors: string[];
}

export const ALL_COLUMNS = ['date', 'symbol', 'name', 'price', 'market_cap', 'volume'] as const;

export const COLUMN_LABELS: Record<string, string> = {
  date: 'Date',
  symbol: 'Symbol',
  name: 'Name',
  price: 'Price (USD)',
  market_cap: 'Market Cap (USD)',
  volume: 'Volume (USD)',
};

// ── Analytics types ──────────────────────────────────────────────────

export interface CorrelationResponse {
  coins: string[];
  matrix: number[][];
  days: number;
  data_points: number;
  error?: string;
}

export interface RiskMetric {
  coin_id: string;
  sector: string;
  current_price: number;
  annualised_return: number;
  annualised_volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  var_95: number;
  var_99: number;
  data_points: number;
}

export interface RiskMetricsResponse {
  data: RiskMetric[];
  days: number;
  risk_free_rate: number;
}

export interface SectorCoin {
  coin_id: string;
  current_price: number;
  pct_7d: number | null;
  pct_30d: number | null;
  pct_90d: number | null;
  pct_ytd: number | null;
}

export interface Sector {
  sector: string;
  coin_count: number;
  avg_7d: number | null;
  avg_30d: number | null;
  avg_90d: number | null;
  avg_ytd: number | null;
  coins: SectorCoin[];
}

export interface SectorResponse {
  sectors: Sector[];
  total_coins: number;
  as_of: string;
}
