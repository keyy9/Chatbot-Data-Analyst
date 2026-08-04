import React from "react";

interface VoiceWaveformProps {
  isListening: boolean;
}

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({ isListening }) => {
  if (!isListening) return null;

  return (
    <div className="flex items-center gap-1 px-3 py-1.5 bg-danger/10 border border-danger/30 rounded-full animate-fade-in font-sans">
      <span className="w-2 h-2 rounded-full bg-danger animate-ping" />
      <span className="text-[10px] font-extrabold uppercase tracking-wider text-danger mr-1">
        Listening
      </span>
      <div className="flex items-center gap-0.5 h-4">
        <span className="w-1 bg-danger rounded-full animate-[bounce_1s_infinite_100ms] h-2" />
        <span className="w-1 bg-danger rounded-full animate-[bounce_1s_infinite_300ms] h-4" />
        <span className="w-1 bg-danger rounded-full animate-[bounce_1s_infinite_200ms] h-3" />
        <span className="w-1 bg-danger rounded-full animate-[bounce_1s_infinite_400ms] h-4" />
        <span className="w-1 bg-danger rounded-full animate-[bounce_1s_infinite_150ms] h-2" />
      </div>
    </div>
  );
};
