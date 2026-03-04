import type { CoinData } from '../../types';
import { COLUMN_LABELS } from '../../types';
import { formatPrice, formatFullUSD } from '../../utils/formatters';
import { Download, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { useState } from 'react';

interface DataTableProps {
  data: CoinData[];
  columns: string[];
  onExport: () => void;
  exporting?: boolean;
}

const NUMERIC_COLS = new Set(['price', 'market_cap', 'volume', 'rank']);

export default function DataTable({ data, columns, onExport, exporting }: DataTableProps) {
  const [sortCol, setSortCol] = useState<string>('');
  const [sortAsc, setSortAsc] = useState(true);

  const visibleCols = columns.length > 0 ? columns : Object.keys(data[0] || {});

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  const sorted = (() => {
    const rows = [...data];
    if (!sortCol) return rows;

    // For numeric columns, sort within each date group to preserve chronological order
    if (NUMERIC_COLS.has(sortCol)) {
      // Group rows by date
      const grouped: Record<string, typeof data> = {};
      const dateOrder: string[] = [];
      rows.forEach((row) => {
        const key = (row as any).date ?? '';
        if (!grouped[key]) {
          grouped[key] = [];
          dateOrder.push(key);
        }
        grouped[key].push(row);
      });

      // Keep dates in chronological order
      dateOrder.sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

      // Sort within each date group by the selected numeric column
      const result: typeof data = [];
      dateOrder.forEach((date) => {
        grouped[date].sort((a, b) => {
          const aVal = (a as any)[sortCol] ?? 0;
          const bVal = (b as any)[sortCol] ?? 0;
          return sortAsc ? aVal - bVal : bVal - aVal;
        });
        result.push(...grouped[date]);
      });
      return result;
    }

    // For date column, sort chronologically
    if (sortCol === 'date') {
      rows.sort((a, b) => {
        const cmp = new Date((a as any).date).getTime() - new Date((b as any).date).getTime();
        return sortAsc ? cmp : -cmp;
      });
      return rows;
    }

    // For other columns (symbol, name), sort globally as text
    rows.sort((a, b) => {
      const aVal = (a as any)[sortCol];
      const bVal = (b as any)[sortCol];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });
    return rows;
  })();

  const formatCell = (col: string, val: any): string => {
    if (val == null) return '—';
    if (col === 'price') return formatPrice(val);
    if (col === 'market_cap' || col === 'volume') return formatFullUSD(val);
    if (col === 'symbol') return String(val).toUpperCase();
    return String(val);
  };

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Market Data</h3>
          <p className="text-xs text-gray-500 mt-0.5">{data.length} records</p>
        </div>
        <button onClick={onExport} disabled={exporting} className="btn-secondary flex items-center gap-2 text-sm disabled:opacity-50">
          <Download size={14} className={exporting ? 'animate-bounce' : ''} />
          {exporting ? 'Exporting…' : 'Export CSV'}
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {visibleCols.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className={`px-5 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100 hover:text-gray-900 select-none transition-colors ${NUMERIC_COLS.has(col) ? 'text-right' : 'text-left'}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {COLUMN_LABELS[col] || col}
                    {sortCol === col ? (
                      sortAsc ? <ArrowUp size={13} className="text-brand-600" /> : <ArrowDown size={13} className="text-brand-600" />
                    ) : (
                      <ArrowUpDown size={12} className="text-gray-300" />
                    )}
                  </span>
                  {sortCol === col && (
                    <span className="ml-1 text-[10px] text-brand-500 font-normal normal-case">
                      {sortAsc ? '(low → high)' : '(high → low)'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 transition-colors">
                {visibleCols.map((col) => (
                  <td
                    key={col}
                    className={`px-5 py-3 whitespace-nowrap text-gray-700 ${NUMERIC_COLS.has(col) ? 'text-right font-mono' : ''}`}
                  >
                    {col === 'symbol' ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-brand-50 text-brand-700 text-xs font-semibold">
                        {formatCell(col, (row as any)[col])}
                      </span>
                    ) : (
                      formatCell(col, (row as any)[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.length === 0 && (
        <div className="px-5 py-12 text-center text-gray-400">
          No data loaded. Configure filters and click "Fetch Data".
        </div>
      )}
    </div>
  );
}
