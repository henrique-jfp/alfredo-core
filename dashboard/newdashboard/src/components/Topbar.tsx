import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { TimerItem } from '../types';
import { AlarmClock, Hourglass } from 'lucide-react';

function TimerDisplay({ timer, onDelete }: { timer: TimerItem, onDelete: (id: number) => void }) {
  const [timeLeft, setTimeLeft] = useState<string>('');
  
  useEffect(() => {
    const updateTime = () => {
      const now = new Date().getTime();
      const end = new Date(timer.expires_at).getTime();
      const diff = Math.max(0, Math.floor((end - now) / 1000));
      
      const m = Math.floor(diff / 60);
      const s = diff % 60;
      setTimeLeft(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
      
      // If time is up, we can automatically trigger a refresh of timers in the parent,
      // but let's just show 00:00 for now.
    };
    
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [timer.expires_at]);

  return (
    <button 
      onClick={() => {
        if (window.confirm(`Você quer cancelar o timer ${timer.message ? `(${timer.message})` : ''}?`)) {
          onDelete(timer.id);
        }
      }}
      className="flex flex-col items-end leading-tight cursor-pointer group hover:bg-sky-500/5 p-2 rounded-xl transition-colors border border-transparent hover:border-sky-500/20"
      title="Cancelar timer"
    >
      <div className="flex items-center gap-2">
        <span className="text-[26px] font-bold text-sky-400 tracking-wide font-mono tabular-nums">
          {timeLeft}
        </span>
        <Hourglass className="w-5 h-5 text-sky-500 group-hover:scale-110 transition-transform" />
      </div>
      <span className="text-[11px] font-medium text-sky-500/70 capitalize tracking-wide mt-1 truncate max-w-[120px]">
        {timer.message || "Timer Ativo"}
      </span>
    </button>
  );
}

export function Topbar({ title, subtitle }: { title: string; subtitle: string }) {
  const [activeItems, setActiveItems] = useState<TimerItem[]>([]);

  const fetchItems = async () => {
    try {
      const data = await api.getTimers();
      setActiveItems(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchItems();
    const timer = setInterval(fetchItems, 5000); // Check every 5s
    return () => clearInterval(timer);
  }, []);

  const deleteTimer = async (id: number) => {
    try {
      await fetch(`/api/dashboard/timers/${id}`, { method: 'DELETE' });
      fetchItems();
    } catch (e) {
      console.error(e);
    }
  };

  const alarms = activeItems.filter(t => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
  const timers = activeItems.filter(t => t.timer_type === 'timer' && !(t.message && t.message.toLowerCase().includes('despertar')));

  const nextAlarm = alarms.length > 0 ? [...alarms].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime())[0] : null;

  return (
    <header className="flex flex-col md:flex-row md:justify-between items-start md:items-center py-2 px-1 mb-6 gap-4 md:gap-0">
      <div>
        <h1 className="text-[24px] md:text-[28px] font-bold text-zinc-100 tracking-tight">{title}</h1>
        <p className="text-[12px] md:text-[13px] text-zinc-400 mt-1 leading-tight">{subtitle}</p>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 md:gap-6 w-full md:w-auto">
        {/* Active Timers */}
        {timers.map(t => (
          <TimerDisplay key={t.id} timer={t} onDelete={deleteTimer} />
        ))}

        {/* Next Alarm */}
        {nextAlarm && (
          <button 
            onClick={() => {
              if (window.confirm(`Você quer desligar esse despertador (${new Date(nextAlarm.expires_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })})?`)) {
                deleteTimer(nextAlarm.id);
              }
            }}
            className="flex flex-col items-end leading-tight cursor-pointer group hover:bg-amber-500/5 p-2 rounded-xl transition-colors border border-transparent hover:border-amber-500/20"
            title="Desligar despertador"
          >
            <div className="flex items-center gap-2">
              <span className="text-[26px] font-bold text-amber-400 tracking-wide font-mono tabular-nums">
                {new Date(nextAlarm.expires_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </span>
              <AlarmClock className="w-5 h-5 text-amber-500 group-hover:scale-110 transition-transform" />
            </div>
            <span className="text-[11px] font-medium text-amber-500/70 capitalize tracking-wide mt-1">
              Despertador Ativo
            </span>
          </button>
        )}

        {/* Refresh Button */}
        <button 
          onClick={() => window.location.reload()}
          className="flex items-center justify-center p-2.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-all text-zinc-400 hover:text-white cursor-pointer active:scale-95"
          title="Recarregar Dashboard"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>

        {/* Status Indicator */}
        <div className="flex items-center gap-2.5 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 rounded-full">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
          </div>
          <span className="text-[12.5px] font-semibold text-emerald-400 tracking-wide">Sistema Online</span>
        </div>
      </div>
    </header>
  );
}
