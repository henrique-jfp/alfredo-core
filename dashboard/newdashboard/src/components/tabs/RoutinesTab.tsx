import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Clock, PlusCircle, HelpCircle, X, Play, Trash2, ChevronRight, Sparkles } from 'lucide-react';
import { Routine, DEFAULT_ROOM, ROOM_LABELS, ROOM_IDS, RoomId } from '../../types';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { Modal } from '../ui/Modal';
import { cn } from '../../lib/utils';

const DAYS = [
  { label: 'D', value: 0 },
  { label: 'S', value: 1 },
  { label: 'T', value: 2 },
  { label: 'Q', value: 3 },
  { label: 'Q', value: 4 },
  { label: 'S', value: 5 },
  { label: 'S', value: 6 },
];

// O Mapeamento exato da casa do usuário
const HOUSE_DEVICES = {
  light: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM, ROOM_IDS.LAURA, ROOM_IDS.OFFICE],
  fan: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM, ROOM_IDS.LAURA],
  tv: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM],
};

export type ActionBlock = {
  id: string;
  device_type: 'light' | 'fan' | 'tv' | 'tts' | 'command';
  location?: RoomId | string;
  state?: 'on' | 'off';
  speed?: 'low' | 'medium' | 'high' | 'off';
  action?: 'power_on' | 'power_off' | 'open_app';
  app_name?: string;
  content?: string;
  text?: string;
};

