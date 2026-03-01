import { useEffect, useState } from 'react';
import { fetchSummary, fetchTopCoins } from '../api/marketDataApi';
import type { CoinData, SummaryResponse } from '../types';
import { formatUSD, formatFullUSD, formatCompact, formatNumber } from '../utils/formatters';
import StatCard from '../components/cards/StatCard';
import PriceChart from '../components/charts/PriceChart';
import MarketCapChart from '../components/charts/MarketCapChart';
import { BarChart3, Coins, CalendarRange, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [previewData, setPreviewData] = useState<CoinData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [sum, preview] = await Promise.all([
          fetchSummary(),
          fetchTopCoins({ topN: 10, startYear: 2024, endYear: 2025, position: 'end' }),
        ]);
        setSummary(sum);
        setPreviewData(preview.data);
      } catch (err) {
        console.error('Dashboard load error:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <svg className="animate-spin h-8 w-8 text-brand-600 mx-auto mb-3" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-sm text-gray-500">Loading dashboard data…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Overview of historical cryptocurrency market data
        </p>
      </div>

      {/* Stat Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Data Points"
            value={formatNumber(summary.total_data_points)}
            subtitle={`${summary.unique_coins_tracked} unique coins`}
            icon={<BarChart3 size={20} />}
            color="brand"
          />
          <StatCard
            title="Quarters Tracked"
            value={String(summary.total_quarters)}
            subtitle={summary.date_range}
            icon={<CalendarRange size={20} />}
            color="blue"
          />
          <StatCard
            title="Top Coin"
            value={summary.top_coin?.symbol.toUpperCase() || '—'}
            subtitle={summary.top_coin ? formatUSD(summary.top_coin.market_cap) + ' market cap' : ''}
            icon={<Coins size={20} />}
            color="amber"
          />
          <StatCard
            title="Highest Price"
            value={summary.top_coin ? `$${formatCompact(summary.top_coin.price)}` : '—'}
            subtitle={summary.top_coin?.name || ''}
            icon={<TrendingUp size={20} />}
            color="green"
          />
        </div>
      )}

      {/* Charts */}
      {previewData.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <PriceChart data={previewData} />
          <MarketCapChart data={previewData} />
        </div>
      )}

      {/* Recent Data Preview */}
      {previewData.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900">Recent Quarter Data (Preview)</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Top 10 coins · Quarter ends 2024–2025 ·{' '}
              <a href="/explorer" className="text-brand-600 hover:underline">
                Open Explorer →
              </a>
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Date</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Symbol</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Name</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Price</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Market Cap</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {previewData.slice(0, 20).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 text-gray-700">{row.date}</td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-brand-50 text-brand-700 text-xs font-semibold">
                        {row.symbol?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-700">{row.name}</td>
                    <td className="px-5 py-3 text-right text-gray-700">{formatFullUSD(row.price || 0)}</td>
                    <td className="px-5 py-3 text-right text-gray-700">{formatFullUSD(row.market_cap || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
