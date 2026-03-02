import { useEffect, useState } from 'react';
import { fetchSectors } from '../api/marketDataApi';
import type { Sector, SectorCoin } from '../types';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react';

function pctClass(val: number): string {
  if (val > 0) return 'text-green-600';
  if (val < 0) return 'text-red-500';
  return 'text-gray-500';
}

function PerfBadge({ value }: { value: number }) {
  return (
    <span className={`inline-flex items-center gap-0.5 font-mono text-sm ${pctClass(value)}`}>
      {value > 0 ? <TrendingUp size={14} /> : value < 0 ? <TrendingDown size={14} /> : null}
      {value > 0 ? '+' : ''}{value}%
    </span>
  );
}

function SectorRow({ sector, isOpen, toggle }: { sector: Sector; isOpen: boolean; toggle: () => void }) {
  return (
    <>
      <tr className="cursor-pointer hover:bg-gray-50 border-b" onClick={toggle}>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span className="font-semibold text-gray-900">{sector.sector}</span>
            <span className="text-xs text-gray-400">({sector.coin_count} coins)</span>
          </div>
        </td>
        <td className="px-4 py-3 text-right"><PerfBadge value={sector.perf_7d} /></td>
        <td className="px-4 py-3 text-right"><PerfBadge value={sector.perf_30d} /></td>
        <td className="px-4 py-3 text-right"><PerfBadge value={sector.perf_90d} /></td>
        <td className="px-4 py-3 text-right"><PerfBadge value={sector.perf_ytd} /></td>
        <td className="px-4 py-3 text-right font-mono text-gray-600">
          ${formatMcap(sector.total_market_cap)}
        </td>
      </tr>
      {isOpen && sector.coins.map((c) => (
        <CoinRow key={c.coin_id} coin={c} />
      ))}
    </>
  );
}

function CoinRow({ coin }: { coin: SectorCoin }) {
  return (
    <tr className="bg-gray-50/50 border-b border-gray-100">
      <td className="px-4 py-2 pl-10">
        <span className="text-sm text-gray-700">{coin.coin_id.replace(/-/g, ' ')}</span>
      </td>
      <td className="px-4 py-2 text-right"><PerfBadge value={coin.perf_7d} /></td>
      <td className="px-4 py-2 text-right"><PerfBadge value={coin.perf_30d} /></td>
      <td className="px-4 py-2 text-right"><PerfBadge value={coin.perf_90d} /></td>
      <td className="px-4 py-2 text-right"><PerfBadge value={coin.perf_ytd} /></td>
      <td className="px-4 py-2 text-right font-mono text-gray-500 text-xs">
        ${formatMcap(coin.market_cap)}
      </td>
    </tr>
  );
}

function formatMcap(val: number): string {
  if (val >= 1e12) return (val / 1e12).toFixed(2) + 'T';
  if (val >= 1e9) return (val / 1e9).toFixed(2) + 'B';
  if (val >= 1e6) return (val / 1e6).toFixed(2) + 'M';
  return val.toLocaleString();
}

export default function SectorRotation() {
  const [data, setData] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openSectors, setOpenSectors] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<'perf_7d' | 'perf_30d' | 'perf_90d' | 'perf_ytd' | 'total_market_cap'>('perf_30d');
  const [sortAsc, setSortAsc] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchSectors();
      setData(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load sectors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = (name: string) => {
    setOpenSectors((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    return sortAsc ? av - bv : bv - av;
  });

  const ColHead = ({ label, field }: { label: string; field: typeof sortKey }) => (
    <th
      className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700"
      onClick={() => handleSort(field)}
    >
      {label} {sortKey === field ? (sortAsc ? '↑' : '↓') : ''}
    </th>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sector Rotation</h1>
        <p className="text-sm text-gray-500 mt-1">
          Performance breakdown by sector — click a row to see individual coins
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-[40vh]">
          <div className="text-center">
            <svg className="animate-spin h-8 w-8 text-brand-600 mx-auto mb-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm text-gray-500">Loading sector data…</p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && sorted.length > 0 && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {sorted.slice(0, 4).map((s) => (
              <div key={s.sector} className="card p-4">
                <p className="text-xs text-gray-500 font-medium mb-1">{s.sector}</p>
                <div className="flex items-baseline gap-2">
                  <PerfBadge value={s.perf_30d} />
                  <span className="text-xs text-gray-400">30d</span>
                </div>
              </div>
            ))}
          </div>

          {/* Table */}
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sector</th>
                  <ColHead label="7d" field="perf_7d" />
                  <ColHead label="30d" field="perf_30d" />
                  <ColHead label="90d" field="perf_90d" />
                  <ColHead label="YTD" field="perf_ytd" />
                  <ColHead label="Market Cap" field="total_market_cap" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <SectorRow
                    key={s.sector}
                    sector={s}
                    isOpen={openSectors.has(s.sector)}
                    toggle={() => toggle(s.sector)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
