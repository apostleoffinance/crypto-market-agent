import { type FilterState, ALL_COLUMNS, COLUMN_LABELS } from '../../types';

interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onApply: () => void;
  loading: boolean;
}

export default function FilterPanel({ filters, onChange, onApply, loading }: FilterPanelProps) {
  const update = (patch: Partial<FilterState>) => onChange({ ...filters, ...patch });

  const toggleColumn = (col: string) => {
    const cols = filters.columns.includes(col)
      ? filters.columns.filter((c) => c !== col)
      : [...filters.columns, col];
    update({ columns: cols });
  };

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Filters</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {/* Top N */}
        <div>
          <label className="label">Top N Coins</label>
          <input
            type="number"
            min={1}
            max={100}
            value={filters.topN}
            onChange={(e) => update({ topN: Number(e.target.value) || 15 })}
            className="input-field"
          />
        </div>

        {/* Start Year */}
        <div>
          <label className="label">Start Year</label>
          <input
            type="number"
            min={2010}
            max={2030}
            value={filters.startYear}
            onChange={(e) => update({ startYear: Number(e.target.value) || 2020 })}
            className="input-field"
          />
        </div>

        {/* End Year */}
        <div>
          <label className="label">End Year</label>
          <input
            type="number"
            min={2010}
            max={2030}
            value={filters.endYear}
            onChange={(e) => update({ endYear: Number(e.target.value) || 2026 })}
            className="input-field"
          />
        </div>

        {/* Position */}
        <div>
          <label className="label">Quarter Position</label>
          <select
            value={filters.position}
            onChange={(e) => update({ position: e.target.value as FilterState['position'] })}
            className="input-field"
          >
            <option value="end">Quarter End</option>
            <option value="start">Quarter Start</option>
            <option value="both">Both</option>
          </select>
        </div>

        {/* Specific Quarters */}
        <div>
          <label className="label">Specific Quarters</label>
          <input
            type="text"
            placeholder="e.g. 2024-Q1,2024-Q4"
            value={filters.quarters}
            onChange={(e) => update({ quarters: e.target.value })}
            className="input-field"
          />
        </div>

        {/* Apply Button */}
        <div className="flex items-end">
          <button onClick={onApply} disabled={loading} className="btn-primary w-full">
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Loading…
              </span>
            ) : (
              'Fetch Data'
            )}
          </button>
        </div>
      </div>

      {/* Column Selector */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <label className="label">Columns to Display</label>
        <div className="flex flex-wrap gap-2">
          {ALL_COLUMNS.map((col) => (
            <button
              key={col}
              onClick={() => toggleColumn(col)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                filters.columns.includes(col)
                  ? 'bg-brand-100 text-brand-700 ring-1 ring-brand-300'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {COLUMN_LABELS[col]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
