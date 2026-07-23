import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { Stats, HistoryItem, ListItem, TimerItem, Weather, getWeatherKind } from '../../types';
import {
  Bell,
  CheckSquare,
  Clock,
  Cpu,
  Mic,
  MessageSquare,
  ShoppingCart,
  Sun,
  Cloud,
  CloudRain,
  CloudLightning,
  CloudSnow,
  Zap,
  AlarmClock,
  TimerReset,
  Activity,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { SpotifyCard } from '../SpotifyCard';
import { EmptyState, MetricCard, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { Modal } from '../ui/Modal';
import { useIsVisible } from '../../hooks/useIsVisible';

type WidgetKey = 'compras' | 'tarefas' | 'lembretes';
const RIO_TIME_ZONE = 'America/Sao_Paulo';

function formatRio(date: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: RIO_TIME_ZONE, ...options }).format(date);
}

const ClockDisplay = React.memo(function ClockDisplay({ time }: { time: Date }) {
  return (
    <div className="flex flex-col shrink-0">
      <div className="text-[11px] font-medium uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
        {formatRio(time, { weekday: 'long', day: '2-digit', month: 'long' })}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <h1 className="text-5xl font-semibold leading-none tracking-tight text-[color:var(--text-primary)] md:text-6xl" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {formatRio(time, { hour: '2-digit', minute: '2-digit' })}
        </h1>
        <span className="font-mono text-2xl font-medium text-[color:var(--text-tertiary)] md:text-3xl opacity-50">
          {time.getSeconds().toString().padStart(2, '0')}
        </span>
      </div>
    </div>
  );
});

