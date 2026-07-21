import React, { useCallback, useEffect, useState } from "react";
import { Play, Plus, RefreshCw, X } from "lucide-react";
import { BenchmarkEvalPanel } from "../components/BenchmarkEvalPanel";
import { PipelineEvalPanel } from "../components/PipelineEvalPanel";
import { ApiError, evaluationApi, type BenchmarkQuestionApi } from "../lib/apiClient";
import { useAuthStore } from "../store/authStore";

export const Benchmark: React.FC = () => {
  const { user } = useAuthStore();
  const [questions, setQuestions] = useState<BenchmarkQuestionApi[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [question, setQuestion] = useState("");
  const [goldSql, setGoldSql] = useState("");
  const [goldAnswer, setGoldAnswer] = useState("");
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [limit, setLimit] = useState<number | undefined>(undefined);

  const loadQuestions = useCallback(async () => {
    if (!user?.userId) return;
    try { setQuestions((await evaluationApi.getBenchmarkQuestions(user.userId)).questions); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Failed to load benchmark questions."); }
  }, [user?.userId]);
  useEffect(() => { loadQuestions(); }, [loadQuestions]);

  const checkInitialStatus = useCallback(async () => {
    if (!user?.userId) return;
    try {
      const status = await evaluationApi.getBenchmarkRunStatus(user.userId);
      if (status.is_running) {
        setRunning(true);
      }
    } catch { /* ignore */ }
  }, [user?.userId]);
  useEffect(() => { checkInitialStatus(); }, [checkInitialStatus]);

  useEffect(() => {
    if (!running || !user?.userId) return;
    const timer = window.setInterval(async () => {
      try {
        const status = await evaluationApi.getBenchmarkRunStatus(user.userId);
        if (!status.is_running) {
          setRunning(false);
          if (status.error) {
            setMessage(`Benchmark run failed: ${status.error}`);
          } else {
            setRefreshKey((key) => key + 1);
            setMessage("Benchmark run completed. Results have been refreshed.");
          }
        }
      } catch { /* retry on next poll */ }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [running, user?.userId]);

  const addQuestion = async (event: React.FormEvent) => {
    event.preventDefault(); if (!user?.userId) return;
    setSaving(true); setMessage(null);
    try {
      await evaluationApi.addBenchmarkQuestion(user.userId, question, goldSql, goldAnswer);
      setQuestion(""); setGoldSql(""); setGoldAnswer(""); setShowForm(false);
      setMessage("Benchmark question saved to the database."); await loadQuestions();
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "Failed to save benchmark question."); }
    finally { setSaving(false); }
  };
  const runBenchmark = async () => {
    if (!user?.userId || running) return;
    try { const result = await evaluationApi.runBenchmark(user.userId, limit); setRunning(true); setMessage(result.message); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Could not start the benchmark run."); }
  };

  return <div className="space-y-6 font-sans">
    <div className="bg-surface border border-border shadow-lg p-5 rounded-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text">Benchmark Evaluations</h2>
          <p className="text-xs text-text-muted mt-1">Cases and results are persisted in the backend database.</p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select
            value={limit === undefined ? "all" : limit.toString()}
            onChange={(e) => setLimit(e.target.value === "all" ? undefined : Number(e.target.value))}
            disabled={running}
            className="px-3 py-2 text-xs bg-surface-hover border border-border rounded-lg text-text font-bold focus:outline-none cursor-pointer"
          >
            <option value="all">All Cases ({questions.length})</option>
            <option value="5">Quick Test (5 cases)</option>
            <option value="10">Medium Test (10 cases)</option>
            <option value="20">Large Test (20 cases)</option>
          </select>
          <button type="button" onClick={() => setShowForm((value) => !value)} disabled={running} className="px-4 py-2 text-xs font-bold rounded-lg border border-border bg-surface-hover flex gap-1.5 items-center disabled:opacity-50 cursor-pointer"><Plus className="w-3.5 h-3.5" /> Add Question</button>
          <button type="button" onClick={runBenchmark} disabled={running || questions.length === 0} className="px-4 py-2 text-xs font-bold rounded-lg bg-gradient-to-r from-accent to-teal text-white flex gap-1.5 items-center disabled:opacity-50 cursor-pointer"><Play className="w-3.5 h-3.5" /> {running ? "Running..." : "Execute Run"}</button>
        </div>
      </div>
      {message && <p className="text-xs text-text-muted">{message}</p>}
      {running && <div className="flex gap-2 items-center text-xs text-accent"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Evaluation is running in the backend and may take several minutes.</div>}
      {showForm && <form onSubmit={addQuestion} className="border-t border-border pt-4 grid gap-3"><div className="flex items-center justify-between"><h3 className="text-sm font-bold">Add benchmark case</h3><button type="button" onClick={() => setShowForm(false)}><X className="w-4 h-4" /></button></div><input required value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Question in natural language" className="w-full p-2.5 text-xs bg-surface-hover border border-border rounded-lg" /><textarea required value={goldSql} onChange={(e) => setGoldSql(e.target.value)} placeholder="Expected SQL (SELECT only)" rows={3} className="w-full p-2.5 text-xs font-mono bg-surface-hover border border-border rounded-lg" /><textarea value={goldAnswer} onChange={(e) => setGoldAnswer(e.target.value)} placeholder="Expected answer (optional, stored as reference)" rows={2} className="w-full p-2.5 text-xs bg-surface-hover border border-border rounded-lg" /><div className="flex justify-end"><button disabled={saving} className="px-4 py-2 text-xs font-bold rounded-lg bg-accent text-white disabled:opacity-50">{saving ? "Saving..." : "Save to Database"}</button></div></form>}
    </div>
    <div className="bg-surface border border-border rounded-xl overflow-hidden"><div className="px-5 py-3 border-b border-border text-xs font-bold">Persisted cases ({questions.length})</div><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="bg-surface-2 text-text-muted"><tr><th className="p-3">Question</th><th className="p-3">Expected SQL</th><th className="p-3">Expected Answer</th></tr></thead><tbody className="divide-y divide-border">{questions.map((item) => <tr key={item.id}><td className="p-3">{item.question}</td><td className="p-3 font-mono max-w-80 truncate">{item.gold_sql}</td><td className="p-3 max-w-64 truncate">{item.gold_answer || "—"}</td></tr>)}</tbody></table></div></div>
    <BenchmarkEvalPanel refreshKey={refreshKey} /><PipelineEvalPanel />
  </div>;
};
