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

export interface FilterState {
  topN: number;
  startYear: number;
  endYear: number;
  position: 'start' | 'end' | 'both';
  columns: string[];
  quarters: string;
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
