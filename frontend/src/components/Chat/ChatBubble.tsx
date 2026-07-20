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
import { useSpeechStore } from "../../store/speechStore";

interface ChatBubbleProps {
  message: Message;
  /** The user's question this answer responds to (a separate, preceding
   *  message - `Message` itself carries no question field). Only needed
   *  for export; omit on messages with no exportable result. */
  questionText?: string;
  /** Handles a clarification option pick. Omit if this surface never produces clarification messages. */
  onClarificationSelect?: (option: string) => void;
  /** Confirms and executes a proposed write. CRUD-only - only ever wired by the admin surface,
   *  since `pendingConfirmation` is only ever populated for admin-generated write proposals. */
  onConfirmWrite?: (messageId: string, token: string) => void;
  /** Triggers a per-query comparison of both models for this question. Only rendered on user messages. */
  onCompare?: (questionText: string) => void;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  questionText,
  onClarificationSelect,
  onConfirmWrite,
  onCompare
}) => {
  const isUser = message.sender === "user";
  const isBlocked = message.status === "Blocked";
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const hasExportableResult = !isUser && !!message.resultPreview && message.resultPreview.rows.length > 0;

  const { isSupported: ttsSupported, speakingId, speak } = useSpeechStore();
  const isSpeaking = speakingId === message.id;

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
          <div className="p-3 border border-warning/25 bg-warning/10 rounded-lg space-y-2 font-sans">
            <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-warning">
              <AlertCircle className="w-3.5 h-3.5" />
              {message.pendingConfirmation.resolved === "confirmed"
                ? "Write executed"
                : `Confirm ${message.pendingConfirmation.operation.toUpperCase()} before it runs`}
            </div>
            {message.pendingConfirmation.resolved !== "confirmed" && onConfirmWrite && (
              <button
                type="button"
                onClick={() => onConfirmWrite(message.id, message.pendingConfirmation!.token)}
                className="px-3 py-1.5 bg-warning hover:opacity-90 text-bg text-xs font-extrabold uppercase tracking-wide rounded-lg transition-all cursor-pointer"
              >
                Confirm &amp; Execute
              </button>
            )}
          </div>
        )}

        {/* Results grid preview */}
        {!isUser && message.resultPreview && (
          <TableChart columns={message.resultPreview.columns} rows={message.resultPreview.rows} />
        )}

        {/* Auto charts visual representation */}
        {!isUser && message.chartData && (
          <div ref={chartContainerRef} className="space-y-1 pt-1">
            <span className="text-[10px] font-extrabold uppercase text-text-muted tracking-wider font-mono">
              Auto-Generated {message.chartData.type} view
            </span>
            {message.chartData.type === "bar" && (
              <BarChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {message.chartData.type === "line" && (
              <LineChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {message.chartData.type === "pie" && (
              <PieChart
                data={message.chartData.data}
                xAxisKey={message.chartData.xAxisKey}
                dataKeys={message.chartData.dataKeys}
              />
            )}
            {message.chartData.type === "area" && (
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

        {/* Per-answer export controls - hidden for clarification/blocked/no-result answers */}
        {hasExportableResult && message.resultPreview && (
          <ExportButtons
            questionText={questionText || message.text}
            explanationText={message.text}
            sql={message.sql}
            columns={message.resultPreview.columns}
            rows={message.resultPreview.rows}
            chartElementRef={chartContainerRef}
          />
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
