import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../../lib/api';
import { Stats, HistoryItem, ListItem, TimerItem, Weather } from '../../types';
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

type WidgetKey = 'compras' | 'tarefas' | 'lembretes';
const RIO_TIME_ZONE = 'America/Sao_Paulo';

function formatRio(date: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: RIO_TIME_ZONE, ...options }).format(date);
}

function formatCountdown(expiresAt: string) {
  const now = Date.now();
  const end = new Date(expiresAt).getTime();
  const diff = Math.max(0, Math.floor((end - now) / 1000));
  const minutes = Math.floor(diff / 60);
  const seconds = diff % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function getWeatherKind(code: number) {
  if (code <= 1) return 'sun';
  if (code <= 3) return 'cloud';
  if (code <= 69 || (code >= 80 && code <= 82)) return 'rain';
  if (code >= 71 && code <= 77) return 'snow';
  if (code >= 95) return 'storm';
  return 'cloud';
}

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
        'group flex min-w-0 flex-col justify-between rounded-3xl border p-4 text-left transition-all duration-200 hover:-translate-y-0.5',
        accent,
        glow
      )}
      title={label}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="alfredo-section-label mb-2 text-[10px]">{label}</div>
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

  const fetchData = async () => {
    setIsRefreshing(true);
    const [statsData, historyData, listsData, timersData, weatherData] = await Promise.all([
      api.getStats(),
      api.getHistory(),
      api.getLists(),
      api.getTimers(),
      api.getWeather().catch(() => null),
    ]);
    setStats(statsData);
    setHistory(historyData);
    setLists(listsData);
    setTimers(timersData);
    if (weatherData) setWeather(weatherData);
    setTimeout(() => setIsRefreshing(false), 450);
  };

  useEffect(() => {
    fetchData();
    const dataInterval = setInterval(fetchData, 10000);
    const clockInterval = setInterval(() => setTime(new Date()), 1000);
    return () => {
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, []);

  const handleCommandSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!commandText.trim()) return;

    setIsSending(true);
    const startedAt = performance.now();
    try {
      await fetch('/api/dashboard/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: commandText }),
      });
      setLastCommandLatencyMs(Math.max(0, Math.round(performance.now() - startedAt)));
      setCommandText('');
      fetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSending(false);
    }
  };

  const deleteTimer = async (id: number) => {
    try {
      await api.deleteTimer(id);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const alarms = timers.filter((t) => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
  const nextAlarm = alarms.length > 0 ? [...alarms].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime())[0] : null;

  const getWeatherIcon = (code: number) => {
    if (code === undefined) return <Sun className="h-12 w-12 animate-[spin_20s_linear_infinite] text-brass-400" />;
    if (code <= 1) return <Sun className="h-12 w-12 animate-[spin_20s_linear_infinite] text-brass-400" />;
    if (code <= 3) return <Cloud className="h-12 w-12 animate-[pulse_4s_ease-in-out_infinite] text-zinc-300" />;
    if (code <= 69 || (code >= 80 && code <= 82)) return <CloudRain className="h-12 w-12 animate-[bounce_2s_infinite] text-blue-400" />;
    if (code >= 71 && code <= 77) return <CloudSnow className="h-12 w-12 animate-pulse text-white" />;
    if (code >= 95) return <CloudLightning className="h-12 w-12 animate-[pulse_1s_ease-in-out_infinite] text-yellow-400" />;
    return <Cloud className="h-12 w-12 text-zinc-300" />;
  };

  const recentActivities = useMemo(() => history.slice(0, 6), [history]);
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

  const weatherCode = weather?.weather_code ?? -1;
  const weatherKind = getWeatherKind(weatherCode);
  const activeTimers = timers.filter((t) => t.timer_type === 'timer' && !(t.message && t.message.toLowerCase().includes('despertar')));
  const activeAlarms = alarms;
  const hasPinnedTimers = activeTimers.length > 0 || activeAlarms.length > 0;
  const pinnedTimers =
    activeTimers.length > 0 && activeAlarms.length > 0
      ? [activeTimers[0], activeAlarms[0]]
      : activeTimers.length > 0
        ? activeTimers.slice(0, 2)
        : activeAlarms.slice(0, 2);

  const weatherTitle =
    weatherKind === 'sun' ? 'Ensolarado' :
    weatherKind === 'cloud' ? 'Nublado' :
    weatherKind === 'rain' ? 'Chuva' :
    weatherKind === 'snow' ? 'Neve' : 'Tempestade';

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pr-2 pb-10">
      {/* NOVO CABEÇALHO (Relógio + Timers + Clima) */}
      <div className="flex flex-col xl:flex-row w-full items-start xl:items-stretch justify-between gap-5 xl:gap-8 mb-2">
        
        {/* Esquerda: Relógio */}
        <div className="flex flex-col justify-center xl:min-w-[340px]">
          <div className="alfredo-section-label mb-2">Visão Geral</div>
          <div className="text-[12px] uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
            {formatRio(time, { weekday: 'long', day: '2-digit', month: 'long' })}
          </div>
          <h1 className="mt-2 text-7xl font-semibold leading-none tracking-tight text-[color:var(--text-primary)] md:text-[92px]" style={{ fontVariantNumeric: 'tabular-nums' }}>
            {formatRio(time, { hour: '2-digit', minute: '2-digit' })}
          </h1>
          <div className="mt-3 flex items-end gap-3">
            <span className="font-mono text-[18px] text-[color:var(--text-tertiary)] md:text-[22px]">
              {formatRio(time, { second: '2-digit' })}
            </span>
            <span className="pb-0.5 text-[15px] font-medium capitalize text-brass-400 md:text-[16px]">
              Briefing do Dia
            </span>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            <StatusPulse label="Sistema em escuta" tone="success" />
            <StatusPulse label={`${stats?.active_timers ?? 0} timers vivos`} tone="warning" />
            <StatusPulse label={`${stats?.devices ?? 0} satélites`} tone="info" />
          </div>
        </div>

        {/* Centro: Timers (se existirem) */}
        {hasPinnedTimers && (
          <div className="flex-1 w-full flex items-center justify-center">
            <div className="grid gap-3 w-full max-w-lg md:grid-cols-2">
              {pinnedTimers.map((timer) => (
                <div key={timer.id} className="min-w-0">
                  <TimerCard timer={timer} onDelete={deleteTimer} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Direita: Clima */}
        <div className="flex-shrink-0 w-full xl:w-[380px]">
          <div className="relative h-full overflow-hidden rounded-3xl border border-white/5 bg-[linear-gradient(180deg,rgba(19,20,23,0.95),rgba(27,29,33,0.95))] p-5 md:p-6">
          <div className={cn(
            'absolute inset-0 pointer-events-none opacity-100',
            weatherKind === 'sun' && 'bg-[radial-gradient(circle_at_70%_20%,rgba(212,162,78,0.22),transparent_34%),radial-gradient(circle_at_40%_80%,rgba(212,162,78,0.08),transparent_32%)]',
            weatherKind === 'cloud' && 'bg-[radial-gradient(circle_at_60%_22%,rgba(255,255,255,0.09),transparent_30%)]',
            weatherKind === 'rain' && 'bg-[radial-gradient(circle_at_50%_10%,rgba(96,165,250,0.14),transparent_36%)]',
            weatherKind === 'snow' && 'bg-[radial-gradient(circle_at_50%_10%,rgba(255,255,255,0.14),transparent_36%)]',
            weatherKind === 'storm' && 'bg-[radial-gradient(circle_at_50%_15%,rgba(245,158,11,0.16),transparent_32%)]'
          )} />
          <div className="relative flex h-full flex-col justify-between gap-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="alfredo-section-label">Meteorologia</div>
                <div className="mt-2 text-[15px] font-semibold tracking-wide text-[color:var(--text-primary)]">{weatherTitle}</div>
                <div className="mt-1 text-[13px] text-[color:var(--text-secondary)]">{weather ? weather.description : 'Buscando...'}</div>
              </div>

              <div className="shrink-0 drop-shadow-[0_0_18px_rgba(255,255,255,0.12)]">
                <div className={cn(
                  'flex h-20 w-20 items-center justify-center rounded-full border',
                  weatherKind === 'sun' && 'border-brass-500/20 bg-brass-500/10 text-brass-300 shadow-[0_0_30px_rgba(212,162,78,0.14)]',
                  weatherKind === 'cloud' && 'border-white/10 bg-white/[0.03] text-zinc-300',
                  weatherKind === 'rain' && 'border-blue-500/20 bg-blue-500/10 text-blue-400',
                  weatherKind === 'snow' && 'border-white/10 bg-white/[0.03] text-white',
                  weatherKind === 'storm' && 'border-amber-500/20 bg-amber-500/10 text-yellow-400'
                )}>
                  <div className={cn(
                    weatherKind === 'sun' && 'animate-[spin_20s_linear_infinite]',
                    weatherKind === 'cloud' && 'animate-[pulse_4s_ease-in-out_infinite]',
                    weatherKind === 'rain' && 'animate-[bounce_2s_infinite]',
                    weatherKind === 'snow' && 'animate-pulse',
                    weatherKind === 'storm' && 'animate-[pulse_1s_ease-in-out_infinite]'
                  )}>
                    {getWeatherIcon(weatherCode)}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-3 rounded-2xl border border-white/5 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-[40px] font-semibold tracking-tight text-[color:var(--text-primary)]">
                  {weather ? `${weather.temperature}°` : '--°'}
                </div>
                <div className="text-right text-[12px] text-[color:var(--text-secondary)]">
                  <div>Máx. <span className="font-semibold text-rose-400">{weather?.max_temp ?? '--'}°</span></div>
                  <div>Mín. <span className="font-semibold text-blue-400">{weather?.min_temp ?? '--'}°</span></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[12px] text-[color:var(--text-secondary)]">
                <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                  Umidade: {weather?.humidity ?? '--'}%
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                  {weather ? 'Atualizado agora' : 'Aguardando leitura'}
                </div>
              </div>
            </div>
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
            subtitle="A tela vira briefing: menos log cru, mais contexto útil."
            action={
              <button className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                Ver histórico completo
              </button>
            }
          />

          <form onSubmit={handleCommandSubmit} className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
            <input
              type="text"
              value={commandText}
              onChange={(e) => setCommandText(e.target.value)}
              disabled={isSending}
              placeholder="Comando rápido para o Alfredo..."
              className="alfredo-input"
            />
            <button
              type="submit"
              disabled={isSending || !commandText.trim()}
              className="alfredo-pill justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.18)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Mic className="h-4 w-4" />
              Enviar
            </button>
          </form>

          <div className="mt-5 flex min-h-0 flex-col gap-2 overflow-y-auto pr-1">
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
                        {isLatest && lastCommandLatencyMs !== null && (
                          <span className="rounded-full border border-white/5 bg-black/30 px-2 py-0.5 text-[9px] tracking-[0.16em] text-[color:var(--text-secondary)]">
                            Latência {lastCommandLatencyMs} ms
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 flex gap-3">
                      <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-brass-400 shadow-[0_0_12px_rgba(212,162,78,0.25)]" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-medium text-[color:var(--text-primary)]">{item.input_text}</p>
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
            eyebrow="Widgets rápidos"
            title="Compras, tarefas e lembretes"
            subtitle="Um único bloco com abas internas evita três cards vazios competindo por altura."
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
                  <span className="rounded-full bg-black/25 px-2 py-0.5 text-[10px] font-semibold">{widgetCounts[item.key]}</span>
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
                  lists.compras.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                      <div className="h-2 w-2 rounded-full bg-brass-400" />
                      <span className="truncate text-[14px] text-[color:var(--text-primary)]">{item.content}</span>
                    </div>
                  ))
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
    </div>
  );
}
