import { useState } from 'react';
import { fetchTopCoins, downloadExportCSV } from '../api/marketDataApi';
import type { CoinData, FilterState } from '../types';
import FilterPanel from '../components/filters/FilterPanel';
import DataTable from '../components/tables/DataTable';
import PriceChart from '../components/charts/PriceChart';
import MarketCapChart from '../components/charts/MarketCapChart';

const defaultFilters: FilterState = {
  topN: 15,
  startYear: 2020,
  endYear: 2025,
  position: 'end',
  quarters: '',
  columns: ['date', 'symbol', 'name', 'price', 'market_cap', 'volume'],
  excludeSectors: [],
};

export default function HistoricalExplorer() {
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [data, setData] = useState<CoinData[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');

  const handleApply = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchTopCoins({
        topN: filters.topN,
        startYear: filters.startYear,
        endYear: filters.endYear,
        position: filters.position,
        quarters: filters.quarters || undefined,
        excludeSectors: filters.excludeSectors.length > 0 ? filters.excludeSectors : undefined,
      });
      setData(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadExportCSV({
        topN: filters.topN,
        startYear: filters.startYear,
        endYear: filters.endYear,
        position: filters.position,
        quarters: filters.quarters || undefined,
        columns: filters.columns.length > 0 ? filters.columns : undefined,
        excludeSectors: filters.excludeSectors.length > 0 ? filters.excludeSectors : undefined,
      });
    } catch (err: any) {
      setError(err.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Historical Explorer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Query and export historical crypto market data — rebalanced quarterly by market cap
        </p>
      </div>

      {/* Filters */}
      <FilterPanel
        filters={filters}
        onChange={setFilters}
        onApply={handleApply}
        loading={loading}
      />

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Charts */}
      {data.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {filters.columns.includes('price') && <PriceChart data={data} />}
          {filters.columns.includes('market_cap') && <MarketCapChart data={data} />}
        </div>
      )}

      {/* Data Table */}
      <DataTable data={data} columns={filters.columns} onExport={handleExport} exporting={exporting} />
    </div>
  );
}
