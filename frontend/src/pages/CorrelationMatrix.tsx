import { useEffect, useState } from 'react';
import { fetchCorrelation } from '../api/marketDataApi';
import type { CorrelationResponse } from '../types';

const PERIOD_OPTIONS = [
  { label: '90 days', value: 90 },
  { label: '180 days', value: 180 },
  { label: '1 year', value: 365 },
  { label: '2 years', value: 730 },
];

const COUNT_OPTIONS = [
  { label: 'Top 10', value: 10 },
  { label: 'Top 15', value: 15 },
  { label: 'Top 20', value: 20 },
];

function getCorrelationColor(val: number): string {
  // Strong positive → blue, zero → white, strong negative → red
  if (val >= 0.8) return 'bg-blue-600 text-white';
  if (val >= 0.6) return 'bg-blue-400 text-white';
  if (val >= 0.4) return 'bg-blue-200 text-blue-900';
  if (val >= 0.2) return 'bg-blue-50 text-blue-900';
  if (val >= -0.2) return 'bg-gray-50 text-gray-700';
  if (val >= -0.4) return 'bg-red-100 text-red-900';
  if (val >= -0.6) return 'bg-red-300 text-white';
  return 'bg-red-500 text-white';
}

export default function CorrelationMatrix() {
  const [data, setData] = useState<CorrelationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(365);
  const [topN, setTopN] = useState(15);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchCorrelation({ days, topN });
      if (res.error) {
        setError(res.error);
      } else {
        setData(res);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch correlation data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [days, topN]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Correlation Matrix</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pairwise correlations of daily log returns — identify diversification opportunities
        </p>
      </div>

      {/* Controls */}
      <div className="card p-4 flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Period</label>
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
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Coins</label>
          <select
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {COUNT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        {data && (
          <div className="text-xs text-gray-400 self-end pb-2">
            {data.data_points} data points
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-[40vh]">
          <div className="text-center">
            <svg className="animate-spin h-8 w-8 text-brand-600 mx-auto mb-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm text-gray-500">Computing correlations… this may take a minute.</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Heatmap */}
      {!loading && data && !error && (
        <div className="card overflow-x-auto">
          <table className="text-xs">
            <thead>
              <tr>
                <th className="px-2 py-2 text-left sticky left-0 bg-white z-10"></th>
                {data.coins.map((coin) => (
                  <th key={coin} className="px-2 py-2 text-center font-medium text-gray-600 whitespace-nowrap">
                    {coin.replace(/-/g, ' ').slice(0, 8)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.coins.map((rowCoin, i) => (
                <tr key={rowCoin}>
                  <td className="px-2 py-2 font-medium text-gray-700 sticky left-0 bg-white z-10 whitespace-nowrap">
                    {rowCoin.replace(/-/g, ' ').slice(0, 10)}
                  </td>
                  {data.matrix[i].map((val, j) => (
                    <td
                      key={j}
                      className={`px-2 py-2 text-center font-mono ${getCorrelationColor(val)}`}
                      title={`${rowCoin} × ${data.coins[j]}: ${val.toFixed(4)}`}
                    >
                      {i === j ? '1.00' : val.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Legend */}
      {!loading && data && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Legend:</span>
          <span className="inline-block w-4 h-4 bg-red-500 rounded"></span>
          <span>-1.0</span>
          <span className="inline-block w-4 h-4 bg-gray-50 border rounded"></span>
          <span>0.0</span>
          <span className="inline-block w-4 h-4 bg-blue-600 rounded"></span>
          <span>+1.0</span>
        </div>
      )}
    </div>
  );
}
