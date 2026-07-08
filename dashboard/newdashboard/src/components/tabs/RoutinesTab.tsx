import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Clock, PlusCircle, HelpCircle, X, Play, Trash2, ChevronRight, Sparkles } from 'lucide-react';
import { Routine } from '../../types';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { cn } from '../../lib/utils';

export function RoutinesTab() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    trigger_type: 'time',
    trigger_value: '',
    action_type: 'command',
    action_value: '',
    room_id: 'ROOM_LIVING',
    days_of_week: [0, 1, 2, 3, 4, 5, 6],
  });

  const DAYS = [
    { label: 'D', value: 0 },
    { label: 'S', value: 1 },
    { label: 'T', value: 2 },
    { label: 'Q', value: 3 },
    { label: 'Q', value: 4 },
    { label: 'S', value: 5 },
    { label: 'S', value: 6 },
  ];

  useEffect(() => {
    fetchRoutines();
  }, []);

  const fetchRoutines = async () => {
    try {
      const data = await api.getRoutines();
      setRoutines(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteRoutine(id);
      setRoutines(routines.filter((r) => r.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.trigger_value || !formData.action_value) return;
    try {
      const payload = {
        ...formData,
        days_of_week: formData.days_of_week.join(','),
      };
      const newRoutine = await api.createRoutine(payload);
      setRoutines([newRoutine, ...routines]);
      setFormData({ ...formData, name: '', trigger_value: '', action_value: '', days_of_week: [0, 1, 2, 3, 4, 5, 6] });
    } catch (e) {
      console.error(e);
    }
  };

  const preview = `${formData.days_of_week.length === 7 ? 'Todos os dias' : `${formData.days_of_week.length} dia(s)`}, às ${formData.trigger_value || '07:00'}, em ${formData.room_id === 'ROOM_LIVING' ? 'Sala de Estar' : 'Quarto'}, executo: "${formData.action_value || '...' }"`;

  return (
    <div className="relative flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      {showHelp && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm rounded-2xl">
          <div className="alfredo-card relative max-w-md w-full p-6 shadow-2xl">
            <button onClick={() => setShowHelp(false)} className="absolute right-4 top-4 text-[color:var(--text-tertiary)] hover:text-[color:var(--text-primary)]">
              <X className="h-5 w-5" />
            </button>
            <h3 className="mb-4 flex items-center gap-2 text-[18px] font-semibold text-brass-400">
              <HelpCircle className="h-5 w-5" /> Como criar rotinas?
            </h3>
            <ul className="space-y-3 text-sm text-[color:var(--text-secondary)]">
              <li><strong className="text-[color:var(--text-primary)]">Nome:</strong> apenas para você identificar.</li>
              <li><strong className="text-[color:var(--text-primary)]">Horário:</strong> o disparo exato.</li>
              <li><strong className="text-[color:var(--text-primary)]">Sala:</strong> o cômodo onde atua.</li>
              <li><strong className="text-[color:var(--text-primary)]">Comando:</strong> o que o Alfredo vai executar.</li>
            </ul>
          </div>
        </div>
      )}

      <SectionHeading
        eyebrow="Automação"
        title="Rotinas automáticas"
        subtitle="A tela deixou de ser um formulário isolado e virou uma composição de lista, preview e criação."
        action={<StatusPulse label="Agendamento ativo" tone="success" />}
      />

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Minhas rotinas"
            title="Execuções salvas"
            subtitle="Quando o espaço está vazio, ele explica o próximo passo e não apenas reclama da ausência."
            action={
              <button onClick={() => setShowHelp(true)} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                <HelpCircle className="h-3.5 w-3.5" />
                Ajuda
              </button>
            }
          />

          <div className="mt-5 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {routines.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                tone="brass"
                title="Crie sua primeira rotina"
                description="O Alfredo passa a agir sozinho nos horários certos assim que você salva a primeira automação."
                className="flex-1"
              />
            ) : (
              routines.map((rt) => (
                <div key={rt.id} className={cn('alfredo-card p-4', !rt.is_active && 'opacity-55 grayscale')}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brass-500/10 text-brass-300">
                          <Clock className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="truncate text-[15px] font-semibold text-[color:var(--text-primary)]">{rt.name}</h3>
                          <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">
                            {rt.room_id === 'ROOM_LIVING' ? 'Sala de Estar' : 'Quarto'} · {rt.trigger_value}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <span className="alfredo-pill border-brass-500/20 bg-brass-500/10 text-brass-300">
                          <Clock className="h-3.5 w-3.5" />
                          {rt.trigger_value}
                        </span>
                        <span className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                          <ChevronRight className="h-3.5 w-3.5" />
                          {rt.days_of_week ? (rt.days_of_week.split(',').length === 7 ? 'Todos os dias' : `${rt.days_of_week.split(',').length} dia(s)`) : 'Todos os dias'}
                        </span>
                        <span className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                          {rt.room_id === 'ROOM_LIVING' ? 'Sala de Estar' : 'Quarto'}
                        </span>
                      </div>

                      <p className="mt-4 rounded-2xl border border-white/5 bg-black/20 px-4 py-3 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
                        "{rt.action_value}"
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-col gap-2">
                      <StatusPulse label={rt.is_active ? 'Ativa' : 'Pausada'} tone={rt.is_active ? 'success' : 'warning'} />
                      <button className="alfredo-pill justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                        <Play className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDelete(rt.id)} className="alfredo-pill justify-center border-rose-500/20 bg-rose-500/10 text-rose-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-5">
          <div className="alfredo-card p-5 md:p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="alfredo-section-label">Nova rotina</div>
                <h2 className="mt-2 text-[18px] font-semibold text-[color:var(--text-primary)]">Criação com preview</h2>
              </div>
              <button onClick={() => setShowHelp(true)} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]" title="Como usar">
                <HelpCircle className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="mt-5 flex flex-col gap-4">
              <div>
                <label className="alfredo-section-label">Nome da rotina</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} type="text" placeholder="Ex: Bom dia" className="alfredo-input mt-1" />
              </div>
              <div>
                <label className="alfredo-section-label">Horário</label>
                <input value={formData.trigger_value} onChange={(e) => setFormData({ ...formData, trigger_value: e.target.value })} type="time" className="alfredo-input mt-1" />
              </div>
              <div>
                <label className="alfredo-section-label">Dias da semana</label>
                <div className="mt-2 grid grid-cols-7 gap-2">
                  {DAYS.map((day) => {
                    const isSelected = formData.days_of_week.includes(day.value);
                    return (
                      <button
                        key={day.value}
                        onClick={() => {
                          const newDays = isSelected
                            ? formData.days_of_week.filter((d) => d !== day.value)
                            : [...formData.days_of_week, day.value].sort();
                          setFormData({ ...formData, days_of_week: newDays });
                        }}
                        className={cn(
                          'h-9 rounded-xl border text-xs font-semibold transition-colors',
                          isSelected
                            ? 'border-brass-500/30 bg-brass-500/15 text-brass-300'
                            : 'border-white/5 bg-white/[0.03] text-[color:var(--text-tertiary)] hover:bg-white/[0.05]'
                        )}
                      >
                        {day.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label className="alfredo-section-label">Sala</label>
                <select value={formData.room_id} onChange={(e) => setFormData({ ...formData, room_id: e.target.value })} className="alfredo-input mt-1 appearance-none cursor-pointer">
                  <option value="ROOM_LIVING">Sala de Estar</option>
                  <option value="ROOM_BEDROOM">Quarto</option>
                </select>
              </div>
              <div>
                <label className="alfredo-section-label">Comando simulado</label>
                <input value={formData.action_value} onChange={(e) => setFormData({ ...formData, action_value: e.target.value })} type="text" placeholder="Ex: como está o clima" className="alfredo-input mt-1" />
              </div>

              <button
                onClick={handleSave}
                className="alfredo-pill mt-2 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.18)]"
              >
                <PlusCircle className="h-4 w-4" />
                Salvar rotina
              </button>
            </div>
          </div>

          <div className="alfredo-card p-5 md:p-6">
            <div className="alfredo-section-label">Preview ao vivo</div>
            <div className="mt-2 text-[18px] font-semibold text-[color:var(--text-primary)]">O que vai acontecer</div>
            <p className="mt-3 rounded-2xl border border-white/5 bg-black/20 px-4 py-4 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
              {preview}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
