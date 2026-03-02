import { useEffect, useState } from 'react';
import { fetchRiskMetrics } from '../api/marketDataApi';
import type { RiskMetric } from '../types';
import { exportCSV, exportPDF } from '../utils/exportUtils';
import { Download, FileText } from 'lucide-react';

const PERIOD_OPTIONS = [
  { label: '90 days', value: 90 },
  { label: '180 days', value: 180 },
  { label: '1 year', value: 365 },
  { label: '2 years', value: 730 },
];

function colorClass(val: number, invert = false): string {
  const positive = invert ? val < 0 : val > 0;
  if (positive) return 'text-green-600';
  if (val === 0) return 'text-gray-500';
  return 'text-red-500';
}

function sharpeColor(val: number): string {
  if (val >= 2) return 'bg-green-100 text-green-800';
  if (val >= 1) return 'bg-green-50 text-green-700';
  if (val >= 0) return 'bg-yellow-50 text-yellow-700';
  return 'bg-red-50 text-red-700';
}

export default function RiskMetrics() {
  const [data, setData] = useState<RiskMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(365);
  const [sortKey, setSortKey] = useState<keyof RiskMetric>('sharpe_ratio');
  const [sortAsc, setSortAsc] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchRiskMetrics({ days, topN: 20 });
      setData(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch risk metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [days]);

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] as number;
    const bv = b[sortKey] as number;
    return sortAsc ? av - bv : bv - av;
  });

  const handleSort = (key: keyof RiskMetric) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const SortHeader = ({ label, field }: { label: string; field: keyof RiskMetric }) => (
    <th
      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700 whitespace-nowrap"
      onClick={() => handleSort(field)}
    >
      {label} {sortKey === field ? (sortAsc ? '↑' : '↓') : ''}
    </th>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Metrics</h1>
        <p className="text-sm text-gray-500 mt-1">
          Sharpe ratio, Sortino ratio, max drawdown, and Value at Risk for top cryptocurrencies
        </p>
      </div>

      {/* Controls */}
      <div className="card p-4 flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Lookback Period</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="text-xs text-gray-400 self-end pb-2">
          Risk-free rate: 5% · {data.length} coins
        </div>
        <div className="ml-auto flex gap-2 self-end">
          <button
            disabled={data.length === 0}
            onClick={() => exportCSV(data as unknown as Record<string, unknown>[], `risk-metrics-${days}d.csv`, [
              { key: 'coin_id', label: 'Coin' },
              { key: 'sector', label: 'Sector' },
              { key: 'annualised_return', label: 'Ann. Return %' },
              { key: 'annualised_volatility', label: 'Ann. Volatility %' },
              { key: 'sharpe_ratio', label: 'Sharpe' },
              { key: 'sortino_ratio', label: 'Sortino' },
              { key: 'max_drawdown', label: 'Max Drawdown %' },
              { key: 'var_95', label: 'VaR 95%' },
              { key: 'var_99', label: 'VaR 99%' },
            ])}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <Download size={14} /> CSV
          </button>
          <button
            onClick={() => exportPDF(`Risk Metrics – ${days}d`)}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <FileText size={14} /> PDF
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-[40vh]">
          <div className="text-center">
            <svg className="animate-spin h-8 w-8 text-brand-600 mx-auto mb-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm text-gray-500">Computing risk metrics… this may take a minute.</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      {!loading && sorted.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                <SortHeader label="Coin" field="coin_id" />
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sector</th>
                <SortHeader label="Return (ann.)" field="annualised_return" />
                <SortHeader label="Volatility (ann.)" field="annualised_volatility" />
                <SortHeader label="Sharpe" field="sharpe_ratio" />
                <SortHeader label="Sortino" field="sortino_ratio" />
                <SortHeader label="Max Drawdown" field="max_drawdown" />
                <SortHeader label="VaR 95%" field="var_95" />
                <SortHeader label="VaR 99%" field="var_99" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted.map((m, i) => (
                <tr key={m.coin_id} className="hover:bg-gray-50">
                  <td className="px-3 py-3 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-3 py-3 font-medium text-gray-900 whitespace-nowrap">
                    {m.coin_id.replace(/-/g, ' ')}
                  </td>
                  <td className="px-3 py-3">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">
                      {m.sector}
                    </span>
                  </td>
                  <td className={`px-3 py-3 font-mono ${colorClass(m.annualised_return)}`}>
                    {m.annualised_return > 0 ? '+' : ''}{m.annualised_return}%
                  </td>
                  <td className="px-3 py-3 font-mono text-gray-600">
                    {m.annualised_volatility}%
                  </td>
                  <td className="px-3 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${sharpeColor(m.sharpe_ratio)}`}>
                      {m.sharpe_ratio.toFixed(2)}
                    </span>
                  </td>
                  <td className={`px-3 py-3 font-mono ${colorClass(m.sortino_ratio)}`}>
                    {m.sortino_ratio.toFixed(2)}
                  </td>
                  <td className="px-3 py-3 font-mono text-red-500">
                    {m.max_drawdown}%
                  </td>
                  <td className="px-3 py-3 font-mono text-gray-600">
                    {m.var_95}%
                  </td>
                  <td className="px-3 py-3 font-mono text-gray-600">
                    {m.var_99}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Explainer */}
      {!loading && sorted.length > 0 && (
        <div className="card p-4 text-xs text-gray-500 space-y-1">
          <p><strong>Sharpe Ratio:</strong> Risk-adjusted return. Higher is better. &gt;1 is good, &gt;2 is excellent.</p>
          <p><strong>Sortino Ratio:</strong> Like Sharpe but only penalises downside volatility.</p>
          <p><strong>Max Drawdown:</strong> Largest peak-to-trough decline in the period.</p>
          <p><strong>VaR 95%:</strong> Worst expected daily loss 95% of the time (parametric).</p>
        </div>
      )}
    </div>
  );
}
