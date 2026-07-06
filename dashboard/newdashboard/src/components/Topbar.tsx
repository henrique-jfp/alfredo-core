import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { TimerItem } from '../types';
import { AlarmClock } from 'lucide-react';

export function Topbar({ title, subtitle }: { title: string; subtitle: string }) {
  const [alarms, setAlarms] = useState<TimerItem[]>([]);

  const fetchAlarms = async () => {
    try {
      const data = await api.getTimers();
      const activeAlarms = data.filter(t => t.timer_type === 'alarm' || (t.message && t.message.toLowerCase().includes('despertar')));
      setAlarms(activeAlarms);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchAlarms();
    const timer = setInterval(fetchAlarms, 10000); // Check every 10s
    return () => clearInterval(timer);
  }, []);

  const deleteTimer = async (id: number) => {
    try {
      await fetch(`/api/dashboard/timers/${id}`, { method: 'DELETE' });
      fetchAlarms();
    } catch (e) {
      console.error(e);
    }
  };

  const nextAlarm = alarms.length > 0 ? [...alarms].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime())[0] : null;

  return (
    <header className="flex justify-between items-center py-2 px-1 mb-6">
      <div>
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">{title}</h1>
        <p className="text-[13px] text-zinc-400 mt-1">{subtitle}</p>
      </div>

      <div className="flex items-center gap-6">
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
