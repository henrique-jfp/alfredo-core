import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import { Satellite } from '../../types';
import {
  Activity,
  Cpu,
  Lightbulb,
  Loader2,
  Mic,
  Radio,
  Sparkles,
  Sun,
  Volume1,
  Volume2,
  Zap,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { EmptyState, SectionHeading, SkeletonBlock, StatusPulse } from '../ui/DashboardPrimitives';

export class SatellitesTabBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return <div className="p-10 font-mono text-red-500"><h1>Component Crash:</h1><pre>{String(this.state.error?.stack || this.state.error)}</pre></div>;
    }

    return this.props.children;
  }
}

export function SatellitesTab() {
  return (
    <SatellitesTabBoundary>
      <SatellitesTabContent />
    </SatellitesTabBoundary>
  );
}

function SatellitesTabContent() {
  const [satellites, setSatellites] = useState<Satellite[]>([]);
  const [selectedSat, setSelectedSat] = useState<Satellite | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [volume, setVolume] = useState(70);
  const [brightness, setBrightness] = useState(50);
  const [alsaCapture, setAlsaCapture] = useState(100);
  const [alsaMaster, setAlsaMaster] = useState(100);
  const [softwarePreamp, setSoftwarePreamp] = useState(1.0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadSatellites = async () => {
      setIsLoading(true);
      try {
        const data = await api.getSatellites();
        const validData = Array.isArray(data) ? data : [];
        if (!mounted) return;
        setSatellites(validData);
        if (validData.length > 0) {
          setSelectedSat(validData[0]);
          setVolume(validData[0].volume ?? 70);
          setBrightness(validData[0].brightness ?? 50);
        }
      } catch (err) {
        console.error(err);
        if (mounted) setSatellites([]);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadSatellites();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/dashboard`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = async (event) => {
      if (event.data instanceof Blob && audioCtxRef.current) {
        const arrayBuffer = await event.data.arrayBuffer();
        try {
          const audioCtx = audioCtxRef.current;
          const view = new Int16Array(arrayBuffer);
          const audioBuffer = audioCtx.createBuffer(1, view.length, 16000);
          const channelData = audioBuffer.getChannelData(0);
          for (let i = 0; i < view.length; i++) {
            channelData[i] = view[i] / 32768.0;
          }

          const source = audioCtx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioCtx.destination);

          const w = window as any;
          if (!w.nextAudioTime || w.nextAudioTime < audioCtx.currentTime) {
            w.nextAudioTime = audioCtx.currentTime + 0.15;
          }

          source.start(w.nextAudioTime);
          w.nextAudioTime += audioBuffer.duration;
        } catch (e) {
          console.error('Audio playback error:', e);
        }
      }
    };

    return () => {
      mounted = false;
      if (ws.readyState === WebSocket.OPEN) ws.close();
      if (audioCtxRef.current) audioCtxRef.current.close();
    };
  }, []);

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

  const parseCapabilities = (capInput: any) => {
    if (Array.isArray(capInput)) return capInput;
    if (!capInput || typeof capInput !== 'string') return [];
    try {
      const parsed = JSON.parse(capInput);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const handleVolumeCommit = () => {
    if (wsRef.current && selectedSat) wsRef.current.send(`SET_VOLUME:${selectedSat.device_id}:${volume}`);
  };

  const handleBrightnessCommit = () => {
    if (wsRef.current && selectedSat) wsRef.current.send(`SET_BRIGHTNESS:${selectedSat.device_id}:${brightness}`);
  };

  const handleAlsaCaptureCommit = () => {
    if (wsRef.current && selectedSat) wsRef.current.send(`SET_ALSA_CAPTURE:${selectedSat.device_id}:${alsaCapture}`);
  };

  const handleAlsaMasterCommit = () => {
    if (wsRef.current && selectedSat) wsRef.current.send(`SET_ALSA_MASTER:${selectedSat.device_id}:${alsaMaster}`);
  };

  const handleSoftwarePreampCommit = () => {
    if (wsRef.current && selectedSat) wsRef.current.send(`SET_SOFTWARE_PREAMP:${selectedSat.device_id}:${softwarePreamp}`);
  };

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
      sendCommand('STOP_STREAM');
      return;
    }

    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }

    setIsListening(true);
    sendCommand('START_STREAM');
  };

  const capIcons: Record<string, { icon: any; label: string; color: string }> = {
    mic: { icon: Mic, label: 'Microfone I2S', color: 'text-indigo-400 border-indigo-400/20 bg-indigo-400/10' },
    speaker: { icon: Volume1, label: 'Alto-Falante', color: 'text-rose-400 border-rose-400/20 bg-rose-400/10' },
    led: { icon: Lightbulb, label: 'Matriz LED', color: 'text-yellow-400 border-yellow-400/20 bg-yellow-400/10' },
    display: { icon: Activity, label: 'Display OLED', color: 'text-teal-400 border-teal-400/20 bg-teal-400/10' },
  };

  if (isLoading) {
    return (
      <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
        <SectionHeading
          eyebrow="Alfredo"
          title="Controle de Frota"
          subtitle="Carregando a telemetria dos satélites e o painel técnico."
          action={<StatusPulse label="Conectando" tone="warning" />}
        />
        <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="alfredo-card flex min-h-[540px] flex-col gap-4 p-6">
            <SkeletonBlock className="h-4 w-40 rounded-full" />
            <SkeletonBlock className="h-3 w-56 rounded-full" />
            <div className="mt-2 space-y-3">
              <SkeletonBlock className="h-20 rounded-2xl" />
              <SkeletonBlock className="h-20 rounded-2xl" />
              <SkeletonBlock className="h-20 rounded-2xl" />
            </div>
          </div>
          <div className="alfredo-card flex min-h-[540px] flex-col gap-4 p-6">
            <SkeletonBlock className="h-4 w-52 rounded-full" />
            <SkeletonBlock className="h-3 w-72 rounded-full" />
            <SkeletonBlock className="mt-2 h-24 rounded-2xl" />
            <SkeletonBlock className="h-24 rounded-2xl" />
            <SkeletonBlock className="h-24 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Alfredo"
        title="Controle de Frota"
        subtitle="A interface técnica agora ocupa o espaço com mais intenção e menos ruído."
        action={<StatusPulse label={isConnected ? 'WS conectado' : 'WS offline'} tone={isConnected ? 'success' : 'danger'} />}
      />

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <aside className="alfredo-card flex min-h-0 flex-col gap-5 p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="alfredo-section-label">Satélites</div>
              <h2 className="mt-2 text-[18px] font-semibold text-[color:var(--text-primary)]">Frota disponível</h2>
              <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">Selecione um dispositivo para acessar telemetria, áudio e comandos remotos.</p>
            </div>
            <button
              onClick={() => {
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                  satellites.forEach((sat) => wsRef.current?.send(`SET_VOLUME:${sat.device_id}:0`));
                  setVolume(0);
                }
              }}
              className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400"
            >
              Mutar todos
            </button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {satellites.length === 0 ? (
              <EmptyState
                icon={Cpu}
                tone="info"
                title="Nenhum satélite encontrado"
                description="Quando a frota aparecer, ela ocupa esse painel com cards técnicos de leitura rápida."
                className="flex-1"
              />
            ) : (
              satellites.map((sat) => {
                const isActive = selectedSat?.device_id === sat.device_id;
                return (
                  <button
                    key={sat.device_id}
                    onClick={() => setSelectedSat(sat)}
                    className={cn(
                      'relative flex flex-col gap-3 overflow-hidden rounded-2xl border p-4 text-left transition-all duration-200',
                      isActive
                        ? 'border-brass-500/25 bg-brass-500/10 shadow-[0_0_24px_rgba(212,162,78,0.12)]'
                        : 'border-white/5 bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.04]'
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-[15px] font-semibold text-[color:var(--text-primary)]">{sat.hardware}</div>
                        <div className="mt-1 flex items-center gap-2 text-[12px] text-[color:var(--text-secondary)]">
                          <span className="font-mono">{sat.device_id?.split('-')[0] || 'Unk'}</span>
                          <span>·</span>
                          <span>{sat.room_id}</span>
                        </div>
                      </div>
                      <StatusPulse label={sat.is_online ? 'ONLINE' : 'OFFLINE'} tone={sat.is_online ? 'success' : 'danger'} />
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/30">
                        <div className={cn('h-full rounded-full', sat.is_online ? 'bg-emerald-400' : 'bg-rose-400')} style={{ width: `${sat.is_online ? 85 : 35}%` }} />
                      </div>
                      <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                        {sat.is_online ? 'vivo' : 'sem sinal'}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <section className={cn('alfredo-card flex min-h-0 flex-col p-6 md:p-8', !selectedSat && 'justify-center')}>
          {!selectedSat ? (
            <EmptyState
              icon={Cpu}
              tone="brass"
              title="Selecione um satélite"
              description="Escolha um dispositivo na coluna da esquerda para abrir a telemetria e os controles remotos."
              className="min-h-[520px]"
            />
          ) : (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="alfredo-section-label">Detalhes</div>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-tight text-[color:var(--text-primary)] md:text-[28px]">
                    {selectedSat.hardware}
                  </h2>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <StatusPulse label={selectedSat.is_online ? 'Online (WebSockets)' : 'Offline (HTTP)'} tone={selectedSat.is_online ? 'success' : 'danger'} />
                    {selectedSat.is_online && <StatusPulse label="Latência estável" tone="info" />}
                    <StatusPulse label={`Room ${selectedSat.room_id}`} tone="brass" />
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => sendCommand('OTA_UPDATE')}
                    title="Atualização OTA"
                    className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]"
                  >
                    <Zap className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => sendCommand('IDENTIFY')}
                    title="Localizar satélite"
                    className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]"
                  >
                    <Radio className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <div className="alfredo-surface p-4">
                  <div className="alfredo-section-label">Hardware</div>
                  <div className="mt-2 text-[14px] text-[color:var(--text-primary)]">{selectedSat.hardware}</div>
                </div>
                <div className="alfredo-surface p-4">
                  <div className="alfredo-section-label">Firmware</div>
                  <div className="mt-2 font-mono text-[14px] text-[color:var(--text-primary)]">{selectedSat.firmware_version}</div>
                </div>
                <div className="alfredo-surface p-4">
                  <div className="alfredo-section-label">ID</div>
                  <div className="mt-2 font-mono text-[14px] text-[color:var(--text-primary)]">{selectedSat.device_id}</div>
                </div>
                <div className="alfredo-surface p-4">
                  <div className="alfredo-section-label">Cômodo</div>
                  <div className="mt-2 text-[14px] text-[color:var(--text-primary)]">{selectedSat.room_id}</div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {parseCapabilities((selectedSat as any).capabilities).map((cap: string) => {
                  const spec = capIcons[cap];
                  if (!spec) return null;
                  const Icon = spec.icon;
                  return (
                    <div key={cap} className={cn('alfredo-pill', spec.color)}>
                      <Icon className="h-3.5 w-3.5" />
                      {spec.label}
                    </div>
                  );
                })}
                {parseCapabilities((selectedSat as any).capabilities).length === 0 && (
                  <div className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-tertiary)]">Hardware básico</div>
                )}
              </div>

              <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
                <div className="alfredo-card p-5">
                  <div className="flex items-center gap-2">
                    <Volume2 className="h-4 w-4 text-brass-400" />
                    <span className="alfredo-section-label">Volume</span>
                    <span className="ml-auto font-mono text-[14px] font-semibold text-brass-300">{volume}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={volume}
                    onChange={(e) => setVolume(parseInt(e.target.value))}
                    onMouseUp={handleVolumeCommit}
                    onTouchEnd={handleVolumeCommit}
                    className="mt-4 w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-brass-500 h-1.5"
                  />

                  <div className="mt-5 flex items-center gap-2">
                    <Sun className="h-4 w-4 text-brass-400" />
                    <span className="alfredo-section-label">Brilho do LED</span>
                    <span className="ml-auto font-mono text-[14px] font-semibold text-brass-300">{brightness}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={brightness}
                    onChange={(e) => setBrightness(parseInt(e.target.value))}
                    onMouseUp={handleBrightnessCommit}
                    onTouchEnd={handleBrightnessCommit}
                    className="mt-4 w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-brass-500 h-1.5"
                  />
                </div>

                <div className="alfredo-card border-rose-500/10 bg-rose-500/[0.04] p-5">
                  <div className="flex items-center gap-2 border-b border-rose-500/10 pb-3">
                    <Activity className="h-4 w-4 text-rose-400" />
                    <span className="alfredo-section-label text-rose-300">Mixer de áudio avançado</span>
                  </div>

                  <div className="mt-4 space-y-4">
                    <div>
                      <div className="mb-2 flex items-center justify-between text-[13px] text-[color:var(--text-secondary)]">
                        <span className="flex items-center gap-2">ALSA Microfone</span>
                        <span className="font-mono text-rose-400">{alsaCapture}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={alsaCapture}
                        onChange={(e) => setAlsaCapture(parseInt(e.target.value))}
                        onMouseUp={handleAlsaCaptureCommit}
                        onTouchEnd={handleAlsaCaptureCommit}
                        className="w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-rose-500 h-1.5"
                      />
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between text-[13px] text-[color:var(--text-secondary)]">
                        <span className="flex items-center gap-2">ALSA Alto-falante</span>
                        <span className="font-mono text-rose-400">{alsaMaster}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={alsaMaster}
                        onChange={(e) => setAlsaMaster(parseInt(e.target.value))}
                        onMouseUp={handleAlsaMasterCommit}
                        onTouchEnd={handleAlsaMasterCommit}
                        className="w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-rose-500 h-1.5"
                      />
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between text-[13px] text-[color:var(--text-secondary)]">
                        <span className="flex items-center gap-2">Pré-amp digital</span>
                        <span className="font-mono text-rose-400">{softwarePreamp.toFixed(1)}x</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="150"
                        value={softwarePreamp * 10}
                        onChange={(e) => setSoftwarePreamp(parseInt(e.target.value) / 10)}
                        onMouseUp={handleSoftwarePreampCommit}
                        onTouchEnd={handleSoftwarePreampCommit}
                        className="w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-rose-500 h-1.5"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="relative mt-6 rounded-2xl border border-white/5 bg-black/20 p-6">
                <div className={cn('absolute inset-0 pointer-events-none rounded-2xl bg-gradient-to-t', isListening ? 'from-emerald-500/10 to-transparent' : 'from-brass-500/5 to-transparent')} />
                <div className="relative flex flex-col items-center">
                  <div className={cn('mb-5 flex h-20 w-20 items-center justify-center rounded-full border-2', isListening ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' : 'border-brass-500/20 text-brass-400')}>
                    {!isListening ? (
                      <Mic className="h-8 w-8" />
                    ) : (
                      <div className="flex h-8 items-end justify-center gap-1.5">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div
                            key={i}
                            className="w-1.5 rounded-full bg-emerald-400 animate-pulse"
                            style={{
                              height: `${Math.max(20, Math.random() * 100)}%`,
                              animationDelay: `${i * 0.15}s`,
                              animationDuration: '0.6s',
                            }}
                          />
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={toggleListening}
                    className={cn(
                      'w-full rounded-2xl px-4 py-3.5 font-semibold transition-all',
                      isListening
                        ? 'bg-emerald-500 text-black shadow-[0_0_20px_rgba(16,185,129,0.35)] scale-[0.98]'
                        : 'bg-gradient-to-r from-brass-400 to-brass-600 text-[color:var(--bg-base)] shadow-[0_0_20px_rgba(212,162,78,0.22)] hover:scale-[1.02]'
                    )}
                  >
                    {isListening ? 'Parar transmissão' : 'Iniciar áudio ao vivo'}
                  </button>
                  <p className="mt-3 text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">
                    Via WebSocket PCM 16kHz
                  </p>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
