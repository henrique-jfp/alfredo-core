import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { TimerItem } from '../types';
import { AlarmClock, Hourglass, RefreshCw } from 'lucide-react';
import { StatusPulse } from './ui/DashboardPrimitives';

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
      className="alfredo-card alfredo-card-hover flex min-w-[190px] flex-col items-end justify-between p-4 text-right"
      title="Cancelar timer"
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-[26px] font-semibold tracking-wide text-blue-300 tabular-nums">
          {timeLeft}
        </span>
        <Hourglass className="h-5 w-5 text-blue-400 transition-transform group-hover:scale-110" />
      </div>
      <span className="mt-1 max-w-[120px] truncate text-[11px] font-medium uppercase tracking-[0.16em] text-blue-400/70">
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
    <header className="mb-6 flex flex-col gap-4 md:gap-5">
      <div className="alfredo-card overflow-hidden px-4 py-4 md:px-6 md:py-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl">
            <div className="alfredo-section-label mb-2">Briefing do Dia</div>
            <h1 className="alfredo-page-title">{title}</h1>
            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{subtitle}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <StatusPulse label="Sistema online" tone="success" />
            <button
              onClick={() => window.location.reload()}
              className="alfredo-pill border-brass-500/25 bg-brass-500/10 text-brass-300 hover:bg-brass-500/15"
              title="Recarregar Dashboard"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Recarregar
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
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
            className="alfredo-card alfredo-card-hover group flex min-w-[190px] flex-col items-end justify-between p-4 text-right"
            title="Desligar despertador"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-[26px] font-semibold tracking-wide text-brass-300 tabular-nums">
                {new Date(nextAlarm.expires_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </span>
              <AlarmClock className="h-5 w-5 text-brass-400 transition-transform group-hover:scale-110" />
            </div>
            <span className="mt-1 text-[11px] font-medium uppercase tracking-[0.16em] text-brass-400/70">
              Despertador Ativo
            </span>
          </button>
        )}
      </div>
    </header>
  );
}
