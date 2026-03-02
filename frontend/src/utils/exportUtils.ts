/**
 * Client-side PDF + CSV export helpers.
 *
 * PDF: uses window.print() with a print-friendly stylesheet.
 * CSV: builds a Blob and triggers a download.
 */

/* ────────── PDF (window.print wrapper) ────────── */

export function exportPDF(title?: string) {
  // Temporarily set document title so the PDF filename is nice
  const prev = document.title;
  if (title) document.title = title;
  window.print();
  document.title = prev;
}

/* ────────── CSV helpers ────────── */

function escapeCSV(val: unknown): string {
  const s = String(val ?? '');
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

/** Convert an array of objects into a CSV string */
export function toCSV<T extends Record<string, unknown>>(rows: T[], columns?: { key: keyof T; label: string }[]): string {
  if (rows.length === 0) return '';

  const cols = columns ?? Object.keys(rows[0]).map((k) => ({ key: k as keyof T, label: String(k) }));
  const header = cols.map((c) => escapeCSV(c.label)).join(',');
  const body = rows.map((row) => cols.map((c) => escapeCSV(row[c.key])).join(',')).join('\n');
  return header + '\n' + body;
}

/** Trigger browser download of a CSV string */
export function downloadCSV(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Convenience: convert rows → CSV → download */
export function exportCSV<T extends Record<string, unknown>>(
  rows: T[],
  filename: string,
  columns?: { key: keyof T; label: string }[],
) {
  downloadCSV(toCSV(rows, columns), filename);
}
