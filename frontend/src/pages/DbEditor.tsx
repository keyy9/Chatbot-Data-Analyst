import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Database, RefreshCw, Search, AlertTriangle } from "lucide-react";
import { adminApi, dataApi, ApiError } from "../lib/apiClient";

interface DbEditorProps {
  userId: string;
  sessionId: string;
}

/** Displays rows returned by the business database. Writes remain in Admin Chat,
 * where they require the existing explicit confirmation flow. */
export const DbEditor: React.FC<DbEditorProps> = ({ userId, sessionId }) => {
  const [tables, setTables] = useState<string[]>([]);
  const [table, setTable] = useState<string>("");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dataApi.getTables().then((res) => {
      const names = Object.keys(res.tables);
      setTables(names);
      setTable((current) => current || names[0] || "");
    }).catch(() => setError("Failed to load table list."));
  }, []);

  const loadRows = useCallback(async () => {
    if (!table) return;
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.executeQuery(`SELECT * FROM ${table} LIMIT 100`, userId, sessionId);
      setRows(result.data);
      setColumns(result.columns);
    } catch (err) {
      setRows([]);
      setColumns([]);
      setError(err instanceof ApiError ? err.message : "Failed to load database rows.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, table, userId]);

  useEffect(() => { loadRows(); }, [loadRows]);

  const visibleRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(term)));
  }, [rows, search]);

  return (
    <div className="space-y-6 animate-fade-in text-text font-sans">
      <div className="bg-surface border border-border shadow-lg p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-surface-2 border border-border flex items-center justify-center text-accent"><Database className="w-4 h-4" /></div>
          <div><h2 className="text-sm font-bold">Business Database</h2><p className="text-xs text-text-muted">Live rows from the connected database (up to 100 rows).</p></div>
        </div>
        <div className="flex gap-2">
          <select value={table} onChange={(e) => setTable(e.target.value)} className="bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs font-bold">
            {tables.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
          <button type="button" onClick={loadRows} disabled={loading} className="bg-accent text-white rounded-lg px-3 py-2 text-xs font-bold flex gap-1.5 items-center disabled:opacity-60"><RefreshCw className={loading ? "w-3.5 h-3.5 animate-spin" : "w-3.5 h-3.5"} /> Refresh</button>
        </div>
      </div>

      <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden">
        <div className="p-4 border-b border-border bg-surface-2/45 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <span className="text-xs text-text-muted">{loading ? "Loading..." : `${visibleRows.length} live row(s)`}</span>
          <label className="relative w-full sm:w-72"><Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-text-muted" /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search loaded rows..." className="w-full pl-8 pr-3 py-2 text-xs bg-surface border border-border rounded-lg" /></label>
        </div>
        {error ? <div className="p-8 text-center text-amber-400 text-xs flex justify-center gap-2"><AlertTriangle className="w-4 h-4" />{error}</div> :
          !loading && visibleRows.length === 0 ? <div className="p-10 text-center text-text-muted text-xs">No rows found in <code>{table}</code>.</div> :
          <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="bg-surface-2 text-text-muted">{columns.map((column) => <th key={column} className="px-4 py-3 font-bold whitespace-nowrap">{column}</th>)}</tr></thead><tbody className="divide-y divide-border">{visibleRows.map((row, index) => <tr key={index} className="hover:bg-surface-hover/40">{columns.map((column) => <td key={column} className="px-4 py-3 whitespace-nowrap max-w-64 truncate">{row[column] === null ? "—" : String(row[column])}</td>)}</tr>)}</tbody></table></div>}
      </div>
      <p className="text-[11px] text-text-muted">To add, edit, or delete data, use Admin Chat. Every write is proposed first and requires confirmation before it reaches the database.</p>
    </div>
  );
};
