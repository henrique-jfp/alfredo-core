import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../lib/api';
import { CalendarEvent } from '../../types';
import { EmptyState, SectionHeading } from '../ui/DashboardPrimitives';
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Plus, X, Trash2, Link } from 'lucide-react';
import { cn } from '../../lib/utils';

const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function getMonthStart(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function getMonthEnd(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function getMonthGrid(date: Date): { date: Date; isCurrentMonth: boolean }[] {
  const start = getMonthStart(date);
  const end = getMonthEnd(date);
  const startDay = start.getDay();
  const cells: { date: Date; isCurrentMonth: boolean }[] = [];
  const padStart = new Date(start);
  padStart.setDate(padStart.getDate() - startDay);
  for (let i = 0; i < 42; i++) {
    const d = new Date(padStart);
    d.setDate(d.getDate() + i);
    cells.push({ date: d, isCurrentMonth: d.getMonth() === date.getMonth() });
  }
  return cells;
}

export function CalendarTab() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewDate, setViewDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(toISODate(new Date()));
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newTime, setNewTime] = useState('12:00');

  const monthStart = getMonthStart(viewDate);
  const monthEnd = getMonthEnd(viewDate);
  const grid = getMonthGrid(viewDate);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const first = grid[0].date;
      const last = grid[grid.length - 1].date;
      const startStr = toISODate(first) + 'T00:00:00';
      const endStr = toISODate(last) + 'T23:59:59';
      const data = await api.getEvents(startStr, endStr);
      setEvents(data.events);
    } catch (e) {
      console.error('Failed to load events', e);
    } finally {
      setLoading(false);
    }
  }, [viewDate]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  const goPrev = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  const goNext = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
  const goToday = () => {
    setViewDate(new Date());
    setSelectedDate(toISODate(new Date()));
  };

  const eventsByDate = new Map<string, CalendarEvent[]>();
  for (const ev of events) {
    const existing = eventsByDate.get(ev.date) || [];
    existing.push(ev);
    eventsByDate.set(ev.date, existing);
  }

  const selectedEvents = eventsByDate.get(selectedDate) || [];

  const handleCreateEvent = async () => {
    if (!newTitle.trim()) return;
    try {
      await api.createEvent({
        title: newTitle.trim(),
        start_time: `${selectedDate}T${newTime}:00`,
      });
      setNewTitle('');
      setShowCreate(false);
      fetchEvents();
    } catch (e) {
      console.error('Failed to create event', e);
    }
  };

  const handleDeleteEvent = async (id: number) => {
    try {
      await api.deleteEvent(id);
      fetchEvents();
    } catch (e) {
      console.error('Failed to delete event', e);
    }
  };

  const todayStr = toISODate(new Date());
  const isTodaySelected = selectedDate === todayStr;

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Calendário"
        title={`${MONTHS[viewDate.getMonth()]} ${viewDate.getFullYear()}`}
        subtitle="Compromissos e eventos organizados por mês."
        action={
          <button onClick={goToday} className="alfredo-pill border-brass-500/25 bg-brass-500/10 text-brass-300 text-xs px-3">
            Hoje
          </button>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <div className="alfredo-card p-4 md:p-6">
          <div className="flex items-center justify-between mb-5">
            <button onClick={goPrev} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)] p-2">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-semibold text-[color:var(--text-primary)]">
              {MONTHS[viewDate.getMonth()]} {viewDate.getFullYear()}
            </span>
            <button onClick={goNext} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)] p-2">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-7 mb-2">
            {WEEKDAYS.map((day) => (
              <div key={day} className="text-center text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)] py-1">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {grid.map(({ date, isCurrentMonth }, idx) => {
              const dateStr = toISODate(date);
              const dayEvents = eventsByDate.get(dateStr) || [];
              const isToday = dateStr === todayStr;
              const isSelected = dateStr === selectedDate;
              const isWeekend = date.getDay() === 0 || date.getDay() === 6;

              return (
                <button
                  key={idx}
                  onClick={() => setSelectedDate(dateStr)}
                  className={cn(
                    'relative flex flex-col items-center justify-start py-1.5 transition-all duration-150 border border-transparent rounded-lg min-h-[56px]',
                    isSelected && 'border-brass-500/30 bg-brass-500/10',
                    !isSelected && isToday && 'bg-brass-500/5',
                    !isSelected && !isToday && isCurrentMonth && 'hover:bg-white/[0.03]',
                    !isCurrentMonth && 'opacity-20'
                  )}
                >
                  <span className={cn(
                    'text-xs font-semibold leading-none mt-0.5',
                    isToday ? 'text-brass-300' : isSelected ? 'text-brass-200' : isWeekend ? 'text-zinc-500' : 'text-[color:var(--text-primary)]'
                  )}>
                    {date.getDate()}
                  </span>
                  {dayEvents.length > 0 && (
                    <div className="flex flex-wrap gap-0.5 justify-center mt-1 px-0.5">
                      {dayEvents.slice(0, 3).map((ev, i) => {
                        const colors = ['bg-brass-400', 'bg-sky-400', 'bg-rose-400', 'bg-emerald-400', 'bg-violet-400'];
                        return <div key={i} className={cn('h-1 w-1.5 rounded-full', colors[i % colors.length])} title={ev.title} />;
                      })}
                      {dayEvents.length > 3 && (
                        <span className="text-[8px] text-[color:var(--text-tertiary)] leading-none">+{dayEvents.length - 3}</span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="alfredo-card p-4 md:p-5 flex-1">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[color:var(--text-primary)]">
                {new Date(selectedDate + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}
              </h3>
              <button
                onClick={() => setShowCreate(!showCreate)}
                className="alfredo-pill border-brass-500/25 bg-brass-500/10 text-brass-300 text-xs"
              >
                {showCreate ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                {showCreate ? 'Cancelar' : 'Novo'}
              </button>
            </div>

            {showCreate && (
              <div className="mb-4 rounded-2xl border border-brass-500/20 bg-brass-500/5 p-3 space-y-3">
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Título do evento..."
                  className="alfredo-input text-sm"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateEvent()}
                />
                <div className="flex gap-2">
                  <input
                    type="time"
                    value={newTime}
                    onChange={(e) => setNewTime(e.target.value)}
                    className="alfredo-input text-sm w-32"
                  />
                  <button onClick={handleCreateEvent} disabled={!newTitle.trim()} className="alfredo-pill flex-1 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] text-xs disabled:opacity-50">
                    Salvar
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {loading ? (
                <div className="text-center py-8 text-[color:var(--text-secondary)] text-sm">Carregando...</div>
              ) : selectedEvents.length === 0 ? (
                <div className="text-center py-8 text-[color:var(--text-tertiary)] text-xs">
                  Nenhum compromisso neste dia.
                </div>
              ) : (
                selectedEvents.map((ev) => (
                  <div key={ev.id} className="group flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-3 py-2.5 hover:bg-white/[0.04] transition-colors">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brass-500/10">
                      <Clock className="h-4 w-4 text-brass-300" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-semibold text-[color:var(--text-primary)] truncate">{ev.title}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-[color:var(--text-tertiary)]">{ev.time}</span>
                        {ev.room_id === 'google_calendar' && (
                          <Link className="h-3 w-3 text-blue-400" />
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteEvent(ev.id)}
                      className="shrink-0 text-[color:var(--text-tertiary)] hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}