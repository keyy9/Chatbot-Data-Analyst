import React, { useRef } from "react";
import { Sparkles, ShieldAlert, CheckCircle, AlertCircle, Scale, Volume2, Square } from "lucide-react";
import type { Message } from "../../types";
import { SQLToggle } from "./SQLToggle";
import { TableChart } from "../Charts/TableChart";
import { BarChart } from "../Charts/BarChart";
import { LineChart } from "../Charts/LineChart";
import { PieChart } from "../Charts/PieChart";
import { AreaChart } from "../Charts/AreaChart";
import { ClarificationCard } from "./ClarificationCard";
import { ExportButtons } from "./ExportButtons";
import { InsightsCard } from "./InsightsCard";
import { useSpeechStore } from "../../store/speechStore";

interface ChatBubbleProps {
  message: Message;
  /** The user's question this answer responds to (a separate, preceding
   *  message - `Message` itself carries no question field). Only needed
   *  for export; omit on messages with no exportable result. */
  questionText?: string;
  /** Handles a clarification option pick. Omit if this surface never produces clarification messages. */
  onClarificationSelect?: (option: string) => void;
  /** Handles clicking a suggested follow-up question chip. */
  onSuggestedSelect?: (question: string) => void;
  /** Confirms and executes a proposed write. CRUD-only - only ever wired by the admin surface,
   *  since `pendingConfirmation` is only ever populated for admin-generated write proposals. */
  onConfirmWrite?: (messageId: string, token: string) => void;
  /** Triggers a per-query comparison of both models for this question. Only rendered on user messages. */
  onCompare?: (questionText: string) => void;
  hideSaveObservation?: boolean;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  questionText,
  onClarificationSelect,
  onSuggestedSelect,
  onConfirmWrite,
  onCompare,
  hideSaveObservation = false
}) => {
  const isUser = message.sender === "user";
  const isBlocked = message.status === "Blocked";
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const hasExportableResult = !isUser && !!message.resultPreview && message.resultPreview.rows.length > 0;

  const { isSupported: ttsSupported, speakingId, speak } = useSpeechStore();
  const isSpeaking = speakingId === message.id;
  const [activeChartType, setActiveChartType] = React.useState<"bar" | "line" | "pie" | "area">(
    message.chartData?.type || "bar"
  );

  return (
    <div className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"} font-sans`}>
      {/* AI Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-teal/15 border border-teal/30 flex items-center justify-center shadow-sm flex-shrink-0">
          <Sparkles className="w-4 h-4 text-teal" />
        </div>
      )}

      {/* Bubble Panel */}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-accent text-white rounded-tr-none font-semibold text-left"
            : isBlocked
            ? "bg-danger/10 border border-danger/20 text-danger rounded-tl-none space-y-3 w-full max-w-lg text-left"
            : "bg-surface-2 border border-border text-text rounded-tl-none space-y-3 w-full max-w-xl text-left"
        }`}
      >
        {/* Header information */}
        <div className="flex items-center justify-between mb-1.5 opacity-80 gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[10px] font-bold uppercase tracking-wider flex-shrink-0 text-accent">
              {isUser ? "You" : "Lapis Analyst"}
            </span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {!isUser && ttsSupported && message.text && (
              <button
                type="button"
                onClick={() => speak(message.id, message.text)}
                title={isSpeaking ? "Stop reading aloud" : "Read aloud"}
                className={`p-1 rounded-full transition-colors cursor-pointer ${
                  isSpeaking ? "text-accent" : "text-text-faint hover:text-accent"
                }`}
              >
                {isSpeaking ? <Square className="w-3 h-3 fill-current" /> : <Volume2 className="w-3 h-3" />}
              </button>
            )}
            <span className="text-[9px] font-mono">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>

        {/* Text Body */}
        <p className="whitespace-pre-wrap leading-normal font-semibold">{message.text}</p>

        {/* Per-query model comparison trigger - user questions only */}
        {isUser && onCompare && (
          <button
            type="button"
            onClick={() => onCompare(message.text)}
            className="mt-1.5 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-white/80 hover:text-white transition-colors cursor-pointer"
          >
            <Scale className="w-3 h-3" />
            Compare Both Models
          </button>
        )}

        {/* Guardrail badge indicator */}
        {isBlocked && (
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-danger/10 border border-danger/30 text-danger text-xs font-bold rounded-lg mt-2 font-sans animate-pulse">
            <ShieldAlert className="w-3.5 h-3.5" />
            Blocked Status: Read-Only Guardrail Triggered
          </div>
        )}

        {/* Operation status banner (e.g. write execution result). Only ever
            populated by the admin write flow - naturally absent on user chat. */}
        {!isUser && message.message && (
          <div
            className={`p-2.5 border rounded-lg flex flex-col gap-1 mt-2 font-sans ${
              message.status === "Failed"
                ? "bg-danger/10 border-danger/20 text-danger"
                : "bg-success/10 border-success/20 text-success"
            }`}
          >
            <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide">
              {message.status === "Failed" ? (
                <>
                  <AlertCircle className="w-3.5 h-3.5" />
                  Operation Failed
                </>
              ) : (
                <>
                  <CheckCircle className="w-3.5 h-3.5" />
                  Operation Successful
                </>
              )}
            </div>
            <span className="text-xs font-mono opacity-90 block">{message.message}</span>
          </div>
        )}

        {/* SQL dialect toggle */}
        {!isUser && message.sql && (
          <SQLToggle sql={message.sql} executionTimeMs={message.executionTimeMs} rowCount={message.rowCount} />
        )}

        {/* Pending write confirmation. CRUD-only: pendingConfirmation is only ever
            populated for admin-generated write proposals. */}
        {!isUser && message.pendingConfirmation && (
          <div className="p-3.5 border border-warning/35 bg-warning/10 rounded-xl space-y-2.5 font-sans my-2">
            <div className="flex items-center justify-between text-xs font-extrabold uppercase tracking-wide text-warning">
              <span className="flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                {message.pendingConfirmation.resolved === "confirmed"
                  ? `${message.pendingConfirmation.operation.toUpperCase()} Operation Executed`
                  : `Confirm ${message.pendingConfirmation.operation.toUpperCase()} Operation`}
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-warning/20 text-warning font-bold">
                {message.pendingConfirmation.resolved === "confirmed" ? "EXECUTED" : "ACTION REQUIRED"}
              </span>
            </div>

            {message.pendingConfirmation.resolved !== "confirmed" && (
              <p className="text-xs text-text font-semibold">
                Please review the proposed SQL statement below before executing against the database:
              </p>
            )}

            {/* SQL Code Preview Block */}
            <div className="p-2.5 bg-surface/90 border border-border rounded-lg text-xs font-mono text-text space-y-1">
              <div className="text-[10px] text-text-muted uppercase font-bold tracking-wider">Target SQL Statement:</div>
              <div className="text-accent font-bold break-all bg-surface-2/80 p-2 rounded border border-border/50">
                <code>{message.pendingConfirmation.sqlPreview || message.sql || "SQL proposal generated"}</code>
              </div>
            </div>

            {message.pendingConfirmation.resolved !== "confirmed" && onConfirmWrite && (
              <div className="pt-1 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onConfirmWrite(message.id, message.pendingConfirmation!.token)}
                  className="px-4 py-2 bg-warning hover:opacity-90 text-slate-950 font-extrabold text-xs uppercase tracking-wide rounded-lg transition-all shadow-md cursor-pointer flex items-center gap-1.5 active:scale-95"
                >
                  <CheckCircle className="w-4 h-4" />
                  Confirm &amp; Execute {message.pendingConfirmation.operation.toUpperCase()}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Results grid preview */}
        {!isUser && message.resultPreview && (
          <TableChart columns={message.resultPreview.columns} rows={message.resultPreview.rows} />
        )}

        {/* Auto charts visual representation with interactive switcher */}
        {!isUser && message.chartData && (
          <div ref={chartContainerRef} className="space-y-2 pt-1 font-sans">
            <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
              <span className="text-[10px] font-extrabold uppercase text-text-muted tracking-wider font-mono">
                Visual View: {activeChartType.toUpperCase()}
              </span>
              <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-0.5 shadow-2xs">
                <button
                  type="button"
                  onClick={() => setActiveChartType("bar")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    activeChartType === "bar" ? "bg-accent text-white shadow-xs" : "text-text-muted hover:text-text"
                  }`}
                  title="Bar Chart View"
                >
                  📊 Bar
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChartType("line")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    activeChartType === "line" ? "bg-accent text-white shadow-xs" : "text-text-muted hover:text-text"
                  }`}
                  title="Line Chart View"
                >
                  📈 Line
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChartType("area")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    activeChartType === "area" ? "bg-accent text-white shadow-xs" : "text-text-muted hover:text-text"
                  }`}
                  title="Area Chart View"
                >
                  ⛰️ Area
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChartType("pie")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    activeChartType === "pie" ? "bg-accent text-white shadow-xs" : "text-text-muted hover:text-text"
                  }`}
                  title="Pie Chart View"
                >
                  🥧 Pie
                </button>
              </div>
            </div>

            {activeChartType === "bar" && (
              <BarChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {activeChartType === "line" && (
              <LineChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {activeChartType === "pie" && (
              <PieChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {activeChartType === "area" && (
              <AreaChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
          </div>
        )}

        {/* Clarification prompt card */}
        {!isUser && message.isClarification && message.clarificationOptions && onClarificationSelect && (
          <ClarificationCard options={message.clarificationOptions} onSelect={onClarificationSelect} />
        )}

        {/* AI Executive Summary & Trend Insights */}
        {!isUser && !message.isClarification && (
          <InsightsCard insights={message.insights} resultPreview={message.resultPreview} />
        )}

        {/* Per-answer export controls - hidden for clarification/blocked/no-result answers */}
        {hasExportableResult && message.resultPreview && (
          <ExportButtons
            questionText={questionText || message.text}
            explanationText={message.text}
            sql={message.sql}
            columns={message.resultPreview.columns}
            rows={message.resultPreview.rows}
            chartElementRef={chartContainerRef}
            hideSaveObservation={hideSaveObservation}
          />
        )}

        {/* Suggested Follow-up Questions Chips */}
        {!isUser && message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
          <div className="pt-2 border-t border-border/50 space-y-1.5 font-sans">
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
              Suggested Follow-ups
            </span>
            <div className="flex flex-wrap gap-1.5">
              {message.suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    if (onSuggestedSelect) onSuggestedSelect(q);
                    else if (onClarificationSelect) onClarificationSelect(q);
                  }}
                  className="text-xs font-semibold px-2.5 py-1.5 rounded-xl bg-surface hover:bg-accent hover:text-white border border-border transition-all cursor-pointer text-left shadow-sm flex items-center gap-1 active:scale-[0.98]"
                >
                  <span className="text-accent hover:text-white font-bold">➔</span> {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent to-teal text-white font-extrabold flex items-center justify-center shadow-md flex-shrink-0 text-xs font-mono">
          U
        </div>
      )}
    </div>
  );
};