export function RoutinesTab() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  const [formData, setFormData] = useState<{
    name: string;
    trigger_type: string;
    trigger_value: string;
    room_id: string;
    days_of_week: number[];
    actions_list: ActionBlock[];
  }>({
    name: '',
    trigger_type: 'time',
    trigger_value: '',
    room_id: DEFAULT_ROOM,
    days_of_week: [0, 1, 2, 3, 4, 5, 6],
    actions_list: [],
  });

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
    const confirmed = window.confirm('Tem certeza que deseja excluir esta rotina?');
    if (!confirmed) return;
    try {
      await api.deleteRoutine(id);
      setRoutines(routines.filter((r) => r.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const res = await api.toggleRoutine(id);
      setRoutines(routines.map(r => r.id === id ? { ...r, is_active: res.is_active } : r));
    } catch (e) {
      console.error(e);
    }
  };

  const handleTest = async (id: number) => {
    try {
      await api.testRoutine(id);
      alert('Rotina enviada para execucao!');
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.trigger_value || formData.actions_list.length === 0) return;
    try {
      const payload = {
        name: formData.name,
        trigger_type: formData.trigger_type,
        trigger_value: formData.trigger_value,
        room_id: formData.room_id,
        action_type: 'multi_action',
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        action_value: JSON.stringify(formData.actions_list.map(({id, ...rest}) => rest)),
        days_of_week: formData.days_of_week.join(','),
      };
      const newRoutine = await api.createRoutine(payload);
      setRoutines([newRoutine, ...routines]);
      setFormData({ ...formData, name: '', trigger_value: '', actions_list: [], days_of_week: [0, 1, 2, 3, 4, 5, 6] });
    } catch (e) {
      console.error(e);
    }
  };

  const addAction = () => {
    const newAction: ActionBlock = {
      id: Math.random().toString(36).substring(2, 9),
      device_type: 'light',
      location: formData.room_id,
      state: 'on'
    };
    // Fix location if not available for default device_type (light is available everywhere)
    setFormData({ ...formData, actions_list: [...formData.actions_list, newAction] });
  };

  const updateAction = (id: string, updates: Partial<ActionBlock>) => {
    setFormData({
      ...formData,
      actions_list: formData.actions_list.map(a => {
        if (a.id === id) {
           const merged = { ...a, ...updates };
           // If changing device_type, ensure the current location is valid for it
           if (updates.device_type) {
              const dt = updates.device_type as keyof typeof HOUSE_DEVICES;
              if (HOUSE_DEVICES[dt] && !HOUSE_DEVICES[dt].includes(merged.location as any)) {
                 merged.location = HOUSE_DEVICES[dt][0]; // Fallback to first valid room
              }
           }
           return merged;
        }
        return a;
      })
    });
  };

  const removeAction = (id: string) => {
    setFormData({
      ...formData,
      actions_list: formData.actions_list.filter(a => a.id !== id)
    });
  };

  const formatActionList = (routine: Routine) => {
    if (routine.action_type === 'multi_action') {
      try {
        const actions = JSON.parse(routine.action_value) as ActionBlock[];
        return actions.map((a, i) => {
          if (a.device_type === 'light') return `Luz ${ROOM_LABELS[a.location as RoomId] || a.location} (${a.state === 'on' ? 'Ligar' : 'Desligar'})`;
          if (a.device_type === 'fan') return `Ventilador ${ROOM_LABELS[a.location as RoomId] || a.location} (${a.speed || 'on'})`;
          if (a.device_type === 'tv') return `TV ${ROOM_LABELS[a.location as RoomId] || a.location} (${a.action === 'power_on' ? 'Ligar' : a.action === 'power_off' ? 'Desligar' : 'App'})`;
          if (a.device_type === 'tts') return `Falar: "${a.content}"`;
          if (a.device_type === 'command') return `Comando: "${a.text}"`;
          return a.device_type;
        }).join(' → ');
      } catch {
        return routine.action_value;
      }
    }
    return `Comando simulado: "${routine.action_value}"`;
  };

  return (
    <div className="relative flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <Modal open={showHelp} onClose={() => setShowHelp(false)} title="Como criar rotinas?" maxWidth="max-w-md">
        <ul className="space-y-3 text-sm text-[color:var(--text-secondary)]">
          <li><strong className="text-[color:var(--text-primary)]">Nome:</strong> apenas para você identificar.</li>
          <li><strong className="text-[color:var(--text-primary)]">Horário:</strong> o disparo exato.</li>
          <li><strong className="text-[color:var(--text-primary)]">Sala:</strong> o cômodo onde atua.</li>
          <li><strong className="text-[color:var(--text-primary)]">Blocos de Ação:</strong> adicione comandos estruturados baseados nos cômodos e aparelhos existentes.</li>
        </ul>
      </Modal>

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
                AJUDA
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
                <div key={rt.id} className={cn('alfredo-card p-4 transition-all', !rt.is_active && 'opacity-50 grayscale')}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brass-500/10 text-brass-300">
                          <Clock className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="truncate text-[15px] font-semibold text-[color:var(--text-primary)]">{rt.name}</h3>
                          <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">
                            {ROOM_LABELS[rt.room_id as keyof typeof ROOM_LABELS] || rt.room_id} · {rt.trigger_value}
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
                          {ROOM_LABELS[rt.room_id as keyof typeof ROOM_LABELS] || rt.room_id}
                        </span>
                      </div>

                      <p className="mt-4 rounded-2xl border border-white/5 bg-black/20 px-4 py-3 text-[13px] leading-relaxed text-[color:var(--text-secondary)] truncate">
                        {formatActionList(rt)}
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-col gap-2">
                      <button onClick={() => handleToggle(rt.id)} className="w-full">
                        <StatusPulse label={rt.is_active ? 'Ativa' : 'Pausada'} tone={rt.is_active ? 'success' : 'warning'} />
                      </button>
                      <button
                        onClick={() => handleTest(rt.id)}
                        className="alfredo-pill justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]"
                        aria-label="Executar rotina"
                      >
                        <Play className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(rt.id)}
                        className="alfredo-pill justify-center border-rose-500/20 bg-rose-500/10 text-rose-400"
                        aria-label={`Excluir rotina ${rt.name}`}
                      >
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
                <div className="alfredo-section-label">NOVA ROTINA</div>
                <h2 className="mt-2 text-[18px] font-semibold text-[color:var(--text-primary)]">Criação com preview</h2>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-4">
              <div>
                <label className="alfredo-section-label">NOME DA ROTINA</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} type="text" placeholder="Ex: Bom dia" className="alfredo-input mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="alfredo-section-label">HORÁRIO</label>
                  <input value={formData.trigger_value} onChange={(e) => setFormData({ ...formData, trigger_value: e.target.value })} type="time" className="alfredo-input mt-1" />
                </div>
                <div>
                  <label className="alfredo-section-label">SALA PADRÃO</label>
                  <select value={formData.room_id} onChange={(e) => setFormData({ ...formData, room_id: e.target.value })} className="alfredo-input mt-1 appearance-none cursor-pointer">
                    <option value={ROOM_IDS.LIVING}>Sala de Estar</option>
                    <option value={ROOM_IDS.BEDROOM}>Quarto</option>
                    <option value={ROOM_IDS.LAURA}>Quarto da Laura</option>
                    <option value={ROOM_IDS.OFFICE}>Escritório</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="alfredo-section-label">DIAS DA SEMANA</label>
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
                        aria-label={`${day.label}${isSelected ? ' (selecionado)' : ''}`}
                      >
                        {day.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mt-2 border-t border-white/5 pt-4">
                <label className="alfredo-section-label mb-3 block">BLOCOS DE AÇÃO ({formData.actions_list.length})</label>
                <div className="space-y-3">
                  {formData.actions_list.map((action, idx) => (
                    <div key={action.id} className="alfredo-card p-4 relative flex flex-col gap-3 border border-white/10 bg-white/[0.02]">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-brass-400">Ação {idx + 1}</span>
                        <button onClick={() => removeAction(action.id)} className="text-rose-400/70 hover:text-rose-400 transition-colors">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <select value={action.device_type} onChange={(e) => updateAction(action.id, { device_type: e.target.value as any })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                        <option value="light">Controle de Luz</option>
                        <option value="fan">Ventilador</option>
                        <option value="tv">Televisão</option>
                        <option value="tts">Falar Mensagem (TTS)</option>
                        <option value="command">Comando Livre da IA</option>
                      </select>

                      {action.device_type === 'light' && (
                        <div className="grid grid-cols-2 gap-2">
                          <select value={action.location || formData.room_id} onChange={(e) => updateAction(action.id, { location: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            {HOUSE_DEVICES.light.map(roomId => (
                               <option key={roomId} value={roomId}>{ROOM_LABELS[roomId as RoomId]}</option>
                            ))}
                          </select>
                          <select value={action.state || 'on'} onChange={(e) => updateAction(action.id, { state: e.target.value as 'on'|'off' })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            <option value="on">Ligar</option>
                            <option value="off">Desligar</option>
                          </select>
                        </div>
                      )}

                      {action.device_type === 'fan' && (
                        <div className="grid grid-cols-2 gap-2">
                           <select value={action.location || formData.room_id} onChange={(e) => updateAction(action.id, { location: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                             {HOUSE_DEVICES.fan.map(roomId => (
                               <option key={roomId} value={roomId}>{ROOM_LABELS[roomId as RoomId]}</option>
                             ))}
                          </select>
                          <select value={action.speed || 'medium'} onChange={(e) => updateAction(action.id, { speed: e.target.value as any })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            <option value="off">Desligar</option>
                            <option value="low">Velocidade 1 (Baixa)</option>
                            <option value="medium">Velocidade 2 (Média)</option>
                            <option value="high">Velocidade 3 (Alta)</option>
                          </select>
                        </div>
                      )}

                      {action.device_type === 'tv' && (
                        <div className="grid grid-cols-2 gap-2">
                          <select value={action.location || formData.room_id} onChange={(e) => updateAction(action.id, { location: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                             {HOUSE_DEVICES.tv.map(roomId => (
                               <option key={roomId} value={roomId}>{ROOM_LABELS[roomId as RoomId]}</option>
                             ))}
                          </select>
                          <select value={action.action || 'power_on'} onChange={(e) => updateAction(action.id, { action: e.target.value as any })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            <option value="power_on">Ligar TV</option>
                            <option value="power_off">Desligar TV</option>
                            <option value="open_app">Abrir App</option>
                          </select>
                          {action.action === 'open_app' && (
                            <input value={action.app_name || ''} onChange={(e) => updateAction(action.id, { app_name: e.target.value })} type="text" placeholder="Ex: netflix" className="alfredo-input py-2 text-sm col-span-2" />
                          )}
                        </div>
                      )}

                      {action.device_type === 'tts' && (
                        <input value={action.content || ''} onChange={(e) => updateAction(action.id, { content: e.target.value })} type="text" placeholder="Ex: Bom dia! Hora de acordar." className="alfredo-input py-2 text-sm" />
                      )}

                      {action.device_type === 'command' && (
                        <input value={action.text || ''} onChange={(e) => updateAction(action.id, { text: e.target.value })} type="text" placeholder="Ex: toque musica relaxante" className="alfredo-input py-2 text-sm" />
                      )}
                    </div>
                  ))}
                  
                  <button onClick={addAction} className="alfredo-pill mt-2 w-full justify-center border-dashed border-white/20 text-[color:var(--text-secondary)] hover:bg-white/[0.05] transition-colors">
                    <PlusCircle className="h-4 w-4" />
                    Adicionar Bloco de Ação
                  </button>
                </div>
              </div>

              <button
                onClick={handleSave}
                disabled={formData.actions_list.length === 0}
                className="alfredo-pill mt-4 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.18)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                SALVAR ROTINA
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
