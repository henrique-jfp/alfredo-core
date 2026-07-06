import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Clock, PlusCircle, HelpCircle, X } from 'lucide-react';
import { Routine } from '../../types';

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
    days_of_week: [0, 1, 2, 3, 4, 5, 6] // 0=Sun, 6=Sat
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
      setRoutines(routines.filter(r => r.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.trigger_value || !formData.action_value) return;
    try {
      const payload = {
        ...formData,
        days_of_week: formData.days_of_week.join(',')
      };
      const newRoutine = await api.createRoutine(payload);
      setRoutines([newRoutine, ...routines]);
      setFormData({ ...formData, name: '', trigger_value: '', action_value: '', days_of_week: [0, 1, 2, 3, 4, 5, 6] });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex gap-6 h-full pb-10 relative">
      
      {/* Help Modal */}
      {showHelp && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm rounded-xl">
          <div className="bg-obsidian-800 border border-white/10 p-6 rounded-2xl max-w-md w-full shadow-2xl relative">
            <button onClick={() => setShowHelp(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-xl font-bold text-brass-400 mb-4 flex items-center gap-2"><HelpCircle className="w-5 h-5"/> Como criar rotinas?</h3>
            <p className="text-sm text-zinc-300 mb-4 leading-relaxed">
              As rotinas permitem que o Alfredo execute tarefas automaticamente baseadas no horário.
            </p>
            <ul className="text-sm text-zinc-400 space-y-3">
              <li><strong className="text-white">Nome:</strong> Apenas para você identificar (ex: "Bom dia").</li>
              <li><strong className="text-white">Horário:</strong> A hora exata que vai disparar (ex: "07:00").</li>
              <li><strong className="text-white">Sala:</strong> O cômodo onde o comando será executado (ex: "Sala de Estar").</li>
              <li><strong className="text-white">Comando Simulado:</strong> É exatamente o que você falaria pro Alfredo (ex: "Acenda a luz e me dê o clima de hoje").</li>
            </ul>
          </div>
        </div>
      )}

      {/* List */}
      <div className="w-3/5 glass-panel p-6 flex flex-col h-full min-h-0">
        <h2 className="text-[16px] font-semibold text-zinc-100 mb-6 flex items-center gap-2">
          <Clock className="w-5 h-5 text-brass-400" /> Minhas Rotinas
        </h2>
        
        <div className="flex flex-col gap-3 overflow-y-auto custom-scrollbar pr-2">
           {routines.length === 0 ? (
              <div className="text-zinc-500 text-sm italic py-4 text-center">Nenhuma rotina cadastrada.</div>
           ) : routines.map(rt => (
             <div key={rt.id} className={`bg-white/[0.015] border border-white/5 rounded-xl p-5 flex items-center gap-5 transition-all ${!rt.is_active ? 'opacity-50 grayscale' : 'hover:border-brass-500/30 hover:bg-white/[0.03]'}`}>
                <div className="w-12 h-12 rounded-xl bg-brass-500/10 flex items-center justify-center text-xl shrink-0">
                  ⏰
                </div>
                <div className="flex-grow">
                  <h3 className="font-semibold text-zinc-100 text-[15px]">{rt.name}</h3>
                  <div className="flex gap-2 mt-1.5 flex-wrap">
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-brass-500/10 text-brass-400">🕐 {rt.trigger_value}</span>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-brass-500/10 text-brass-400">📍 {rt.room_id}</span>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-white/5 text-zinc-400">
                      {rt.days_of_week ? rt.days_of_week.split(',').length === 7 ? 'Todos os dias' : `${rt.days_of_week.split(',').length} dia(s)` : 'Todos os dias'}
                    </span>
                  </div>
                  <p className="text-[12px] text-zinc-400 mt-2 italic">🗣️ "{rt.action_value}"</p>
                </div>
                
                <div className="flex items-center gap-3 shrink-0">
                   {/* Toggle switch visual mockup */}
                   <div className={`w-11 h-6 rounded-full p-1 transition-colors ${rt.is_active ? 'bg-brass-500' : 'bg-white/10'}`}>
                      <div className={`w-4 h-4 rounded-full bg-obsidian-900 transition-transform ${rt.is_active ? 'translate-x-5' : 'translate-x-0 bg-zinc-400'}`} />
                   </div>
                   <button className="w-9 h-9 flex items-center justify-center bg-white/5 rounded-lg hover:bg-white/10">▶</button>
                   <button onClick={() => handleDelete(rt.id)} className="w-9 h-9 flex items-center justify-center bg-rose-500/10 text-rose-400 rounded-lg hover:bg-rose-500/20">🗑️</button>
                </div>
             </div>
           ))}
        </div>
      </div>

      {/* Form */}
      <div className="w-2/5 glass-panel p-6 flex flex-col h-full min-h-0 relative">
        <h2 className="text-[16px] font-semibold text-zinc-100 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-brass-400" /> Nova Rotina
          </div>
          <button onClick={() => setShowHelp(true)} className="p-1.5 bg-white/5 rounded-lg text-brass-400 hover:bg-white/10 transition-colors" title="Como usar">
            <HelpCircle className="w-5 h-5" />
          </button>
        </h2>
        
        <div className="flex flex-col gap-4">
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Nome da Rotina</label>
              <input value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} type="text" placeholder="Ex: Bom dia" className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" />
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Horário (HH:MM)</label>
              <input value={formData.trigger_value} onChange={e => setFormData({...formData, trigger_value: e.target.value})} type="time" className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" />
            </div>

            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Dias da Semana</label>
              <div className="flex gap-1.5">
                {DAYS.map(day => {
                  const isSelected = formData.days_of_week.includes(day.value);
                  return (
                    <button
                      key={day.value}
                      onClick={() => {
                        const newDays = isSelected 
                          ? formData.days_of_week.filter(d => d !== day.value)
                          : [...formData.days_of_week, day.value].sort();
                        setFormData({...formData, days_of_week: newDays});
                      }}
                      className={`flex-1 h-9 rounded-md text-xs font-bold transition-all ${
                        isSelected 
                          ? 'bg-brass-500/20 text-brass-400 border border-brass-500/50' 
                          : 'bg-white/5 text-zinc-500 border border-transparent hover:bg-white/10'
                      }`}
                    >
                      {day.label}
                    </button>
                  )
                })}
              </div>
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Sala</label>
              <select value={formData.room_id} onChange={e => setFormData({...formData, room_id: e.target.value})} className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none appearance-none cursor-pointer">
                <option value="ROOM_LIVING">Sala de Estar</option>
                <option value="ROOM_BEDROOM">Quarto</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Comando Simulado</label>
              <input value={formData.action_value} onChange={e => setFormData({...formData, action_value: e.target.value})} type="text" placeholder="Ex: como está o clima" className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" />
            </div>
            
            <button onClick={handleSave} className="w-full py-3.5 mt-4 bg-gradient-to-r from-brass-400 to-brass-600 hover:from-brass-300 hover:to-brass-500 text-obsidian-900 font-bold rounded-xl shadow-lg transition-all">
               Salvar Rotina
            </button>
        </div>
      </div>

    </div>
  );
}
