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
  RefreshCw,
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
    try {
      await fetch('/api/dashboard/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: commandText }),
      });
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

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pr-2 pb-10">
      <div className="alfredo-card relative overflow-hidden px-5 py-5 md:px-6 md:py-6">
        <div className="absolute right-0 top-0 h-56 w-56 translate-x-1/2 -translate-y-1/2 rounded-full bg-brass-500/10 blur-[80px]" />
        <div className="relative z-10 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="flex flex-col gap-4">
            <div className="alfredo-section-label">Briefing da casa</div>
            <div>
              <h1 className="text-5xl font-semibold tracking-tight text-[color:var(--text-primary)] md:text-6xl" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {time.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                <span className="ml-2 align-baseline text-2xl font-normal text-[color:var(--text-tertiary)] md:text-3xl">
                  {time.toLocaleTimeString('pt-BR', { second: '2-digit' })}
                </span>
              </h1>
              <p className="mt-2 text-[15px] font-medium capitalize text-brass-400">
                {time.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <StatusPulse label="Sistema em escuta" tone="success" />
              <StatusPulse label={`${stats?.active_timers ?? 0} timers vivos`} tone="warning" />
              <StatusPulse label={`${stats?.devices ?? 0} satélites`} tone="info" />
            </div>
          </div>

          <div className="alfredo-card bg-[linear-gradient(180deg,rgba(19,20,23,0.95),rgba(27,29,33,0.95))] p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="alfredo-section-label">Clima</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <div className="text-[40px] font-semibold tracking-tight text-[color:var(--text-primary)]">{weather ? `${weather.temperature}°` : '--°'}</div>
                  <div className="text-[13px] text-[color:var(--text-secondary)]">{weather ? weather.description : 'Buscando...'}</div>
                </div>
                {weather && weather.max_temp !== '—' && (
                  <div className="mt-2 flex gap-3 text-xs font-semibold">
                    <span className="text-rose-400">↑ {weather.max_temp}°</span>
                    <span className="text-blue-400">↓ {weather.min_temp}°</span>
                  </div>
                )}
              </div>
              <div className="shrink-0 drop-shadow-[0_0_15px_rgba(255,255,255,0.08)]">
                {getWeatherIcon(weather?.weather_code ?? -1)}
              </div>
            </div>
            <div className="mt-4 grid gap-3 rounded-2xl border border-white/5 bg-black/20 p-4">
              <div className="flex items-center justify-between text-[12px] text-[color:var(--text-secondary)]">
                <span>Última atualização</span>
                <button
                  onClick={fetchData}
                  className="inline-flex items-center gap-2 rounded-full border border-brass-500/20 bg-brass-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-brass-300 transition-colors hover:bg-brass-500/15"
                >
                  <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
                  Atualizar
                </button>
              </div>
              <div className="font-mono text-[13px] text-[color:var(--text-primary)]">{time.toLocaleTimeString('pt-BR')}</div>
            </div>
          </div>
        </div>
      </div>

      <SpotifyCard />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
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
              recentActivities.map((item) => (
                <div key={item.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.04]">
                  <div className="flex items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">
                    <span className="truncate">{item.room_id} • {item.device_id}</span>
                    <span>{new Date(item.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className="mt-3 flex gap-3">
                    <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-brass-400 shadow-[0_0_12px_rgba(212,162,78,0.25)]" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14px] font-medium text-[color:var(--text-primary)]">{item.input_text}</p>
                      <p className="mt-2 rounded-xl border border-white/5 bg-black/20 px-3 py-2 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
                        {item.output_text}
                      </p>
                    </div>
                  </div>
                </div>
              ))
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
