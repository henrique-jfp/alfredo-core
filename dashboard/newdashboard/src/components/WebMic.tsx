import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2, Volume2, MonitorSpeaker, Smartphone } from 'lucide-react';
import { cn } from '../lib/utils';

export function WebMic() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playOnServer, setPlayOnServer] = useState(true); // Default to server (satellite)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const isInitializingRef = useRef(false);

  const startRecording = async (e?: React.TouchEvent | React.MouseEvent) => {
    if (e && e.type === 'touchstart') {
      // Prevent synthetic mouse events on mobile
      if (e.cancelable) e.preventDefault();
    }
    
    if (isRecording || isInitializingRef.current) return;
    
    try {
      isInitializingRef.current = true;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = handleAudioStop;
      
      mediaRecorder.start(250);
      setIsRecording(true);
      isInitializingRef.current = false;
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Não foi possível acessar o microfone. Verifique as permissões do navegador.");
      isInitializingRef.current = false;
    }
  };

  const stopRecording = (e?: React.TouchEvent | React.MouseEvent) => {
    if (e && e.type === 'touchend') {
      if (e.cancelable) e.preventDefault();
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsProcessing(true);
    }
  };

  const handleAudioStop = async () => {
    // Stop tracks safely after recording stops
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('file', audioBlob, 'voice.webm');

    try {
      // 1. Transcribe the audio
      const transcribeRes = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: formData,
      });
      
      if (!transcribeRes.ok) throw new Error('Transcription failed');
      const transcribeData = await transcribeRes.json();
      const text = transcribeData.text;

      if (!text || text.trim() === '') {
        setIsProcessing(false);
        return; // Empty speech
      }

      // 2. Send text to agent and get TTS audio back
      const commandRes = await fetch('/api/voice/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, device_id: 'web-dashboard', play_locally: playOnServer })
      });

      if (!commandRes.ok) throw new Error('Command execution failed');
      
      // 3. Play the returned audio if not played on server
      if (!playOnServer) {
        const responseBlob = await commandRes.blob();
        const audioUrl = URL.createObjectURL(responseBlob);
        
        if (audioPlayerRef.current) {
          audioPlayerRef.current.src = audioUrl;
          setIsPlaying(true);
          audioPlayerRef.current.play();
        }
      }
      
    } catch (error) {
      console.error("Error processing voice command:", error);
    } finally {
      setIsProcessing(false);
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
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        onMouseLeave={stopRecording}
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
