import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { motion } from 'motion/react';
import { api } from '../../lib/api';
import { Stats, HistoryItem, ListItem, TimerItem, Weather, getWeatherKind } from '../../types';
import {
  Bell,
  CheckSquare,
  Clock,
  Cpu,
  MessageSquare,
  ShoppingCart,
  Zap,
  AlarmClock,
  TimerReset,
  Activity,
  Sparkles,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { SpotifyCard } from '../SpotifyCard';
import { EmptyState, MetricCard, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { Modal } from '../ui/Modal';
import { AlfredoOrb } from '../AlfredoOrb';
import { useAlfredoState } from '../../hooks/useAlfredoState';
import { useToast } from '../Toast';
import { WeatherIconByCode } from '../WeatherDisplay';
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

function TimerCard({
  timer,
  onRequestDelete,
}: {
  timer: TimerItem;
  onRequestDelete: (timer: TimerItem) => void;
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
      onClick={() => onRequestDelete(timer)}
      className={cn(
        'group flex min-w-0 flex-col justify-between rounded-2xl border p-4 text-left transition-all duration-200 hover:-translate-y-0.5',
        accent,
        glow
      )}
      title={`Cancelar ${label}`}
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

// --- Section entrance variants for motion ---
const sectionVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.06,
      duration: 0.4,
      ease: [0.25, 0.1, 0.25, 1] as const,
    },
  }),
};

