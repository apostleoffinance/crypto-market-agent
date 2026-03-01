import { TrendingUp } from 'lucide-react';

export default function Header({ title }: { title: string }) {
  return (
    <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-gray-200">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="lg:hidden text-2xl">🪙</div>
          <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <TrendingUp size={16} className="text-green-500" />
          <span>Live Data via CoinGecko Pro API</span>
        </div>
      </div>
    </header>
  );
}
