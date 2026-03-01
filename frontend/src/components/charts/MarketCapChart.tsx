import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import type { CoinData } from '../../types';
import { formatCompact, formatUSD } from '../../utils/formatters';

interface MarketCapChartProps {
  data: CoinData[];
}

export default function MarketCapChart({ data }: MarketCapChartProps) {
  // For each date, show total market cap of the top coins
  const dates = [...new Set(data.map((d) => d.date))].sort();

  const chartData = dates.map((date) => {
    const dateRows = data.filter((d) => d.date === date);
    const totalMcap = dateRows.reduce((sum, r) => sum + (r.market_cap || 0), 0);
    return { date, total_market_cap: totalMcap };
  });

  if (chartData.length === 0) return null;

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Combined Market Cap Over Time
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => v.slice(0, 7)}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `$${formatCompact(v)}`}
          />
          <Tooltip
            formatter={(val: number) => formatUSD(val)}
            labelStyle={{ fontWeight: 600 }}
            contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey="total_market_cap" name="Total Market Cap" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