export function OverviewTab() {
  const { state: alfredoState } = useAlfredoState();
  const { toast } = useToast();
  const { ref, isVisible } = useIsVisible<HTMLDivElement>();

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
  const [confirmDeleteTimer, setConfirmDeleteTimer] = useState<TimerItem | null>(null);

  const fetchData = useCallback(async () => {
    setIsRefreshing(true);

    // Fetch weather asynchronously
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
    setTimeout(() => setIsRefreshing(false), 300);
  }, []);

  useEffect(() => {
    fetchData();
    const dataInterval = setInterval(() => {
      // Só faz fetch se o componente está visivel no viewport E a aba do browser está ativa
      if (isVisible && document.visibilityState === 'visible') fetchData();
    }, 10000);
    const clockInterval = setInterval(() => setTime(new Date()), 1000);

    // Recarrega quando o usuário retorna para a aba (complementa o IntersectionObserver)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isVisible) fetchData();
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(dataInterval);
      clearInterval(clockInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
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
      const latency = Math.max(0, Math.round(performance.now() - startedAt));
      setLastCommandLatencyMs(latency);
      setCommandText('');
      toast('success', 'Comando enviado', `${latency}ms de latência`);
      fetchData();
    } catch (error) {
      console.error(error);
      setCommandError(error instanceof Error ? error.message : 'Erro ao enviar comando');
      toast('error', 'Erro ao enviar comando', error instanceof Error ? error.message : undefined);
    } finally {
      setIsSending(false);
    }
  };

  const deleteTimer = useCallback(async (id: number) => {
    try {
      await api.deleteTimer(id);
      toast('success', 'Timer removido');
      setConfirmDeleteTimer(null);
      fetchData();
    } catch (e) {
      console.error(e);
      toast('error', 'Erro ao remover timer');
    }
  }, [fetchData, toast]);

  const alarms = timers.filter((t) => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
  const activeTimers = timers.filter((t) => t.timer_type === 'timer' && !(t.message && t.message.toLowerCase().includes('despertar')));
  const hasPinnedTimers = activeTimers.length > 0 || alarms.length > 0;
  const pinnedTimers =
    activeTimers.length > 0 && alarms.length > 0
      ? [activeTimers[0], alarms[0]]
      : activeTimers.length > 0
        ? activeTimers.slice(0, 2)
        : alarms.slice(0, 2);

  const recentActivities = useMemo(() => history.slice(0, 6), [history]);
  const weatherCode = weather?.weather_code ?? -1;
  const weatherKind = useMemo(() => getWeatherKind(weatherCode), [weatherCode]);
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

  // --- Greeting based on time of day ---
  const greeting = useMemo(() => {
    const hour = time.getHours();
    if (hour < 6) return 'Boa madrugada';
    if (hour < 12) return 'Bom dia';
    if (hour < 18) return 'Boa tarde';
    return 'Boa noite';
  }, [time]);

  return (
    <div ref={ref} className="flex h-full flex-col gap-5 overflow-y-auto pr-2 pb-10">
      {/* ═══════ HERO SECTION — Alfredo Orb + Clock + Weather ═══════ */}
      <motion.div
        custom={0}
        variants={sectionVariants}
        initial="hidden"
        animate="visible"
        className="flex items-start justify-between gap-6 flex-wrap"
      >
        {/* Left: Orb + Greeting */}
        <div className="flex items-center gap-5">
          <AlfredoOrb state={alfredoState} size="xl" pulse />
          <div className="flex flex-col gap-1">
            <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">
              {greeting}
            </h2>
            <p className="text-[13px] text-[color:var(--text-secondary)] leading-relaxed max-w-[240px]">
              {weather
                ? `${weather.description}, ${weather.temperature}°`
                : 'Alfredo está pronto para ajudar.'}
            </p>
          </div>
        </div>

        {/* Right: Weather Icon + Clock + Timers */}
        <div className="flex items-center gap-4 flex-wrap shrink-0">
          <div className="alfredo-card p-2 md:p-3 flex items-center gap-3 shrink-0">
            <WeatherIconByCode code={weatherCode} size="sm" />
            <div className="flex flex-col min-w-0">
              <span className="text-[15px] font-bold leading-none text-white tabular-nums">
                {weather ? `${weather.temperature}°` : '--°'}
              </span>
              <span className="text-[10px] text-zinc-500 leading-tight mt-0.5 truncate max-w-[80px]">
                {weather?.description || '...'}
              </span>
            </div>
          </div>
          {hasPinnedTimers && pinnedTimers.slice(0, 2).map((timer) => (
            <TimerCard key={timer.id} timer={timer} onRequestDelete={setConfirmDeleteTimer} />
          ))}
          <ClockDisplay time={time} />
        </div>
      </motion.div>

      {/* ═══════ COMMAND BAR ═══════ */}
      <motion.div
        custom={1}
        variants={sectionVariants}
        initial="hidden"
        animate="visible"
        className="relative"
      >
        <form onSubmit={handleCommandSubmit} className="relative">
          <div className="relative flex items-center gap-3 rounded-2xl border border-[color:var(--border-subtle)] bg-[color:var(--bg-surface)] px-4 py-3 transition-all duration-200 focus-within:border-brass-500/40 focus-within:shadow-[0_0_0_1px_rgba(212,162,78,0.2),0_0_24px_rgba(212,162,78,0.08)] shadow-[0_4px_16px_rgba(0,0,0,0.2)]">
            <Sparkles className="h-5 w-5 shrink-0 text-brass-400/60" />
            <input
              type="text"
              value={commandText}
              onChange={(e) => setCommandText(e.target.value)}
              disabled={isSending}
              placeholder="Comande o Alfredo — luzes, música, rotinas..."
              className="flex-1 bg-transparent text-[15px] text-[color:var(--text-primary)] placeholder:text-[color:var(--text-tertiary)] outline-none"
              aria-label="Comando para o Alfredo"
            />
            {commandText.trim() && (
              <button
                type="submit"
                disabled={isSending}
                className="alfredo-pill border-brass-500/25 bg-brass-500/15 text-brass-300 hover:bg-brass-500/25 transition-all disabled:opacity-50 shrink-0"
              >
                {isSending ? (
                  <span className="inline-block w-4 h-4 rounded-full border-2 border-brass-400/30 border-t-brass-300 animate-spin" />
                ) : (
                  'Enviar'
                )}
              </button>
            )}
          </div>
          {commandError && (
            <p className="mt-2 px-4 text-[12px] text-rose-400 flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-rose-400" />
              {commandError}
            </p>
          )}
        </form>
      </motion.div>

      {/* ═══════ SPOTIFY ═══════ */}
      <motion.div custom={2} variants={sectionVariants} initial="hidden" animate="visible">
        <SpotifyCard />
      </motion.div>

      {/* ═══════ KPI CARDS ═══════ */}
      <motion.div
        custom={3}
        variants={sectionVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
      >
        {kpis.map((kpi) => (
          <MetricCard
            key={kpi.label}
            icon={kpi.icon}
            label={kpi.label}
            value={kpi.value}
            detail={kpi.detail}
            tone={kpi.tone}
            sparkline={kpi.label === 'IA' ? [0.35, 0.42, 0.38, 0.55, 0.62, 0.8] : [0.24, 0.28, 0.4, 0.52, 0.48, 0.66]}
          />
        ))}
      </motion.div>

      {/* ═══════ TWO-COLUMN SECTION ═══════ */}
      <motion.div
        custom={4}
        variants={sectionVariants}
        initial="hidden"
        animate="visible"
        className="grid gap-5 xl:grid-cols-[1.45fr_0.95fr]"
      >
        {/* --- Recent conversations --- */}
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
                      <StatusPulse label="" tone={alfredoState === 'error' ? 'danger' : 'brass'} className="mt-0.5 w-2.5 h-2.5 [&>span]:hidden" />
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

        {/* --- Widgets: Compras / Tarefas / Lembretes --- */}
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
      </motion.div>

      {/* ═══════ HISTORY MODAL ═══════ */}
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

      {/* ═══════ CONFIRM DELETE TIMER MODAL ═══════ */}
      <Modal
        open={confirmDeleteTimer !== null}
        onClose={() => setConfirmDeleteTimer(null)}
        title="Cancelar timer"
        maxWidth="max-w-sm"
      >
        {confirmDeleteTimer && (
          <div className="flex flex-col gap-5">
            <p className="text-[14px] leading-relaxed text-[color:var(--text-secondary)]">
              Deseja cancelar o{' '}
              <span className="font-semibold text-[color:var(--text-primary)]">
                {confirmDeleteTimer.timer_type === 'alarm' || confirmDeleteTimer.message?.toLowerCase().includes('despertar')
                  ? 'despertador'
                  : 'timer'}
              </span>
              {confirmDeleteTimer.message ? ` "${confirmDeleteTimer.message}"` : ''}?
              Esta ação não pode ser desfeita.
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteTimer(null)}
                className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)] hover:bg-white/[0.06] hover:text-[color:var(--text-primary)] transition-colors"
              >
                Manter
              </button>
              <button
                onClick={() => deleteTimer(confirmDeleteTimer.id)}
                className="alfredo-pill border-rose-500/30 bg-rose-500/15 text-rose-400 hover:bg-rose-500/25 transition-colors"
              >
                Cancelar timer
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
