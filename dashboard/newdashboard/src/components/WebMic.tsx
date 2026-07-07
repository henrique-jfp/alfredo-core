import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2, Volume2, MonitorSpeaker, Smartphone } from 'lucide-react';
import { cn } from '../lib/utils';

export function WebMic() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playOnServer, setPlayOnServer] = useState(false); // Default to local browser
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const isInitializingRef = useRef(false);
  const audioContextRef = useRef<AudioContext | null>(null);
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
      
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
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
          // Received TTS audio!
          cleanupEverything();
          
          if (!playOnServer) {
            const audioUrl = URL.createObjectURL(event.data);
            if (audioPlayerRef.current) {
              audioPlayerRef.current.src = audioUrl;
              setIsPlaying(true);
              audioPlayerRef.current.play();
            }
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
        stopRecording();
      };

    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Não foi possível acessar o microfone. Verifique as permissões do navegador.");
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
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsProcessing(false);
    setIsRecording(false);
    isRecordingRef.current = false;
  };

  const stopRecording = (e?: React.TouchEvent | React.MouseEvent) => {
    if (e && e.type === 'touchend') {
      if (e.cancelable) e.preventDefault();
    }
    if (isRecording) {
      setIsRecording(false);
      isRecordingRef.current = false;
      setIsProcessing(true); // Wait for TTS to come back via WS
      
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
    <div className="fixed bottom-24 md:bottom-8 right-4 md:right-8 z-50 flex items-center gap-4">
      
      {/* Toggle Output Target */}
      <button 
        onClick={() => setPlayOnServer(!playOnServer)}
        className="bg-black/60 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 flex items-center gap-2 hover:bg-white/10 transition-colors"
        title="Onde o Alfredo vai falar?"
      >
        <span className="text-xs font-semibold text-zinc-400">Responder no:</span>
        {playOnServer ? (
          <div className="flex items-center gap-1 text-brass-400 font-bold text-sm">
            <MonitorSpeaker className="w-4 h-4" /> Satélite
          </div>
        ) : (
          <div className="flex items-center gap-1 text-indigo-400 font-bold text-sm">
            <Smartphone className="w-4 h-4" /> Celular
          </div>
        )}
      </button>

      {/* Visual Indicator */}
      {(isRecording || isProcessing || isPlaying) && (
        <div className="bg-black/60 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 flex items-center gap-2 animate-in fade-in slide-in-from-right-4">
          {isRecording && <span className="text-rose-400 font-bold text-sm flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" /> Ouvindo...</span>}
          {isProcessing && <span className="text-brass-400 font-bold text-sm flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Pensando...</span>}
          {isPlaying && <span className="text-indigo-400 font-bold text-sm flex items-center gap-2"><Volume2 className="w-4 h-4 animate-pulse" /> Falando...</span>}
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
          "w-16 h-16 rounded-full flex items-center justify-center text-white shadow-2xl transition-all duration-300 shrink-0",
          isRecording ? "bg-rose-600 scale-110 shadow-[0_0_30px_rgba(225,29,72,0.5)]" : 
          isProcessing ? "bg-brass-600 cursor-not-allowed" :
          isPlaying ? "bg-indigo-600 shadow-[0_0_30px_rgba(79,70,229,0.5)]" :
          "bg-gradient-to-br from-[#1428A0] to-[#0D1B6E] hover:scale-105 hover:shadow-[0_0_20px_rgba(20,40,160,0.4)]"
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
