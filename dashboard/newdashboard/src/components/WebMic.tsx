import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2, Volume2, MonitorSpeaker, Smartphone } from 'lucide-react';
import { cn } from '../lib/utils';
import { StatusPulse } from './ui/DashboardPrimitives';

/** Dispatch a custom event so useAlfredoState (and the AlfredoOrb) stays in sync */
function emitAlfredoEvent(type: string) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(type));
  }
}

export function WebMic() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playOnServer, setPlayOnServer] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const isInitializingRef = useRef(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const isRecordingRef = useRef(false); // For sync in callbacks

  const startRecording = async (e?: React.TouchEvent | React.MouseEvent) => {
    if (e && e.type === 'touchstart') {
      if (e.cancelable) e.preventDefault();
    }
    
    if (isRecording || isInitializingRef.current) return;
    
    try {
      isInitializingRef.current = true;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host; // This handles dev servers and production
      // In dev mode (vite), proxy will forward to backend. Wait, Vite proxy handles ws?
      // Actually, standard proxy does. We will use the standard host.
      const wsUrl = `${protocol}//${host}/api/ws/satellite/dashboard-virtual-mic`;
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "blob";
      wsRef.current = ws;

      ws.onopen = () => {
        setIsRecording(true);
        isRecordingRef.current = true;
        isInitializingRef.current = false;
        emitAlfredoEvent('alfredo:mic:start');
        
        processor.onaudioprocess = (e) => {
          if (!isRecordingRef.current) return;
          const inputData = e.inputBuffer.getChannelData(0);
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            let s = Math.max(-1, Math.min(1, inputData[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(pcmData.buffer);
          }
        };
        source.connect(processor);
        processor.connect(audioContext.destination);
      };

      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          // Received TTS audio. Stop capture, but keep the playback context
          // alive until the response finishes.
          stopCapture();
          emitAlfredoEvent('alfredo:mic:response');

          try {
            setIsPlaying(true);
            const blobUrl = URL.createObjectURL(event.data);

            if (audioPlayerRef.current) {
              audioPlayerRef.current.src = blobUrl;
              await audioPlayerRef.current.play();
              audioPlayerRef.current.onended = () => {
                URL.revokeObjectURL(blobUrl);
                setIsPlaying(false);
                emitAlfredoEvent('alfredo:mic:done');
                cleanupAfterPlayback();
              };
            } else {
              const playbackContext = playbackContextRef.current ?? new AudioCtx();
              playbackContextRef.current = playbackContext;
              const arrayBuffer = await event.data.arrayBuffer();
              const audioBuffer = await playbackContext.decodeAudioData(arrayBuffer.slice(0));
              const playSource = playbackContext.createBufferSource();
              playSource.buffer = audioBuffer;
              playSource.connect(playbackContext.destination);
              playSource.onended = () => {
                setIsPlaying(false);
                emitAlfredoEvent('alfredo:mic:done');
                cleanupAfterPlayback();
              };
              playSource.start();
            }
          } catch (err) {
            console.error("Erro ao tocar áudio", err);
            setIsPlaying(false);
            cleanupAfterPlayback();
          }
        } else if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'play_audio' && data.url) {
              const bgAudio = new Audio(data.url);
              bgAudio.play().catch(e => console.error("Error playing background audio:", e));
            }
          } catch (e) {
            console.error("Erro ao fazer parse do WS JSON:", e);
          }
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        emitAlfredoEvent('alfredo:mic:error');
        stopRecording();
      };

    } catch (error) {
      console.error("Error accessing microphone:", error);
      emitAlfredoEvent('alfredo:mic:error');
      setMicError("Microfone não disponível. Verifique as permissões.");
      setTimeout(() => setMicError(null), 5000);
      isInitializingRef.current = false;
    }
  };

  const cleanupEverything = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsProcessing(false);
    setIsRecording(false);
    isRecordingRef.current = false;
    emitAlfredoEvent('alfredo:mic:done');
  };

  const stopCapture = () => {
    if (isRecordingRef.current) {
      setIsRecording(false);
      isRecordingRef.current = false;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsProcessing(true);
  };

  const cleanupAfterPlayback = () => {
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }
    setIsProcessing(false);
  };

  const stopRecording = (e?: React.TouchEvent | React.MouseEvent) => {
    if (e && e.type === 'touchend') {
      if (e.cancelable) e.preventDefault();
    }
      if (isRecording) {
        setIsRecording(false);
        isRecordingRef.current = false;
        setIsProcessing(true); // Wait for TTS to come back via WS
        emitAlfredoEvent('alfredo:mic:stop');

      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      // DO NOT close WS yet! We need to receive the TTS audio!
      setTimeout(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
          wsRef.current = null;
        }
        setIsProcessing(false);
      }, 10000); // 10s max wait time
    }
  };

  return (
    <div className="fixed bottom-24 right-4 z-50 flex items-center gap-3 md:bottom-8 md:right-8">
      
      {micError && (
        <div className="absolute bottom-20 right-0 alfredo-card whitespace-nowrap px-4 py-3 text-[13px] text-rose-400 border-rose-500/20 shadow-[0_0_24px_rgba(248,113,113,0.18)]">
          {micError}
        </div>
      )}

      {/* Toggle Output Target */}
      <button 
        onClick={() => setPlayOnServer(!playOnServer)}
        className="alfredo-card flex items-center gap-2 rounded-full px-4 py-2 text-[13px] text-[color:var(--text-secondary)] transition-colors hover:border-brass-500/20 hover:bg-white/[0.04]"
        title="Onde o Alfredo vai falar?"
      >
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">Responder no</span>
        {playOnServer ? (
          <div className="flex items-center gap-1 text-sm font-semibold text-brass-300">
            <MonitorSpeaker className="w-4 h-4" /> Satélite
          </div>
        ) : (
          <div className="flex items-center gap-1 text-sm font-semibold text-blue-400">
            <Smartphone className="w-4 h-4" /> Celular
          </div>
        )}
      </button>

      {/* Visual Indicator */}
      {(isRecording || isProcessing || isPlaying) && (
        <div className="alfredo-card flex items-center gap-2 rounded-full px-4 py-2">
          {isRecording && <StatusPulse label="Ouvindo" tone="danger" />}
          {isProcessing && (
            <span className="alfredo-pill border-brass-500/20 bg-brass-500/10 text-brass-300">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Pensando
            </span>
          )}
          {isPlaying && <StatusPulse label="Falando" tone="info" icon={Volume2} />}
        </div>
      )}

      {/* Main Button */}
      <button
        onClick={() => {
          if (isRecording) {
            stopRecording();
          } else {
            startRecording();
          }
        }}
        disabled={isProcessing || isPlaying}
        className={cn(
          "flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-white transition-all duration-300",
          isRecording
            ? "bg-rose-600 shadow-[0_0_30px_rgba(225,29,72,0.42)] scale-110"
            : isProcessing
            ? "bg-brass-600 cursor-not-allowed"
            : isPlaying
            ? "bg-blue-600 shadow-[0_0_30px_rgba(59,130,246,0.35)]"
            : "bg-gradient-to-br from-brass-400 to-brass-600 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.22)] hover:scale-105"
        )}
      >
        {isRecording ? (
          <Square className="w-6 h-6 fill-current" />
        ) : isProcessing ? (
          <Loader2 className="w-6 h-6 animate-spin" />
        ) : isPlaying ? (
          <Volume2 className="w-6 h-6 animate-pulse" />
        ) : (
          <Mic className="w-6 h-6" />
        )}
      </button>

      {/* Hidden Audio Player */}
      <audio 
        ref={audioPlayerRef} 
        onEnded={() => setIsPlaying(false)}
        className="hidden" 
      />
    </div>
  );
}
