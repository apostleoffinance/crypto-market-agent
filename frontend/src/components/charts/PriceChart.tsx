import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts';
import type { CoinData } from '../../types';
import { formatCompact, formatPrice } from '../../utils/formatters';

interface PriceChartProps {
  data: CoinData[];
}

export default function PriceChart({ data }: PriceChartProps) {
  // Group data: for each date, pick top 5 coins and make them separate lines
  const dates = [...new Set(data.map((d) => d.date))].sort();
  const topSymbols = [...new Set(data.slice(0, 50).map((d) => d.symbol))].slice(0, 5);

  const chartData = dates.map((date) => {
    const row: any = { date };
    const dateRows = data.filter((d) => d.date === date);
    for (const sym of topSymbols) {
      const coin = dateRows.find((d) => d.symbol === sym);
      row[sym!] = coin?.price ?? null;
    }
    return row;
  });

  const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  if (chartData.length === 0) return null;

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Price Trend (Top 5 Coins)</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData}>
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
            formatter={(val: number) => formatPrice(val)}
            labelStyle={{ fontWeight: 600 }}
            contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <Legend />
          {topSymbols.map((sym, i) => (
            <Line
              key={sym}
              type="monotone"
              dataKey={sym!}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
