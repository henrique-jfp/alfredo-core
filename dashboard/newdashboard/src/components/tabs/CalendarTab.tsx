import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { CalendarEvent } from '../../types';
import { EmptyState, SectionHeading } from '../ui/DashboardPrimitives';
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Trash2, Plus } from 'lucide-react';

function formatDate(date: Date): string {
  return date.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' });
}

function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function groupByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const groups = new Map<string, CalendarEvent[]>();
  for (const ev of events) {
    const existing = groups.get(ev.date) || [];
    existing.push(ev);
    groups.set(ev.date, existing);
  }
  return groups;
}

export function CalendarTab() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewStart, setViewStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay());
    return d;
  });

  const weekEnd = new Date(viewStart);
  weekEnd.setDate(weekEnd.getDate() + 6);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const startStr = toISODate(viewStart) + 'T00:00:00';
      const endStr = toISODate(weekEnd) + 'T23:59:59';
      const data = await api.getEvents(startStr, endStr);
      setEvents(data.events);
    } catch (e) {
      console.error('Failed to load events', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [viewStart]);

  const goBack = () => {
    const d = new Date(viewStart);
    d.setDate(d.getDate() - 7);
    setViewStart(d);
  };

  const goForward = () => {
    const d = new Date(viewStart);
    d.setDate(d.getDate() + 7);
    setViewStart(d);
  };

  const goToday = () => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay());
    setViewStart(d);
  };

  const grouped = groupByDate(events);
  const days: { date: Date; dateStr: string; label: string }[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(viewStart);
    d.setDate(d.getDate() + i);
    const isToday = toISODate(d) === toISODate(new Date());
    days.push({
      date: d,
      dateStr: toISODate(d),
      label: d.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit' }).replace('.', '')
    });
  }

  const weekLabel = `${viewStart.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long' })} — ${weekEnd.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}`;

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Calendário"
        title="Compromissos e eventos"
        subtitle="Visão semanal dos seus compromissos."
      />

      <div className="alfredo-card p-4 md:p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <button onClick={goBack} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button onClick={goToday} className="alfredo-pill border-brass-500/25 bg-brass-500/10 text-brass-300 text-xs">
              Hoje
            </button>
            <button onClick={goForward} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <span className="text-sm font-medium text-[color:var(--text-secondary)]">{weekLabel}</span>
        </div>

        <div className="grid grid-cols-7 gap-2 mb-6">
          {days.map((day) => {
            const dayEvents = grouped.get(day.dateStr) || [];
            const isToday = day.dateStr === toISODate(new Date());
            return (
              <div key={day.dateStr} className="flex flex-col items-center gap-1">
                <span className={`text-[11px] font-semibold uppercase tracking-wider ${isToday ? 'text-brass-300' : 'text-[color:var(--text-tertiary)]'}`}>
                  {day.label}
                </span>
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${isToday ? 'bg-brass-500 text-[color:var(--bg-base)]' : 'text-[color:var(--text-primary)]'}`}>
                  {day.date.getDate()}
                </div>
                {dayEvents.length > 0 && (
                  <div className="flex gap-0.5">
                    {dayEvents.slice(0, 3).map((_, i) => (
                      <div key={i} className={`h-1.5 w-1.5 rounded-full ${isToday ? 'bg-brass-400' : 'bg-brass-400/50'}`} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-8 text-[color:var(--text-secondary)] text-sm">Carregando...</div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={CalendarDays}
              tone="info"
              title="Nenhum compromisso esta semana"
              description="Use a agenda por voz para marcar compromissos. Ex: 'marca dentista para amanhã às 14h'"
            />
          ) : (
            [...grouped.entries()].map(([dateStr, dayEvents]) => (
              <div key={dateStr}>
                <h4 className="text-sm font-semibold text-[color:var(--text-secondary)] mb-2 capitalize">
                  {new Date(dateStr + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}
                </h4>
                <div className="space-y-2">
                  {dayEvents.map((ev) => (
                    <div key={ev.id} className="flex items-center gap-4 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brass-500/10">
                        <Clock className="h-5 w-5 text-brass-300" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[14px] font-semibold text-[color:var(--text-primary)]">{ev.title}</div>
                        <div className="text-[12px] text-[color:var(--text-tertiary)] mt-0.5">{ev.time}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
