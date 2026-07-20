import React, { useState, useMemo } from "react";
import { Search, FileSearch, ChevronLeft, ChevronRight } from "lucide-react";
import type { QueryLog } from "../types/query";

interface QueryLogsProps {
  queryLogs: QueryLog[];
  setSelectedLog: (log: QueryLog) => void;
}

const logsPerPage = 8;

const matchesDate = (timestampStr: string, filter: string) => {
  if (filter === "All") return true;
  const date = new Date(timestampStr);
  const now = new Date("2026-06-26T20:32:16+07:00"); // Fictional current time
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (filter === "Today") return diffDays <= 1;
  if (filter === "7days") return diffDays <= 7;
  if (filter === "30days") return diffDays <= 30;
  return true;
};

export const QueryLogs: React.FC<QueryLogsProps> = ({
  queryLogs,
  setSelectedLog,
}) => {
  const [logSearch, setLogSearch] = useState("");
  const [logStatusFilter, setLogStatusFilter] = useState<"All" | "Success" | "Failed">("All");
  const [logDateFilter, setLogDateFilter] = useState<"All" | "Today" | "7days" | "30days">("All");
  const [logCurrentPage, setLogCurrentPage] = useState(1);

  // Query logs filtering logic
  const filteredLogs = useMemo(() => {
    return queryLogs.filter((log) => {
      const matchesSearch =
        log.question.toLowerCase().includes(logSearch.toLowerCase()) ||
        log.user.toLowerCase().includes(logSearch.toLowerCase()) ||
        log.generatedSql.toLowerCase().includes(logSearch.toLowerCase());

      const matchesStatus =
        logStatusFilter === "All" || log.status === logStatusFilter;
      const matchesDateFilter = matchesDate(log.timestamp, logDateFilter);

      return matchesSearch && matchesStatus && matchesDateFilter;
    });
  }, [queryLogs, logSearch, logStatusFilter, logDateFilter]);

  // Paginated logs
  const paginatedLogs = useMemo(() => {
    const startIndex = (logCurrentPage - 1) * logsPerPage;
    return filteredLogs.slice(startIndex, startIndex + logsPerPage);
  }, [filteredLogs, logCurrentPage]);

  const totalLogPages = Math.max(
    1,
    Math.ceil(filteredLogs.length / logsPerPage)
  );

  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden animate-fade-in">
      {/* Search and Filters Header */}
      <div className="p-5 border-b border-border bg-surface-2/45 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search logs by question, user, SQL..."
              value={logSearch}
              onChange={(e) => {
                setLogSearch(e.target.value);
                setLogCurrentPage(1);
              }}
              className="w-full bg-surface-hover border border-border text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-9 pr-4 py-2 rounded-lg text-sm focus:outline-none transition-all placeholder:text-xs font-sans"
            />
          </div>
          <div className="flex items-center gap-2.5">
            {/* Status Filter */}
            <select
              value={logStatusFilter}
              onChange={(e) => {
                setLogStatusFilter(e.target.value as any);
                setLogCurrentPage(1);
              }}
              className="bg-surface-hover text-xs font-bold px-3 py-2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer font-sans"
            >
              <option value="All">All Statuses</option>
              <option value="Success">Success Only</option>
              <option value="Failed">Failed Only</option>
            </select>

            {/* Date Filter */}
            <select
              value={logDateFilter}
              onChange={(e) => {
                setLogDateFilter(e.target.value as any);
                setLogCurrentPage(1);
              }}
              className="bg-surface-hover text-xs font-bold px-3 py-2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer font-sans"
            >
              <option value="All">All Dates</option>
              <option value="Today">Today</option>
              <option value="7days">Last 7 Days</option>
              <option value="30days">Last 30 Days</option>
            </select>

            {/* Reset filter button */}
            {(logSearch ||
              logStatusFilter !== "All" ||
              logDateFilter !== "All") && (
              <button
                type="button"
                onClick={() => {
                  setLogSearch("");
                  setLogStatusFilter("All");
                  setLogDateFilter("All");
                  setLogCurrentPage(1);
                }}
                className="text-xs text-accent hover:text-accent hover:underline font-bold px-2 py-1 flex items-center gap-1 cursor-pointer font-sans"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* QUERY LOGS EMPTY STATE Check */}
      {filteredLogs.length === 0 ? (
        <div className="p-16 text-center">
          <div className="w-12 h-12 bg-surface-2 border border-border text-text-muted rounded-full flex items-center justify-center mx-auto mb-3">
            <FileSearch className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-text mb-1 font-sans">
            No Query Logs Found
          </h4>
          <p className="text-xs text-text-faint max-w-xs mx-auto font-sans">
            We couldn't find any query log matching your criteria. Try adjusting
            your search keywords.
          </p>
        </div>
      ) : (
        /* DATA TABLE */
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-sans">
            <thead>
              <tr className="bg-surface-2 border-b border-border text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
                <th className="py-3 px-5">User</th>
                <th className="py-3 px-5">Natural Language Question</th>
                <th className="py-3 px-5">Generated SQL</th>
                <th className="py-3 px-5">Latency</th>
                <th className="py-3 px-5">Status</th>
                <th className="py-3 px-5">Timestamp</th>
                <th className="py-3 px-5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 text-xs">
              {paginatedLogs.map((log) => (
                <tr
                  key={log.id}
                  onClick={() => setSelectedLog(log)}
                  className="hover:bg-surface-hover/40 cursor-pointer transition-colors group"
                >
                  <td className="py-3 px-5 font-bold text-text font-sans">
                    {log.user}
                  </td>
                  <td className="py-3 px-5 max-w-xs truncate text-text-muted font-medium font-sans">
                    {log.question}
                  </td>
                  <td className="py-3 px-5 font-mono text-[10px] text-text-muted max-w-sm truncate bg-surface-2/40">
                    {log.generatedSql}
                  </td>
                  <td className="py-3 px-5 font-bold text-text-muted font-mono">
                    {log.executionTimeMs}ms
                  </td>
                  <td className="py-3 px-5">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold font-sans ${
                        log.status === "Success"
                          ? "bg-success/10 text-success border border-success/20"
                          : "bg-danger/10 text-danger border border-danger/20"
                      }`}
                    >
                      <span
                        className={`w-1 h-1 rounded-full ${
                          log.status === "Success"
                            ? "bg-success"
                            : "bg-danger"
                        }`}
                      ></span>
                      {log.status}
                    </span>
                  </td>
                  <td className="py-3 px-5 text-text-muted font-medium font-mono text-[10px]">
                    {new Date(log.timestamp).toLocaleString([], {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>
                  <td className="py-3 px-5 text-center">
                    <button
                      type="button"
                      className="text-[10px] font-bold text-accent hover:text-accent bg-accent/10 hover:bg-accent/20 px-2.5 py-1 rounded border border-accent/20 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer font-sans"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedLog(log);
                      }}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Bar */}
      {filteredLogs.length > 0 && (
        <div className="p-4 border-t border-border bg-surface-2 flex items-center justify-between">
          <span className="text-xs text-text-muted font-semibold font-sans">
            Showing{" "}
            <span className="font-bold text-text">
              {Math.min(
                filteredLogs.length,
                (logCurrentPage - 1) * logsPerPage + 1
              )}
              -
              {Math.min(filteredLogs.length, logCurrentPage * logsPerPage)}
            </span>{" "}
            of{" "}
            <span className="font-bold text-text">
              {filteredLogs.length}
            </span>{" "}
            queries
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={logCurrentPage === 1}
              onClick={() => setLogCurrentPage((prev) => Math.max(1, prev - 1))}
              className="p-1.5 border border-border rounded-md bg-surface-hover hover:bg-[#1D3F3A] disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer text-text-muted"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            {[...Array(totalLogPages)].map((_, i) => (
              <button
                type="button"
                key={i}
                onClick={() => setLogCurrentPage(i + 1)}
                className={`px-2.5 py-1 text-xs font-bold rounded-md border cursor-pointer font-mono ${
                  logCurrentPage === i + 1
                    ? "bg-gradient-to-r from-accent to-teal text-white border-none shadow-md"
                    : "bg-surface-hover text-text-muted border-border hover:bg-[#1D3F3A]"
                }`}
              >
                {i + 1}
              </button>
            ))}
            <button
              type="button"
              disabled={logCurrentPage === totalLogPages}
              onClick={() =>
                setLogCurrentPage((prev) => Math.min(totalLogPages, prev + 1))
              }
              className="p-1.5 border border-border rounded-md bg-surface-hover hover:bg-[#1D3F3A] disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer text-text-muted"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
