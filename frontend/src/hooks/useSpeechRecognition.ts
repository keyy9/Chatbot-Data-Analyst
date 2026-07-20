import { useCallback, useEffect, useRef, useState } from "react";

export type SpeechRecognitionErrorKind = "denied" | "no-speech" | "network" | "unsupported" | "other";

interface UseSpeechRecognitionOptions {
  /** Called with the finalized transcript chunk once the browser is confident in it. */
  onResult?: (transcript: string) => void;
  lang?: string;
}

/** Minimal shape of the non-standard SpeechRecognition API - not part of lib.dom.d.ts. */
interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
}

const getRecognitionCtor = (): (new () => SpeechRecognitionLike) | null => {
  if (typeof window === "undefined") return null;
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
};

/**
 * Wraps the browser's native Web Speech API (SpeechRecognition) for
 * dictating text into an input. No backend/API key involved - runs
 * fully client-side (Chrome/Edge/Safari route it through their own
 * speech service; Firefox has no implementation, hence isSupported).
 */
export function useSpeechRecognition({ onResult, lang = "en-US" }: UseSpeechRecognitionOptions = {}) {
  const isSupported = getRecognitionCtor() !== null;
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<SpeechRecognitionErrorKind | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setError("unsupported");
      return;
    }

    setError(null);
    setInterimTranscript("");

    const recognition = new Ctor();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onresult = (event: any) => {
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText += result[0].transcript;
        }
      }
      if (interimText) setInterimTranscript(interimText);
      if (finalText.trim()) {
        onResultRef.current?.(finalText.trim());
        setInterimTranscript("");
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed" || event.error === "permission-denied") {
        setError("denied");
      } else if (event.error === "no-speech") {
        setError("no-speech");
      } else if (event.error === "network") {
        setError("network");
      } else {
        setError("other");
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  }, [lang]);

  const toggle = useCallback(() => {
    if (isListening) {
      stop();
    } else {
      start();
    }
  }, [isListening, start, stop]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  return {
    isSupported,
    isListening,
    interimTranscript,
    error,
    start,
    stop,
    toggle,
    resetError: () => setError(null),
  };
}
