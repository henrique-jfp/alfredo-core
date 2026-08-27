import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Clock, PlusCircle, HelpCircle, X, Play, Trash2, ChevronRight, Sparkles, MessageSquare } from 'lucide-react';
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

const HOUSE_DEVICES = {
  light: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM, ROOM_IDS.LAURA, ROOM_IDS.OFFICE],
  fan: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM, ROOM_IDS.LAURA],
  tv: [ROOM_IDS.LIVING, ROOM_IDS.BEDROOM],
};

type ActionCategory = 'smart_home' | 'climate' | 'news' | 'music' | 'calendar' | 'web_search' | 'safety' | 'custom_prompt';

export type ActionBlock = {
  id: string;
  category: ActionCategory;
  // Smart Home
  location?: RoomId | string;
  device_type?: 'light' | 'fan' | 'tv';
  action?: string;
  app_name?: string;
  color_name?: string;
  // Weather
  weather_type?: 'current' | 'forecast';
  // Music
  music_query?: string;
  // Web Search
  search_query?: string;
  // Safety
  safety_areas?: string;
  // Custom
  prompt_text?: string;
};

export function RoutinesTab() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  const [formData, setFormData] = useState<{
    name: string;
    trigger_value: string;
    room_id: string;
    days_of_week: number[];
    actions_list: ActionBlock[];
  }>({
    name: '',
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
      alert('Rotina enviada para execução!');
    } catch (e) {
      console.error(e);
    }
  };

  const generatePromptFromBlocks = (blocks: ActionBlock[]): string => {
    const sentences: string[] = [];
    for (const block of blocks) {
      if (block.category === 'smart_home') {
        const roomName = ROOM_LABELS[block.location as RoomId] || block.location || 'o cômodo';
        const art = roomName === 'Sala de Estar' ? 'da ' : 'do ';
        
        if (block.device_type === 'light') {
          if (block.action === 'change_color' && block.color_name) sentences.push(`Mude a cor da luz ${art}${roomName} para ${block.color_name}.`);
          else if (block.action === 'power_off') sentences.push(`Desligue a luz ${art}${roomName}.`);
          else sentences.push(`Ligue a luz ${art}${roomName}.`);
        } else if (block.device_type === 'fan') {
          if (block.action === 'turn_on_light') sentences.push(`Acenda a luz do ventilador ${art}${roomName}.`);
          else if (block.action === 'turn_off_light') sentences.push(`Apague a luz do ventilador ${art}${roomName}.`);
          else if (block.action === 'power_off') sentences.push(`Desligue apenas o ventilador ${art}${roomName}.`);
          else if (block.action === 'turn_off_all') sentences.push(`Desligue tudo (luz e ventilador) ${art}${roomName}.`);
          else if (block.action?.startsWith('set_speed_')) sentences.push(`Ligue o ventilador ${art}${roomName} na velocidade ${block.action.split('_')[2]}.`);
          else if (block.action === 'ventilation') sentences.push(`Ligue o ventilador ${art}${roomName} no modo ventilação.`);
          else if (block.action === 'exhaustion') sentences.push(`Ligue o ventilador ${art}${roomName} no modo exaustão.`);
          else sentences.push(`Ligue o ventilador ${art}${roomName}.`);
        } else if (block.device_type === 'tv') {
          if (block.action === 'power_off') sentences.push(`Desligue a TV ${art}${roomName}.`);
          else if (block.action === 'open_app') sentences.push(`Abra o aplicativo ${block.app_name || 'Netflix'} na TV ${art}${roomName}.`);
          else sentences.push(`Ligue a TV ${art}${roomName}.`);
        }
      } else if (block.category === 'climate') {
        sentences.push(block.weather_type === 'current' ? 'Me dê a previsão do tempo atual.' : 'Me dê a previsão do tempo para o dia todo.');
      } else if (block.category === 'news') {
        sentences.push('Me dê um resumo das principais notícias de hoje.');
      } else if (block.category === 'calendar') {
        sentences.push('Faça um resumo dos meus eventos e compromissos do calendário para hoje.');
      } else if (block.category === 'music') {
        sentences.push(`Toque ${block.music_query || 'alguma música boa'} no Spotify.`);
      } else if (block.category === 'web_search') {
        if (block.search_query?.trim()) sentences.push(`Pesquise na internet sobre: ${block.search_query.trim()} e me resuma os resultados.`);
      } else if (block.category === 'safety') {
        if (block.safety_areas?.trim()) sentences.push(`Verifique alertas de segurança, tiroteios e trânsito nas áreas: ${block.safety_areas.trim()}.`);
        else sentences.push(`Verifique alertas gerais de segurança e trânsito no Rio de Janeiro.`);
      } else if (block.category === 'custom_prompt') {
        if (block.prompt_text?.trim()) sentences.push(block.prompt_text.trim());
      }
    }
    return sentences.join(' ');
  };

  const handleSave = async () => {
    const finalPrompt = generatePromptFromBlocks(formData.actions_list);
    if (!formData.name || !formData.trigger_value || !finalPrompt) return;
    
    try {
      const payload = {
        name: formData.name,
        trigger_type: 'time',
        trigger_value: formData.trigger_value,
        room_id: formData.room_id,
        action_type: 'simulate_command', // Back to LLM natural language!
        action_value: finalPrompt,
        days_of_week: formData.days_of_week.join(','),
      };
      const newRoutine = await api.createRoutine(payload);
      setRoutines([newRoutine, ...routines]);
      setFormData({ ...formData, name: '', trigger_value: '', actions_list: [], days_of_week: [0, 1, 2, 3, 4, 5, 6] });
    } catch (e) {
      console.error(e);
    }
  };

  const addAction = (isSmartHome: boolean = true) => {
    const newAction: ActionBlock = {
      id: Math.random().toString(36).substring(2, 9),
      category: isSmartHome ? 'smart_home' : 'climate',
      device_type: isSmartHome ? 'light' : undefined,
      location: formData.room_id,
    };
    setFormData({ ...formData, actions_list: [...formData.actions_list, newAction] });
  };

  const updateAction = (id: string, updates: Partial<ActionBlock>) => {
    setFormData({
      ...formData,
      actions_list: formData.actions_list.map(a => {
        if (a.id === id) {
           const merged = { ...a, ...updates };
           if (updates.device_type) {
              const dt = updates.device_type as keyof typeof HOUSE_DEVICES;
              if (HOUSE_DEVICES[dt] && !HOUSE_DEVICES[dt].includes(merged.location as any)) {
                 merged.location = HOUSE_DEVICES[dt][0];
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

  return (
    <div className="relative flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <Modal open={showHelp} onClose={() => setShowHelp(false)} title="Como montar rotinas inteligentes?" maxWidth="max-w-md">
        <ul className="space-y-3 text-sm text-[color:var(--text-secondary)]">
          <li><strong className="text-[color:var(--text-primary)]">Super Prompt:</strong> O Alfredo junta todos os blocos que você adicionar e converte em um único super-comando para a Inteligência Artificial executar na sequência.</li>
          <li><strong className="text-[color:var(--text-primary)]">Todos os Sistemas:</strong> Você pode mesclar Casa Inteligente, Notícias, Spotify, Clima, etc. Tudo em uma rotina só!</li>
        </ul>
      </Modal>

      <SectionHeading
        eyebrow="Automação"
        title="Construtor Universal de Rotinas"
        subtitle="Monte sua rotina encadeando blocos visuais. O Alfredo irá compor o prompt perfeito e executar todas as habilidades em sequência!"
        action={<StatusPulse label="Agendamento ativo" tone="success" />}
      />

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Minhas rotinas"
            title="Rotinas Ativas"
            subtitle="Aqui estão os super-comandos que o Alfredo vai executar."
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

                      <p className="mt-4 rounded-2xl border border-white/5 bg-black/20 px-4 py-3 text-[13px] italic leading-relaxed text-brass-200/70 truncate">
                        "{rt.action_value}"
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-col gap-2">
                      <button onClick={() => handleToggle(rt.id)} className="w-full">
                        <StatusPulse label={rt.is_active ? 'Ativa' : 'Pausada'} tone={rt.is_active ? 'success' : 'warning'} />
                      </button>
                      <button onClick={() => handleTest(rt.id)} className="alfredo-pill justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
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
                <div className="alfredo-section-label">NOVA ROTINA</div>
                <h2 className="mt-2 text-[18px] font-semibold text-[color:var(--text-primary)]">Montador de Prompt</h2>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-4">
              <div>
                <label className="alfredo-section-label">NOME DA ROTINA</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} type="text" placeholder="Ex: Bom dia Alfredo" className="alfredo-input mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="alfredo-section-label">HORÁRIO</label>
                  <input value={formData.trigger_value} onChange={(e) => setFormData({ ...formData, trigger_value: e.target.value })} type="time" className="alfredo-input mt-1" />
                </div>
                <div>
                  <label className="alfredo-section-label">SATÉLITE QUE VAI FALAR</label>
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
                <label className="alfredo-section-label mb-3 block">BLOCOS / SKILLS ({formData.actions_list.length})</label>
                <div className="space-y-3">
                  {formData.actions_list.map((action, idx) => (
                    <div key={action.id} className="alfredo-card p-4 relative flex flex-col gap-3 border border-white/10 bg-white/[0.02]">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-brass-400">Ação {idx + 1}</span>
                        <button onClick={() => removeAction(action.id)} className="text-rose-400/70 hover:text-rose-400 transition-colors">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      
                      {action.category !== 'smart_home' && (
                        <select value={action.category} onChange={(e) => updateAction(action.id, { category: e.target.value as any })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer border-brass-500/20 text-brass-100">
                          <option value="climate">Clima & Previsão</option>
                          <option value="news">Notícias do Dia</option>
                          <option value="calendar">Calendário & Eventos</option>
                          <option value="music">Tocar Música (Spotify)</option>
                          <option value="web_search">Pesquisa na Internet</option>
                          <option value="safety">Segurança e Rotas (Rio)</option>
                          <option value="custom_prompt">Comando Livre (Qualquer Skill)</option>
                        </select>
                      )}

                      {action.category === 'smart_home' && (
                        <div className="flex flex-col space-y-2">
                          <select value={action.location || formData.room_id} onChange={(e) => updateAction(action.id, { location: e.target.value, device_type: undefined, action: undefined })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            <option value={ROOM_IDS.LIVING}>{ROOM_LABELS[ROOM_IDS.LIVING]}</option>
                            <option value={ROOM_IDS.BEDROOM}>{ROOM_LABELS[ROOM_IDS.BEDROOM]}</option>
                            <option value={ROOM_IDS.LAURA}>{ROOM_LABELS[ROOM_IDS.LAURA]}</option>
                            <option value={ROOM_IDS.OFFICE}>{ROOM_LABELS[ROOM_IDS.OFFICE]}</option>
                          </select>

                          <select value={action.device_type || ''} onChange={(e) => updateAction(action.id, { device_type: e.target.value as any, action: undefined })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                            <option value="" disabled>Selecione um dispositivo...</option>
                            {HOUSE_DEVICES.light.includes(action.location as string || formData.room_id) && <option value="light">Luz Inteligente</option>}
                            {HOUSE_DEVICES.fan.includes(action.location as string || formData.room_id) && <option value="fan">Ventilador de Teto (c/ Luz)</option>}
                            {HOUSE_DEVICES.tv.includes(action.location as string || formData.room_id) && <option value="tv">Televisão</option>}
                          </select>

                          {action.device_type === 'light' && (
                            <div className="grid grid-cols-1 gap-2">
                              <select value={action.action || 'power_on'} onChange={(e) => updateAction(action.id, { action: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                                <option value="power_on">Ligar Luz</option>
                                <option value="power_off">Desligar Luz</option>
                                <option value="change_color">Mudar Cor (Cores e Tons)</option>
                              </select>
                              {action.action === 'change_color' && (
                                <input value={action.color_name || ''} onChange={(e) => updateAction(action.id, { color_name: e.target.value })} type="text" placeholder="Ex: azul, verde, branco quente..." className="alfredo-input py-2 text-sm w-full" />
                              )}
                            </div>
                          )}

                          {action.device_type === 'fan' && (
                            <select value={action.action || 'power_on'} onChange={(e) => updateAction(action.id, { action: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                              <option value="power_on">Ligar (Ventilador)</option>
                              <option value="power_off">Desligar (Apenas Ventilador)</option>
                              <option value="turn_on_light">Ligar (Apenas Luz do Ventilador)</option>
                              <option value="turn_off_light">Desligar (Apenas Luz do Ventilador)</option>
                              <option value="turn_off_all">Desligar Tudo (Luz e Ventilador)</option>
                              <option value="set_speed_1">Velocidade 1 (Mínima)</option>
                              <option value="set_speed_2">Velocidade 2</option>
                              <option value="set_speed_3">Velocidade 3</option>
                              <option value="set_speed_4">Velocidade 4</option>
                              <option value="set_speed_5">Velocidade 5</option>
                              <option value="set_speed_6">Velocidade 6 (Máxima)</option>
                              <option value="ventilation">Modo Ventilação</option>
                              <option value="exhaustion">Modo Exaustão</option>
                            </select>
                          )}

                          {action.device_type === 'tv' && (
                            <div className="grid grid-cols-1 gap-2">
                              <select value={action.action || 'power_on'} onChange={(e) => updateAction(action.id, { action: e.target.value })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                                <option value="power_on">Ligar TV</option>
                                <option value="power_off">Desligar TV</option>
                                <option value="open_app">Abrir App Específico</option>
                              </select>
                              {action.action === 'open_app' && (
                                <input value={action.app_name || ''} onChange={(e) => updateAction(action.id, { app_name: e.target.value })} type="text" placeholder="Ex: Netflix, Youtube, Disney" className="alfredo-input py-2 text-sm w-full" />
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {action.category === 'climate' && (
                        <select value={action.weather_type || 'current'} onChange={(e) => updateAction(action.id, { weather_type: e.target.value as any })} className="alfredo-input py-2 text-sm appearance-none cursor-pointer">
                          <option value="current">Tempo Atual (Agora)</option>
                          <option value="forecast">Previsão (Restante do Dia)</option>
                        </select>
                      )}

                      {action.category === 'music' && (
                         <input value={action.music_query || ''} onChange={(e) => updateAction(action.id, { music_query: e.target.value })} type="text" placeholder="Ex: playlist jazz, The Beatles..." className="alfredo-input py-2 text-sm" />
                      )}

                      {action.category === 'web_search' && (
                         <input value={action.search_query || ''} onChange={(e) => updateAction(action.id, { search_query: e.target.value })} type="text" placeholder="Ex: Cotação do Dólar hoje, Jogo do Brasil..." className="alfredo-input py-2 text-sm" />
                      )}

                      {action.category === 'safety' && (
                         <input value={action.safety_areas || ''} onChange={(e) => updateAction(action.id, { safety_areas: e.target.value })} type="text" placeholder="Locais (Ex: Avenida Brasil, Tijuca, Linha Amarela...)" className="alfredo-input py-2 text-sm" />
                      )}

                      {action.category === 'custom_prompt' && (
                        <textarea 
                           value={action.prompt_text || ''} 
                           onChange={(e) => updateAction(action.id, { prompt_text: e.target.value })} 
                           placeholder="Digite qualquer comando como se falasse com o Alfredo. Ex: Crie uma rotina de treino pra mim hoje." 
                           className="alfredo-input py-2 text-sm resize-none h-20" 
                        />
                      )}
                    </div>
                  ))}
                  
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <button onClick={() => addAction(true)} className="alfredo-pill w-full justify-center border-dashed border-white/20 text-[color:var(--text-secondary)] hover:bg-white/[0.05] transition-colors">
                      <PlusCircle className="h-4 w-4" />
                      Adicionar Ação de Casa
                    </button>
                    <button onClick={() => addAction(false)} className="alfredo-pill w-full justify-center border-dashed border-white/20 text-[color:var(--text-secondary)] hover:bg-white/[0.05] transition-colors">
                      <Sparkles className="h-4 w-4" />
                      Adicionar Skill / Lógica
                    </button>
                  </div>
                </div>
              </div>

              {formData.actions_list.length > 0 && (
                <div className="mt-2 bg-black/40 rounded-xl p-4 border border-white/5">
                   <div className="flex items-center gap-2 mb-2">
                     <MessageSquare className="h-4 w-4 text-brass-400" />
                     <span className="text-xs font-bold text-brass-400">PROMPT GERADO</span>
                   </div>
                   <p className="text-sm text-brass-100/80 leading-relaxed italic">
                     "{generatePromptFromBlocks(formData.actions_list)}"
                   </p>
                </div>
              )}

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