function formatCountdown(expiresAt: string) {
  const now = Date.now();
  const end = new Date(expiresAt).getTime();
  const diff = Math.max(0, Math.floor((end - now) / 1000));
  const minutes = Math.floor(diff / 60);
  const seconds = diff % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// getWeatherKind movido para types.ts (compartilhado)

function TimerCard({
  timer,
  onDelete,
}: {
  timer: TimerItem;
  onDelete: (id: number) => void;
}) {
  const [timeLeft, setTimeLeft] = useState(() => formatCountdown(timer.expires_at));

  useEffect(() => {
    const tick = () => setTimeLeft(formatCountdown(timer.expires_at));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [timer.expires_at]);

  const isAlarm = timer.timer_type === 'alarm' || (timer.message && timer.message.toLowerCase().includes('despertar'));
  const accent = isAlarm
    ? 'border-brass-500/20 bg-brass-500/10 text-brass-300'
    : 'border-blue-500/20 bg-blue-500/10 text-blue-300';
  const glow = isAlarm
    ? 'shadow-[0_0_24px_rgba(212,162,78,0.14)]'
    : 'shadow-[0_0_24px_rgba(96,165,250,0.12)]';
  const label = isAlarm ? 'Despertador' : 'Timer';
  const icon = isAlarm
    ? <AlarmClock className="h-5 w-5 shrink-0 text-brass-400" />
    : <TimerReset className="h-5 w-5 shrink-0 text-blue-400" />;

  return (
    <button
      onClick={() => {
        if (window.confirm(`Você quer cancelar ${label.toLowerCase()} ${timer.message ? `(${timer.message})` : ''}?`)) {
          onDelete(timer.id);
        }
      }}
      className={cn(
        'group flex min-w-0 flex-col justify-between rounded-2xl border p-4 text-left transition-all duration-200 hover:-translate-y-0.5',
        accent,
        glow
      )}
      title={label}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="alfredo-section-label mb-2">{label}</div>
          <div className="font-mono text-[24px] font-semibold tracking-tight tabular-nums">{timeLeft}</div>
        </div>
        {icon}
      </div>
      <div className="mt-3 min-w-0">
        <div className="truncate text-[13px] font-medium text-[color:var(--text-primary)]">
          {timer.message || `${label} ativo`}
        </div>
        <div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
          {formatRio(new Date(timer.expires_at), { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </button>
  );
}

export function OverviewTab() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [lists, setLists] = useState<{ compras: ListItem[]; tarefas: ListItem[] }>({ compras: [], tarefas: [] });
  const [timers, setTimers] = useState<TimerItem[]>([]);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [time, setTime] = useState(new Date());
  const [commandText, setCommandText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [lastCommandLatencyMs, setLastCommandLatencyMs] = useState<number | null>(null);
  const [activeWidget, setActiveWidget] = useState<WidgetKey>('compras');
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [commandError, setCommandError] = useState<string | null>(null);
  const { ref, isVisible } = useIsVisible<HTMLDivElement>();

  const fetchData = useCallback(async () => {
    setIsRefreshing(true);
    
    // Fetch weather asynchronously without blocking
    api.getWeather().then(weatherData => {
      if (weatherData) setWeather(weatherData);
    }).catch(() => null);

    const [statsData, historyData, listsData, timersData] = await Promise.all([
      api.getStats(),
      api.getHistory(),
      api.getLists(),
      api.getTimers(),
    ]);
    setStats(statsData);
    setHistory(historyData);
    setLists(listsData);
    setTimers(timersData);
    setTimeout(() => setIsRefreshing(false), 450);
  }, []);

  useEffect(() => {
    fetchData();
    const dataInterval = setInterval(() => {
      if (isVisible) fetchData();
    }, 10000);
    const clockInterval = setInterval(() => setTime(new Date()), 1000);
    return () => {
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, [fetchData, isVisible]);

  const handleCommandSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!commandText.trim()) return;

    setIsSending(true);
    setCommandError(null);
    const startedAt = performance.now();
    try {
      await api.sendCommand(commandText);
      setLastCommandLatencyMs(Math.max(0, Math.round(performance.now() - startedAt)));
      setCommandText('');
      fetchData();
    } catch (error) {
      console.error(error);
      setCommandError(error instanceof Error ? error.message : 'Erro ao enviar comando');
    } finally {
      setIsSending(false);
    }
  };

  const deleteTimer = useCallback(async (id: number) => {
    try {
      await api.deleteTimer(id);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  }, [fetchData]);

  const alarms = timers.filter((t) => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
  const nextAlarm = alarms.length > 0 ? [...alarms].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime())[0] : null;

  const WeatherIcon = React.memo(function WeatherIcon({ kind, temp }: { kind: string; temp?: number | string }) {
    const sunRays = Array.from({ length: 8 }, (_, i) => (
      <div key={i} className="absolute inset-0 flex items-center justify-center" style={{ transform: `rotate(${i * 45}deg)` }}>
        <div className="w-[2px] h-5 rounded-full bg-gradient-to-t from-transparent via-brass-400/70 to-brass-300/40 origin-bottom" style={{ animation: `rayRotate 4s ${i * 0.3}s ease-in-out infinite` }} />
      </div>
    ));

    const raindrops = Array.from({ length: 12 }, (_, i) => (
      <div key={i} className="absolute w-[1.5px] h-3 rounded-full bg-gradient-to-b from-transparent via-blue-400/50 to-blue-300/30" style={{ left: `${10 + Math.random() * 80}%`, animation: `rainDrop ${0.6 + Math.random() * 0.4}s ${Math.random() * 0.8}s ease-in infinite`, opacity: 0 }} />
    ));

    const snowflakes = Array.from({ length: 15 }, (_, i) => (
      <div key={i} className="absolute w-1.5 h-1.5 rounded-full bg-white/60" style={{ left: `${10 + Math.random() * 80}%`, animation: `snowFall ${2 + Math.random() * 2}s ${Math.random() * 2}s ease-in infinite`, opacity: 0 }} />
    ));

    const lightningBolt = (
      <div className="absolute inset-0 flex items-center justify-center">
      <div className="w-[3px] h-16 skew-y-[12deg] rounded-full bg-gradient-to-b from-yellow-300 via-yellow-400 to-transparent shadow-[0_0_20px_rgba(250,204,21,0.6)]" style={{ animation: 'lightningFlash 3s ease-in-out infinite', marginTop: -20 }} />
      <div className="w-[2px] h-10 skew-y-[-15deg] rounded-full bg-gradient-to-b from-yellow-400 to-transparent" style={{ marginTop: 12, marginLeft: 8 }} />
      </div>
    );

    if (kind === 'sun') {
      return (
        <div className="relative w-14 h-14 flex items-center justify-center" style={{ animation: 'sunPulse 3s ease-in-out infinite' }}>
          {sunRays}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brass-300 to-brass-500 shadow-[0_0_30px_rgba(212,162,78,0.6)]" />
        </div>
      );
    }
    if (kind === 'rain') {
      return (
        <div className="relative w-14 h-14 flex items-center justify-center">
          <Cloud className="absolute w-10 h-10 text-zinc-300/80 z-10" style={{ filter: 'drop-shadow(0 0 10px rgba(255,255,255,0.15))' }} />
          {raindrops}
        </div>
      );
    }
    if (kind === 'snow') {
      return (
        <div className="relative w-14 h-14 flex items-center justify-center">
          <Cloud className="absolute w-10 h-10 text-zinc-300/60 z-10" style={{ animation: 'cloudDrift 4s ease-in-out infinite' }} />
          {snowflakes}
        </div>
      );
    }
    if (kind === 'storm') {
      return (
        <div className="relative w-14 h-14 flex items-center justify-center">
          <div className="absolute w-12 h-12 rounded-full bg-zinc-700/60 blur-md" style={{ animation: 'cloudPulse 2s ease-in-out infinite' }} />
          <Cloud className="absolute w-11 h-11 text-zinc-400 z-10" />
          {lightningBolt}
          {raindrops}
        </div>
      );
    }
    return (
      <div className="relative w-14 h-14 flex items-center justify-center">
        <Cloud className="w-11 h-11 text-zinc-300/70" style={{ animation: 'cloudDrift 5s ease-in-out infinite' }} />
        <Cloud className="absolute w-9 h-9 text-zinc-400/40 -ml-6 -mt-4" style={{ animation: 'cloudDrift2 6s ease-in-out infinite' }} />
      </div>
    );
  });

  const recentActivities = useMemo(() => history.slice(0, 6), [history]);
  const weatherCode = weather?.weather_code ?? -1;
  const weatherKind = useMemo(() => getWeatherKind(weatherCode), [weatherCode]);
  const weatherTitle = useMemo(() => {
    switch (weatherKind) {
      case 'sun': return 'Ensolarado';
      case 'cloud': return 'Nublado';
      case 'rain': return 'Chuva';
      case 'snow': return 'Neve';
      case 'storm': return 'Tempestade';
      default: return '—';
    }
  }, [weatherKind]);
  const kpis = [
    { label: 'Conversas', value: stats?.interactions || '—', icon: MessageSquare, tone: 'info' as const, detail: 'Atividade consolidada' },
    { label: 'Timers', value: stats?.active_timers ?? '—', icon: Clock, tone: 'warning' as const, detail: 'Alarmes e lembretes' },
    { label: 'Satélites', value: stats?.devices || '—', icon: Cpu, tone: 'success' as const, detail: 'Nós online na rede' },
    { label: 'IA', value: stats?.ai_requests?.toLocaleString('pt-BR') || '—', icon: Zap, tone: 'brass' as const, detail: `Tokens ${stats?.tokens_used?.toLocaleString('pt-BR') || 0}` },
  ];

  const widgetCounts = {
    compras: lists.compras.length,
    tarefas: lists.tarefas.length,
    lembretes: timers.length,
  };

  const activeTimers = timers.filter((t) => t.timer_type === 'timer' && !(t.message && t.message.toLowerCase().includes('despertar')));
  const activeAlarms = alarms;
  const hasPinnedTimers = activeTimers.length > 0 || activeAlarms.length > 0;
  const pinnedTimers =
    activeTimers.length > 0 && activeAlarms.length > 0
      ? [activeTimers[0], activeAlarms[0]]
      : activeTimers.length > 0
        ? activeTimers.slice(0, 2)
        : activeAlarms.slice(0, 2);

  return (
    <div ref={ref} className="flex h-full flex-col gap-5 overflow-y-auto pr-2 pb-10">
      {/* Cabeçalho compacto: relógio + timers + clima */}
      <div className="flex items-center justify-between gap-4 py-2 flex-wrap">
        <ClockDisplay time={time} />
        <div className="flex items-center gap-4 flex-wrap">
          {hasPinnedTimers && pinnedTimers.slice(0, 2).map((timer) => (
            <TimerCard key={timer.id} timer={timer} onDelete={deleteTimer} />
          ))}
          <div className="flex items-center gap-3 alfredo-card p-3 md:p-3 shrink-0">
            <WeatherIcon kind={weatherKind} temp={weather?.temperature} />
            <div className="flex flex-col">
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold leading-none text-white tabular-nums">{weather ? `${weather.temperature}°` : '--°'}</span>
                <span className="text-[11px] text-zinc-500">/{weather?.max_temp ?? '--'}°</span>
              </div>
              <span className="text-[10px] text-zinc-500 leading-tight mt-0.5">{weather?.description || 'Buscando...'}</span>
              {weather?.humidity && <span className="text-[9px] text-zinc-600 leading-tight mt-0.5">{weather.humidity}% umidade</span>}
            </div>
          </div>
        </div>
      </div>

      <SpotifyCard />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.label}>
            <MetricCard
              icon={kpi.icon}
              label={kpi.label}
              value={kpi.value}
              detail={kpi.detail}
              tone={kpi.tone}
              sparkline={kpi.label === 'IA' ? [0.35, 0.42, 0.38, 0.55, 0.62, 0.8] : [0.24, 0.28, 0.4, 0.52, 0.48, 0.66]}
            />
          </div>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.45fr_0.95fr]">
        <section className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Atividade"
            title="Conversas recentes" 
            action={
              <button 
                onClick={() => setIsHistoryModalOpen(true)}
                className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)] hover:bg-white/[0.06] hover:text-[color:var(--text-primary)] transition-colors"
              >
                Ver histórico completo
              </button>
            }
          />

          <form onSubmit={handleCommandSubmit} className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
            <div className="flex flex-col gap-1">
              <input
                type="text"
                value={commandText}
                onChange={(e) => setCommandText(e.target.value)}
                disabled={isSending}
                placeholder="Comando rápido para o Alfredo..."
                className="alfredo-input"
                aria-label="Comando para o Alfredo"
              />
              {commandError && (
                <span className="px-1 text-[11px] text-rose-400">{commandError}</span>
              )}
            </div>
            <button
              type="submit"
              disabled={isSending || !commandText.trim()}
              className="alfredo-pill justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.18)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Mic className="h-4 w-4" />
              Enviar
            </button>
          </form>

          <div className="mt-5 flex min-h-0 flex-col gap-2 overflow-y-auto pr-0.5">
            {recentActivities.length === 0 ? (
              <EmptyState
                icon={Activity}
                tone="info"
                title="Ainda não há conversas registradas"
                description="Assim que a casa começar a falar com o Alfredo, eu trago as interações mais úteis primeiro."
                className="py-12"
              />
            ) : (
              recentActivities.map((item, index) => {
                const isLatest = index === 0;
                const rioTime = formatRio(new Date(item.timestamp), { hour: '2-digit', minute: '2-digit' });
                return (
                  <div key={item.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.04]">
                    <div className="flex items-start justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">
                      <span className="truncate">{item.room_id} • {item.device_id}</span>
                      <div className="flex flex-col items-end gap-1 text-right">
                        <span>{rioTime}</span>
                        {(item.latency_ms || (isLatest ? lastCommandLatencyMs : null)) ? (
                          <span className="rounded-full border border-white/5 bg-black/30 px-2 py-0.5 text-[9px] tracking-[0.16em] text-[color:var(--text-secondary)]">
                            Latência {item.latency_ms || lastCommandLatencyMs} ms
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="mt-3 flex gap-3">
                      <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-brass-400 shadow-[0_0_12px_rgba(212,162,78,0.25)]" />
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-[14px] font-medium text-[color:var(--text-primary)]">{item.input_text}</p>
                        <p className="mt-2 rounded-xl border border-white/5 bg-black/20 px-3 py-2 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
                          {item.output_text || 'Processando resposta...'}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        <section className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            title="Compras, tarefas e lembretes"
          />

          <div className="mt-5 grid grid-cols-3 gap-2 rounded-2xl border border-white/5 bg-white/[0.02] p-2">
            {([
              { key: 'compras', label: 'Compras', icon: ShoppingCart },
              { key: 'tarefas', label: 'Tarefas', icon: CheckSquare },
              { key: 'lembretes', label: 'Lembretes', icon: Bell },
            ] as const).map((item) => {
              const Icon = item.icon;
              const isActive = activeWidget === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveWidget(item.key)}
                  className={cn(
                    'flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-[12px] font-semibold transition-colors',
                    isActive
                      ? 'bg-brass-500/15 text-brass-300 shadow-[0_0_20px_rgba(212,162,78,0.12)]'
                      : 'text-[color:var(--text-secondary)] hover:bg-white/[0.04]'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                  <span className="rounded-full bg-black/25 px-2 py-0.5 text-[11px] font-semibold">{widgetCounts[item.key]}</span>
                </button>
              );
            })}
          </div>

          <div className="mt-5 min-h-0 flex-1 overflow-y-auto pr-1">
            {activeWidget === 'compras' && (
              <div className="flex min-h-[220px] flex-col gap-2">
                {lists.compras.length === 0 ? (
                  <EmptyState
                    icon={ShoppingCart}
                    tone="brass"
                    title="Nenhuma compra cadastrada"
                    description="Adicione itens quando quiser. O painel vai manter espaço com intenção, não com vazio."
                    className="flex-1"
                  />
                ) : (
                  (() => {
                    const groupedCompras = lists.compras.reduce((acc, item) => {
                      const match = item.content.match(/^\[(.*?)\] (.*)$/);
                      const listName = match ? match[1] : 'Geral';
                      const itemName = match ? match[2] : item.content;
                      if (!acc[listName]) acc[listName] = [];
                      acc[listName].push({ ...item, parsedContent: itemName });
                      return acc;
                    }, {} as Record<string, any[]>);

                    return Object.entries(groupedCompras).map(([listName, items]) => (
                      <div key={listName} className="mb-3 last:mb-0 flex flex-col gap-2">
                        <div className="flex items-center gap-2 pl-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-brass-500/70">{listName}</span>
                          <div className="h-px flex-1 bg-gradient-to-r from-brass-500/20 to-transparent" />
                        </div>
                        {items.map((item) => (
                          <div key={item.id} className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                            <div className="h-1.5 w-1.5 rounded-full bg-brass-400" />
                            <span className="truncate text-[14px] text-[color:var(--text-primary)]">{item.parsedContent}</span>
                          </div>
                        ))}
                      </div>
                    ));
                  })()
                )}
              </div>
            )}

            {activeWidget === 'tarefas' && (
              <div className="flex min-h-[220px] flex-col gap-2">
                {lists.tarefas.length === 0 ? (
                  <EmptyState
                    icon={CheckSquare}
                    tone="info"
                    title="Nenhuma tarefa pendente"
                    description="Quando surgir uma tarefa, ela ocupa o espaço certo e não quebra a composição."
                    className="flex-1"
                  />
                ) : (
                  lists.tarefas.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                      <div className="h-2 w-2 rounded-full bg-blue-400" />
                      <span className="truncate text-[14px] text-[color:var(--text-primary)]">{item.content}</span>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeWidget === 'lembretes' && (
              <div className="flex min-h-[220px] flex-col gap-2">
                {timers.length === 0 ? (
                  <EmptyState
                    icon={TimerReset}
                    tone="warning"
                    title="Nenhum lembrete ativo"
                    description="Timers e alarmes aparecem aqui com peso visual mais claro quando estão ativos."
                    className="flex-1"
                  />
                ) : (
                  timers.map((timer) => {
                    const timeStr = new Date(timer.expires_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                    return (
                      <button
                        key={timer.id}
                        onClick={() => deleteTimer(timer.id)}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3 text-left transition-colors hover:bg-white/[0.04]"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <div className="h-2 w-2 rounded-full bg-brass-400" />
                          <span className="font-mono text-[14px] font-semibold text-brass-300">{timeStr}</span>
                          <span className="truncate text-[14px] text-[color:var(--text-primary)]">{timer.message || 'Timer ativo'}</span>
                        </div>
                        <AlarmClock className="h-4 w-4 shrink-0 text-[color:var(--text-tertiary)]" />
                      </button>
                    );
                  })
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      <Modal open={isHistoryModalOpen} onClose={() => setIsHistoryModalOpen(false)} title="Histórico de Conversas" maxWidth="max-w-2xl">
        <p className="mb-4 text-sm text-[color:var(--text-secondary)]">Últimas interações registradas no sistema.</p>
        <div className="space-y-4">
          {history.length === 0 ? (
            <EmptyState
              icon={Activity}
              tone="info"
              title="Nenhum histórico encontrado"
              description="As conversas recentes aparecerão aqui."
            />
          ) : (
            history.map((item) => {
              const rioTime = formatRio(new Date(item.timestamp), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
              return (
                <div key={item.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                  <div className="flex items-start justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">
                    <span className="truncate">{item.room_id} • {item.device_id}</span>
                    <div className="flex flex-col items-end gap-1 text-right">
                      <span>{rioTime}</span>
                      {item.latency_ms ? (
                        <span className="rounded-full border border-white/5 bg-black/30 px-2 py-0.5 text-[9px] tracking-[0.16em] text-[color:var(--text-secondary)]">
                          Latência {item.latency_ms} ms
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3">
                    <div className="mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-brass-400 shadow-[0_0_12px_rgba(212,162,78,0.25)]" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[14px] font-medium text-[color:var(--text-primary)]">{item.input_text}</p>
                      <p className="mt-2 rounded-xl border border-white/5 bg-black/20 px-3 py-2 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
                        {item.output_text || 'Processando resposta...'}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Modal>
    </div>
  );
}
