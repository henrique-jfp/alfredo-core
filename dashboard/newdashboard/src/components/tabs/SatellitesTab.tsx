import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { Satellite } from '../../types';
import { Cpu, Power, Volume2, Sun, Mic, Radio, Zap, Volume1, Lightbulb, Activity } from 'lucide-react';
import { cn } from '../../lib/utils';

export function SatellitesTab() {
  const [satellites, setSatellites] = useState<Satellite[]>([]);
  const [selectedSat, setSelectedSat] = useState<Satellite | null>(null);
  
  // WebSocket and Audio states
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Local state for sliders (optimistic updates)
  const [volume, setVolume] = useState(70);
  const [brightness, setBrightness] = useState(50);
  const [alsaCapture, setAlsaCapture] = useState(100);
  const [alsaMaster, setAlsaMaster] = useState(100);
  const [softwarePreamp, setSoftwarePreamp] = useState(1.0);

  useEffect(() => {
    api.getSatellites().then(data => {
      setSatellites(data);
      if (data.length > 0) {
        setSelectedSat(data[0]);
        setVolume(data[0].volume ?? 70);
        setBrightness(data[0].brightness ?? 50);
      }
    });

    // Initialize WebSocket connection to dashboard
    const host = window.location.hostname;
    // Assume backend is on port 10001 (or same port if proxied)
    const wsUrl = `ws://${host}:10001/api/ws/dashboard`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Connected to dashboard WebSocket");
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log("Disconnected from dashboard WebSocket");
      setIsConnected(false);
    };

    ws.onmessage = async (event) => {
      // Audio chunks arrive as binary data
      if (event.data instanceof Blob && audioCtxRef.current) {
        const arrayBuffer = await event.data.arrayBuffer();
        
        // Basic PCM playback (Assuming 16-bit PCM, 16kHz, Mono)
        // If it's a WAV, we could use decodeAudioData, but for raw PCM we construct the buffer:
        try {
          const audioCtx = audioCtxRef.current;
          // Note: In a real scenario, you'd buffer chunks smoothly. This is a naive playback for POC.
          const view = new Int16Array(arrayBuffer);
          const audioBuffer = audioCtx.createBuffer(1, view.length, 16000);
          const channelData = audioBuffer.getChannelData(0);
          for (let i = 0; i < view.length; i++) {
            channelData[i] = view[i] / 32768.0; // convert int16 to float32
          }
          const source = audioCtx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioCtx.destination);
          source.start();
        } catch (e) {
          console.error("Audio playback error:", e);
        }
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close();
      }
    };
  }, []);

  // Update local sliders when selecting a different satellite
  useEffect(() => {
    if (selectedSat) {
      setVolume(selectedSat.volume ?? 70);
      setBrightness(selectedSat.brightness ?? 50);
    }
  }, [selectedSat?.device_id]);

  const sendCommand = (cmd: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && selectedSat) {
      wsRef.current.send(`${cmd}:${selectedSat.device_id}`);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value);
    setVolume(val);
  };
  
  const handleVolumeCommit = () => {
    if (wsRef.current && selectedSat) {
      wsRef.current.send(`SET_VOLUME:${selectedSat.device_id}:${volume}`);
    }
  };

  const handleBrightnessChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value);
    setBrightness(val);
  };

  const handleBrightnessCommit = () => {
    if (wsRef.current && selectedSat) {
      wsRef.current.send(`SET_BRIGHTNESS:${selectedSat.device_id}:${brightness}`);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
      sendCommand("STOP_STREAM");
    } else {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      if (audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume();
      }
      setIsListening(true);
      sendCommand("START_STREAM");
    }
  };

  const handleAlsaCaptureCommit = () => {
    if (wsRef.current && selectedSat) {
      wsRef.current.send(`SET_ALSA_CAPTURE:${selectedSat.device_id}:${alsaCapture}`);
    }
  };

  const handleAlsaMasterCommit = () => {
    if (wsRef.current && selectedSat) {
      wsRef.current.send(`SET_ALSA_MASTER:${selectedSat.device_id}:${alsaMaster}`);
    }
  };

  const handleSoftwarePreampCommit = () => {
    if (wsRef.current && selectedSat) {
      wsRef.current.send(`SET_SOFTWARE_PREAMP:${selectedSat.device_id}:${softwarePreamp}`);
    }
  };

  const parseCapabilities = (capStr: string) => {
    try {
      return JSON.parse(capStr) as string[];
    } catch {
      return [];
    }
  };

  const capIcons: Record<string, { icon: any, label: string, color: string }> = {
    'mic': { icon: Mic, label: 'Microfone I2S', color: 'text-indigo-400 border-indigo-400/20 bg-indigo-400/10' },
    'speaker': { icon: Volume1, label: 'Alto-Falante', color: 'text-rose-400 border-rose-400/20 bg-rose-400/10' },
    'led': { icon: Lightbulb, label: 'Matriz LED', color: 'text-yellow-400 border-yellow-400/20 bg-yellow-400/10' },
    'display': { icon: Activity, label: 'Display OLED', color: 'text-teal-400 border-teal-400/20 bg-teal-400/10' }
  };

  return (
    <div className="flex gap-6 h-full pb-10">
      
      {/* List */}
      <div className="w-1/2 glass-panel p-6 flex flex-col min-h-0 relative overflow-hidden">
        {/* Status Indicator */}
        <div className="absolute top-4 right-4 flex items-center gap-2 text-xs font-bold text-zinc-500">
          WS: {isConnected ? <span className="text-emerald-400">● Conectado</span> : <span className="text-rose-400">○ Desconectado</span>}
        </div>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-[16px] font-semibold text-zinc-100 mb-2">Frota de Satélites</h2>
            <p className="text-zinc-500 text-[13px]">Selecione um dispositivo para acessar telemetria e áudio.</p>
          </div>
          <button 
            onClick={() => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                satellites.forEach(sat => {
                  wsRef.current?.send(`SET_VOLUME:${sat.device_id}:0`);
                });
                setVolume(0);
              }
            }}
            className="flex items-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-bold rounded-lg transition-colors"
          >
            Mutar Todos
          </button>
        </div>
        
        <div className="flex flex-col gap-3 overflow-y-auto custom-scrollbar pr-2 flex-grow">
          {satellites.map(sat => (
            <button 
              key={sat.device_id}
              onClick={() => setSelectedSat(sat)}
              className={cn(
                "flex flex-col p-4 rounded-xl border text-left transition-all relative overflow-hidden group",
                selectedSat?.device_id === sat.device_id 
                  ? "bg-white/10 border-brass-500/40 shadow-[0_0_20px_rgba(201,162,75,0.1)]" 
                  : "bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10"
              )}
            >
              <div className="flex justify-between items-start w-full">
                <span className="text-[15px] font-semibold text-zinc-100">{sat.hardware}</span>
                <span className={cn("text-[11px] font-bold tracking-wider px-2 py-1 rounded-full", sat.is_online ? "bg-emerald-500/10 text-emerald-400" : "bg-zinc-500/10 text-zinc-400")}>
                  {sat.is_online ? '● ONLINE' : '○ OFFLINE'}
                </span>
              </div>
              <div className="flex justify-between w-full text-[12px] text-zinc-500 mt-2">
                <span>Cômodo: {sat.room_id}</span>
                <span className="font-mono">ID: {sat.device_id.split('-')[0]}</span>
              </div>
              {/* Signal strength simulation bar */}
              {sat.is_online && (
                <div className="absolute bottom-0 left-0 h-[2px] bg-emerald-500/50 w-full group-hover:bg-emerald-400 transition-colors" style={{ width: `${Math.random() * 40 + 60}%` }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Details Panel */}
      <div className={cn("w-1/2 glass-panel p-8 flex flex-col transition-opacity duration-300 overflow-y-auto custom-scrollbar min-h-0", !selectedSat ? "opacity-50 pointer-events-none" : "")}>
        {selectedSat && (
          <>
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-brass-300 mb-2">{selectedSat.hardware}</h2>
                <div className="flex gap-2">
                  <span className={cn("text-[11px] px-3 py-1 rounded-full font-bold tracking-wide border", selectedSat.is_online ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20")}>
                    {selectedSat.is_online ? '● Online (WebSockets)' : '○ Offline (HTTP)'}
                  </span>
                  {selectedSat.is_online && (
                    <span className="text-[11px] px-3 py-1 rounded-full font-bold tracking-wide border bg-blue-500/10 text-blue-400 border-blue-500/20 flex items-center gap-1">
                      <Radio className="w-3 h-3" /> -62 dBm
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => sendCommand("OTA_UPDATE")}
                  title="Atualização OTA"
                  className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 hover:border-brass-500/50 hover:text-brass-400 flex items-center justify-center text-zinc-400 transition-colors"
                >
                  <Zap className="w-5 h-5" />
                </button>
                <button 
                  onClick={() => sendCommand("IDENTIFY")}
                  title="Localizar Satélite (Ping)"
                  className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 hover:border-brass-500/50 hover:text-brass-400 flex items-center justify-center text-zinc-400 transition-colors"
                >
                  <Radio className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Capabilities Tags */}
            <div className="flex flex-wrap gap-2 mb-6">
              {parseCapabilities(selectedSat.capabilities).map(cap => {
                const spec = capIcons[cap];
                if (!spec) return null;
                const Icon = spec.icon;
                return (
                  <div key={cap} className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-bold uppercase tracking-wider", spec.color)}>
                    <Icon className="w-3.5 h-3.5" />
                    {spec.label}
                  </div>
                );
              })}
              {parseCapabilities(selectedSat.capabilities).length === 0 && (
                <div className="text-[11px] text-zinc-500 font-bold border border-white/10 px-3 py-1.5 rounded-lg">HARDWARE BÁSICO</div>
              )}
            </div>

            <div className="bg-black/20 rounded-xl p-5 mb-8 grid grid-cols-2 gap-y-4 gap-x-6 text-[13px] border border-white/[0.03]">
              <div className="flex flex-col gap-1">
                <span className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Hardware</span>
                <span className="text-zinc-200">{selectedSat.hardware}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Firmware</span>
                <span className="text-zinc-200">{selectedSat.firmware_version}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">ID</span>
                <span className="text-zinc-200 font-mono">{selectedSat.device_id}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Cômodo</span>
                <span className="text-zinc-200">{selectedSat.room_id}</span>
              </div>
            </div>

            <div className="flex flex-col gap-6 mb-8">
              <h3 className="text-[13px] font-semibold text-zinc-100 border-b border-white/5 pb-2 uppercase tracking-widest">Ajustes Remotos (Básicos)</h3>
              
              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[13px] text-zinc-300">
                  <span className="flex items-center gap-2"><Volume2 className="w-4 h-4 text-brass-400"/> Volume</span>
                  <span className="font-mono text-brass-400 font-bold">{volume}%</span>
                </div>
                <input 
                  type="range" min="0" max="100" 
                  value={volume} 
                  onChange={handleVolumeChange}
                  onMouseUp={handleVolumeCommit}
                  onTouchEnd={handleVolumeCommit}
                  className="w-full accent-brass-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                />
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[13px] text-zinc-300">
                  <span className="flex items-center gap-2"><Sun className="w-4 h-4 text-brass-400"/> Brilho do LED</span>
                  <span className="font-mono text-brass-400 font-bold">{brightness}%</span>
                </div>
                <input 
                  type="range" min="0" max="100" 
                  value={brightness} 
                  onChange={handleBrightnessChange}
                  onMouseUp={handleBrightnessCommit}
                  onTouchEnd={handleBrightnessCommit}
                  className="w-full accent-brass-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                />
              </div>
            </div>

            <div className="flex flex-col gap-6 mb-8 bg-zinc-900/50 p-5 rounded-2xl border border-rose-500/10">
              <h3 className="text-[13px] font-semibold text-rose-400 border-b border-rose-500/10 pb-2 uppercase tracking-widest flex items-center gap-2">
                <Activity className="w-4 h-4" /> Mixer de Áudio Avançado (Depuração)
              </h3>
              
              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[13px] text-zinc-300">
                  <span className="flex items-center gap-2">ALSA Microfone (Capture)</span>
                  <span className="font-mono text-rose-400 font-bold">{alsaCapture}%</span>
                </div>
                <input 
                  type="range" min="0" max="100" 
                  value={alsaCapture} 
                  onChange={(e) => setAlsaCapture(parseInt(e.target.value))}
                  onMouseUp={handleAlsaCaptureCommit}
                  onTouchEnd={handleAlsaCaptureCommit}
                  className="w-full accent-rose-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                />
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[13px] text-zinc-300">
                  <span className="flex items-center gap-2">ALSA Alto-Falante (Master)</span>
                  <span className="font-mono text-rose-400 font-bold">{alsaMaster}%</span>
                </div>
                <input 
                  type="range" min="0" max="100" 
                  value={alsaMaster} 
                  onChange={(e) => setAlsaMaster(parseInt(e.target.value))}
                  onMouseUp={handleAlsaMasterCommit}
                  onTouchEnd={handleAlsaMasterCommit}
                  className="w-full accent-rose-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                />
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[13px] text-zinc-300">
                  <span className="flex items-center gap-2">Pré-Amp Digital (Software Multiplier)</span>
                  <span className="font-mono text-rose-400 font-bold">{softwarePreamp.toFixed(1)}x</span>
                </div>
                <input 
                  type="range" min="10" max="150" 
                  value={softwarePreamp * 10} 
                  onChange={(e) => setSoftwarePreamp(parseInt(e.target.value) / 10)}
                  onMouseUp={handleSoftwarePreampCommit}
                  onTouchEnd={handleSoftwarePreampCommit}
                  className="w-full accent-rose-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                />
              </div>
            </div>

            <div className="mt-auto bg-black/20 rounded-2xl p-6 flex flex-col items-center justify-center relative overflow-hidden border border-white/5">
              <div className={cn("absolute inset-0 bg-gradient-to-t pointer-events-none transition-colors duration-500", isListening ? "from-emerald-500/10 to-transparent" : "from-brass-500/5 to-transparent")} />
              
              <div className={cn("w-20 h-20 rounded-full border-2 flex items-center justify-center mb-5 relative transition-colors duration-500", isListening ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : "border-brass-500/20 text-brass-400")}>
                {!isListening ? (
                  <Mic className="w-8 h-8" />
                ) : (
                  <div className="flex items-center justify-center gap-1.5 h-8">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div 
                        key={i} 
                        className="w-1.5 bg-emerald-400 rounded-full animate-pulse" 
                        style={{ 
                          height: `${Math.max(20, Math.random() * 100)}%`, 
                          animationDelay: `${i * 0.15}s`,
                          animationDuration: '0.6s'
                        }} 
                      />
                    ))}
                  </div>
                )}
              </div>
              
              <button 
                onClick={toggleListening}
                className={cn(
                  "w-full py-3.5 font-bold rounded-xl transition-all transform select-none",
                  isListening 
                    ? "bg-emerald-500 text-black shadow-[0_0_20px_rgba(16,185,129,0.4)] scale-[0.98]" 
                    : "bg-gradient-to-r from-brass-400 to-brass-600 hover:from-brass-300 hover:to-brass-500 text-obsidian-900 shadow-[0_0_20px_rgba(201,162,75,0.3)] hover:scale-[1.02]"
                )}
              >
                {isListening ? "Parar Transmissão" : "Iniciar Áudio Ao Vivo (Toggle)"}
              </button>
              <p className="text-[10px] text-zinc-500 mt-3 text-center uppercase tracking-wider font-semibold">
                Via WebSocket PCM 16kHz
              </p>
            </div>
          </>
        )}
      </div>

    </div>
  );
}
