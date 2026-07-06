import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Stats, HistoryItem, ListItem, TimerItem, Weather } from '../../types';
import { MessageSquare, Clock, Cpu, Zap, ShoppingCart, CheckSquare, Bell, Mic, RefreshCw, Sun, Cloud, CloudRain, CloudLightning, CloudSnow, AlarmClock } from 'lucide-react';
import { cn } from '../../lib/utils';
import { SpotifyCard } from '../SpotifyCard';

export function OverviewTab() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [lists, setLists] = useState<{ compras: ListItem[]; tarefas: ListItem[] }>({ compras: [], tarefas: [] });
  const [timers, setTimers] = useState<TimerItem[]>([]);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [time, setTime] = useState(new Date());

  const fetchData = async () => {
    setIsRefreshing(true);
    const [statsData, historyData, listsData, timersData, weatherData] = await Promise.all([
      api.getStats(),
      api.getHistory(),
      api.getLists(),
      api.getTimers(),
      api.getWeather().catch(() => null)
    ]);
    setStats(statsData);
    setHistory(historyData);
    setLists(listsData);
    setTimers(timersData);
    if (weatherData) setWeather(weatherData);
    setTimeout(() => setIsRefreshing(false), 500); // Visual feedback
  };

  const [commandText, setCommandText] = useState("");
  const [isSending, setIsSending] = useState(false);

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
        body: JSON.stringify({ command: commandText })
      });
      setCommandText("");
      fetchData(); // Refresh history
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

  const alarms = timers.filter(t => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
  const nextAlarm = alarms.length > 0 ? [...alarms].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime())[0] : null;

  const kpis = [
    { label: 'Conversas', value: stats?.interactions || '—', icon: MessageSquare, color: 'text-indigo-400', bg: 'bg-indigo-400/10' },
    { label: 'Timers Ativos', value: stats?.active_timers ?? '—', icon: Clock, color: 'text-teal-400', bg: 'bg-teal-400/10' },
    { label: 'Satélites', value: stats?.devices || '—', icon: Cpu, color: 'text-rose-400', bg: 'bg-rose-400/10' },
    { label: 'Requisições IA', value: stats?.ai_requests?.toLocaleString('pt-BR') || '—', subLabel: `Tokens: ${stats?.tokens_used?.toLocaleString('pt-BR') || 0}`, icon: Zap, color: 'text-brass-300', bg: 'bg-brass-400/10' },
  ];

  const getWeatherIcon = (code: number) => {
    if (code === undefined) return <Sun className="w-12 h-12 text-brass-400 animate-[spin_10s_linear_infinite]" />;
    if (code <= 1) return <Sun className="w-12 h-12 text-brass-400 animate-[spin_20s_linear_infinite]" />;
    if (code <= 3) return <Cloud className="w-12 h-12 text-zinc-300 animate-[pulse_4s_ease-in-out_infinite]" />;
    if (code <= 69 || (code >= 80 && code <= 82)) return <CloudRain className="w-12 h-12 text-blue-400 animate-[bounce_2s_infinite]" />;
    if (code >= 71 && code <= 77) return <CloudSnow className="w-12 h-12 text-white animate-pulse" />;
    if (code >= 95) return <CloudLightning className="w-12 h-12 text-yellow-400 animate-[pulse_1s_ease-in-out_infinite]" />;
    return <Cloud className="w-12 h-12 text-zinc-300" />;
  };

  return (
    <div className="flex flex-col gap-5 h-full overflow-y-auto pr-2 pb-10">
      
      {/* Top Widget: Clock & Weather */}
      <div className="flex items-center justify-between bg-gradient-to-br from-white/[0.05] to-transparent border border-white/5 rounded-3xl p-6 shadow-2xl relative overflow-hidden">
         {/* Background Glow */}
         <div className="absolute top-0 right-0 w-64 h-64 bg-brass-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3" />
         
         <div className="flex flex-col z-10">
            <h1 className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 to-zinc-500 tracking-tighter" style={{ fontVariantNumeric: 'tabular-nums' }}>
              {time.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              <span className="text-3xl text-zinc-600 font-normal ml-2 tracking-normal">{time.toLocaleTimeString('pt-BR', { second: '2-digit' })}</span>
            </h1>
            <p className="text-lg font-medium text-brass-500 mt-2 capitalize">
              {time.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}
            </p>
         </div>

         <div className="flex items-center gap-4 z-10">
            <div className="flex items-center gap-6 bg-black/40 p-4 rounded-2xl border border-white/5">
                <div className="flex flex-col items-end">
                   <span className="text-3xl font-bold text-zinc-100">{weather ? `${weather.temperature}°` : '--°'}</span>
                   <span className="text-sm font-medium text-zinc-400 capitalize">{weather ? weather.description : 'Buscando...'}</span>
                   {weather && weather.max_temp !== "—" && (
                     <div className="flex gap-3 text-xs font-bold mt-1">
                       <span className="text-rose-400">↑ {weather.max_temp}°</span>
                       <span className="text-blue-400">↓ {weather.min_temp}°</span>
                     </div>
                   )}
                </div>
                <div className="w-[2px] h-12 bg-white/10 rounded-full mx-2" />
                <div className="shrink-0 drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                   {getWeatherIcon(weather?.weather_code ?? -1)}
                </div>
            </div>
         </div>
      </div>

      <SpotifyCard />

      {/* KPI Grid */}
      <div className="grid grid-cols-4 gap-4">

        {kpis.map((kpi, idx) => (
          <div key={idx} className="glass-panel glass-panel-hover p-6 flex items-start gap-4 group">
            <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-110", kpi.bg, kpi.color)}>
              <kpi.icon className="w-5 h-5" strokeWidth={2.5} />
            </div>
            <div className="flex flex-col">
              <span className="text-[11.5px] font-semibold text-zinc-500 uppercase tracking-widest">{kpi.label}</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-bold text-zinc-100 tracking-tight">{kpi.value}</span>
                {kpi.subLabel && <span className="text-xs font-bold text-zinc-500">{kpi.subLabel}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-[1.8fr_1fr] gap-5 flex-grow min-h-0">
        
        {/* History Section */}
        <section className="glass-panel flex flex-col p-6 h-[calc(100vh-280px)]">
          <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
            <h2 className="text-[15px] font-semibold text-zinc-100 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brass-400" />
              Conversas Recentes
            </h2>
            <div className="flex items-center gap-3">
              <form onSubmit={handleCommandSubmit} className="relative">
                <input 
                  type="text" 
                  value={commandText}
                  onChange={(e) => setCommandText(e.target.value)}
                  disabled={isSending}
                  placeholder="Comando rápido..." 
                  className="bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-brass-500/50 focus:ring-1 focus:ring-brass-500/50 transition-all w-64"
                />
                <button 
                  type="submit"
                  disabled={isSending || !commandText.trim()}
                  className="absolute right-2 top-1.5 p-1 rounded hover:bg-white/10 text-zinc-400 transition-colors disabled:opacity-50"
                >
                  <Mic className="w-4 h-4" />
                </button>
              </form>
              <button 
                onClick={fetchData}
                className="flex items-center gap-2 bg-white/5 border border-white/10 hover:bg-white/10 px-3 py-2 rounded-lg text-sm font-medium text-zinc-300 transition-all"
              >
                <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
                Atualizar
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-3 overflow-y-auto pr-2 custom-scrollbar flex-grow">
            {history.length === 0 ? (
              <div className="text-zinc-500 italic text-center py-10 text-sm">Nenhuma conversa registrada.</div>
            ) : (
              history.map(item => (
                <div key={item.id} className="flex flex-col gap-2 p-4 rounded-xl bg-white/[0.015] border border-white/[0.04] hover:bg-white/[0.03] transition-colors">
                  <div className="flex justify-between text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    <span>{item.room_id} • {item.device_id}</span>
                    <span>{new Date(item.timestamp).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'})}</span>
                  </div>
                  <div className="text-[14px] font-medium text-zinc-100 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-brass-400 shrink-0" />
                    {item.input_text}
                  </div>
                  <div className="text-[13px] text-zinc-400 bg-white/5 p-3 rounded-lg border-l-2 border-brass-500/40 leading-relaxed mt-1">
                    {item.output_text}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Lists Column */}
        <div className="flex flex-wrap lg:flex-col gap-5 h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar">
          {/* Shopping */}
          <div className="glass-panel p-5 flex-1 min-w-[300px] flex flex-col min-h-[150px]">
            <h2 className="text-[14px] font-semibold text-zinc-100 flex items-center gap-2 border-b border-white/5 pb-3 mb-3 shrink-0">
              <ShoppingCart className="w-4 h-4 text-brass-400" />
              Compras
            </h2>
            <ul className="flex flex-col gap-1.5 overflow-y-auto custom-scrollbar flex-grow pr-2">
              {lists.compras.length === 0 ? (
                <li className="text-zinc-500 text-sm italic py-4 text-center">Nenhum item.</li>
              ) : (
                lists.compras.map(item => (
                  <li key={item.id} className="px-3 py-2 bg-white/[0.02] border border-white/5 rounded-lg text-[13px] text-zinc-300 flex items-center gap-3">
                    <div className="w-1 h-1 rounded-full bg-brass-400" />
                    {item.content}
                  </li>
                ))
              )}
            </ul>
          </div>

          {/* Tasks */}
          <div className="glass-panel p-5 flex-1 min-w-[300px] flex flex-col min-h-[150px]">
            <h2 className="text-[14px] font-semibold text-zinc-100 flex items-center gap-2 border-b border-white/5 pb-3 mb-3 shrink-0">
              <CheckSquare className="w-4 h-4 text-brass-400" />
              Tarefas
            </h2>
            <ul className="flex flex-col gap-1.5 overflow-y-auto custom-scrollbar flex-grow pr-2">
              {lists.tarefas.length === 0 ? (
                <li className="text-zinc-500 text-sm italic py-4 text-center">Nenhuma tarefa.</li>
              ) : (
                lists.tarefas.map(item => (
                  <li key={item.id} className="px-3 py-2 bg-white/[0.02] border border-white/5 rounded-lg text-[13px] text-zinc-300 flex items-center gap-3">
                    <div className="w-1 h-1 rounded-full bg-brass-400" />
                    {item.content}
                  </li>
                ))
              )}
            </ul>
          </div>

          {/* Timers */}
          <div className="glass-panel p-5 flex-1 min-w-[300px] flex flex-col min-h-[150px]">
            <h2 className="text-[14px] font-semibold text-zinc-100 flex items-center gap-2 border-b border-white/5 pb-3 mb-3 shrink-0">
              <Bell className="w-4 h-4 text-brass-400" />
              Lembretes Ativos
            </h2>
            <ul className="flex flex-col gap-1.5 overflow-y-auto custom-scrollbar flex-grow pr-2">
              {timers.length === 0 ? (
                <li className="text-zinc-500 text-sm italic py-4 text-center">Nenhum lembrete.</li>
              ) : (
                timers.map(timer => {
                  const timeStr = new Date(timer.expires_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                  return (
                    <li key={timer.id} className="px-3 py-2 bg-white/[0.02] border border-white/5 rounded-lg text-[13px] text-zinc-300 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                         <div className="w-1 h-1 rounded-full bg-brass-400" />
                         <span className="font-semibold text-brass-300">{timeStr}</span>
                         <span className="truncate max-w-[120px]">{timer.message}</span>
                      </div>
                    </li>
                  )
                })
              )}
            </ul>
          </div>
        </div>

      </div>
    </div>
  );
}
