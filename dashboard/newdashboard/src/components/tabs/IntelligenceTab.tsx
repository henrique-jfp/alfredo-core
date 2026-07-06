import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Activity, Brain, Server, ShieldAlert, Zap, Clock, DollarSign, Cpu, Trash2 } from 'lucide-react';
import { Memory, AIMetrics } from '../../types';

export function IntelligenceTab() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [metrics, setMetrics] = useState<AIMetrics | null>(null);
  const [newFact, setNewFact] = useState('');
  const [editingMemoryId, setEditingMemoryId] = useState<number | null>(null);
  const [editingFactText, setEditingFactText] = useState('');

  useEffect(() => {
    fetchMemories();
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchMemories = async () => {
    try {
      const data = await api.getMemories();
      setMemories(data);
    } catch (e) {
      console.error('Failed to load memories', e);
    }
  };
  
  const fetchMetrics = async () => {
    try {
      const data = await api.getAIMetrics();
      setMetrics(data);
    } catch (e) {
      console.error('Failed to load AI metrics', e);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteMemory(id);
      setMemories(memories.filter(m => m.id !== id));
    } catch (e) {
      console.error('Failed to delete memory', e);
    }
  };

  const handleAddMemory = async () => {
    if (!newFact.trim()) return;
    try {
      await api.createMemory({ fact: newFact });
      fetchMemories();
      setNewFact('');
    } catch (e) {
      console.error('Failed to create memory', e);
    }
  };

  const handleUpdateMemory = async (id: number) => {
    if (!editingFactText.trim()) return;
    try {
      await api.updateMemory(id, editingFactText);
      setEditingMemoryId(null);
      setEditingFactText('');
      fetchMemories();
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="flex gap-6 h-full pb-10">
      
      {/* Monitor de Carga */}
      <div className="w-1/2 flex flex-col gap-6">
        <div className="glass-panel p-6 flex flex-col h-full min-h-0">
          <h2 className="text-[16px] font-semibold text-zinc-100 mb-6 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-brass-400" /> Modelos & Telemetria
          </h2>

          <div className="flex gap-2 mb-6">
            <span className="text-xs px-3 py-1 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              ● API Online
            </span>
            {metrics?.keys?.map((k, idx) => (
              <span key={idx} className="text-xs px-3 py-1 rounded-full font-bold bg-white/5 text-zinc-400 border border-white/10 flex gap-2 items-center">
                {k.provider} <span className="w-2 h-2 rounded-full bg-emerald-400" />
              </span>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
             <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex items-center gap-3">
               <div className="w-10 h-10 rounded-lg bg-brass-500/10 flex items-center justify-center shrink-0">
                 <Zap className="w-5 h-5 text-brass-400" />
               </div>
               <div>
                 <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-0.5">Requisições (Global)</span>
                 <span className="text-xl font-bold text-zinc-100">{metrics?.global_requests || 0}</span>
               </div>
             </div>
             
             <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex items-center gap-3">
               <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center shrink-0">
                 <Clock className="w-5 h-5 text-teal-400" />
               </div>
               <div>
                 <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-0.5">Latência Média</span>
                 <span className="text-xl font-bold text-zinc-100">{metrics?.avg_latency_ms || 0} ms</span>
               </div>
             </div>
             
             <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex items-center gap-3">
               <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                 <DollarSign className="w-5 h-5 text-emerald-400" />
               </div>
               <div>
                 <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-0.5">Economia Estimada</span>
                 <span className="text-xl font-bold text-zinc-100">$ {metrics?.estimated_savings_usd?.toFixed(4) || '0.0000'}</span>
               </div>
             </div>
             
             <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex flex-col justify-center">
                 <div className="flex justify-between items-end mb-1">
                   <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">RPM</span>
                   <span className="text-sm font-bold text-brass-400">{metrics?.rpm || 0}</span>
                 </div>
                 <div className="flex justify-between items-end">
                   <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">TPM</span>
                   <span className="text-sm font-bold text-brass-400">{metrics?.tpm || 0}</span>
                 </div>
             </div>
          </div>
          
          <div className="flex-grow flex flex-col bg-black/20 rounded-xl border border-white/5 p-4 mb-4 overflow-hidden">
             <span className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest block mb-3">Uso por Chave de API</span>
             <div className="flex flex-col gap-2 overflow-y-auto custom-scrollbar">
                {!metrics?.keys?.length ? (
                  <span className="text-sm text-zinc-600 italic">Nenhum dado de chave registrado...</span>
                ) : (
                  metrics.keys.map((k, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white/[0.02] p-2.5 rounded-lg">
                      <span className="text-sm font-medium text-zinc-300">{k.provider}</span>
                      <div className="flex gap-4 text-xs font-mono">
                         <span className="text-zinc-400"><strong className="text-zinc-200">{k.requests}</strong> reqs</span>
                         <span className="text-brass-400/80"><strong className="text-brass-400">{k.tokens}</strong> tkns</span>
                      </div>
                    </div>
                  ))
                )}
             </div>
          </div>
          
          <div className="mt-auto bg-white/5 p-4 rounded-lg flex gap-3 text-sm text-zinc-400 border border-white/5">
            <ShieldAlert className="w-5 h-5 text-brass-500 shrink-0" />
            <p>O roteamento Round-Robin nativo do Alfredo está gerenciando a limitação de RPM (Requests Per Minute) das chaves gratuitas perfeitamente.</p>
          </div>
        </div>
      </div>

      {/* Memória de Longo Prazo */}
      <div className="w-1/2 glass-panel p-6 flex flex-col h-full min-h-0">
        <h2 className="text-[16px] font-semibold text-zinc-100 mb-2 flex items-center gap-2">
          <Brain className="w-5 h-5 text-brass-400" /> Memória de Longo Prazo
        </h2>
        <p className="text-zinc-500 text-[13px] mb-6">
          Fatos que o Alfredo aprendeu sobre você e que são injetados em todas as conversas ("Always-On Context").
        </p>
        
        <ul className="flex flex-col gap-2 overflow-y-auto custom-scrollbar flex-grow pr-2 mb-4">
          {memories.length === 0 ? (
            <li className="text-zinc-500 text-sm italic py-4 text-center">Nenhum fato na memória.</li>
          ) : (
            memories.map(mem => (
              <li key={mem.id} className="p-4 bg-white/[0.015] border border-white/5 hover:border-brass-500/30 hover:bg-white/[0.03] transition-all rounded-xl flex items-start gap-4">
                <span className="text-brass-500 font-mono font-bold mt-0.5 shrink-0">#{mem.id}</span>
                {editingMemoryId === mem.id ? (
                  <div className="flex-grow flex gap-2">
                    <input 
                      type="text" 
                      value={editingFactText}
                      onChange={(e) => setEditingFactText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleUpdateMemory(mem.id);
                        if (e.key === 'Escape') setEditingMemoryId(null);
                      }}
                      className="w-full bg-black/40 border border-brass-500/50 rounded-lg px-3 py-1.5 text-[14px] text-zinc-100 focus:outline-none focus:ring-1 focus:ring-brass-500/50"
                      autoFocus
                    />
                    <button onClick={() => handleUpdateMemory(mem.id)} className="text-emerald-400 hover:text-emerald-300 font-bold text-sm bg-emerald-500/10 px-2 rounded">
                      Salvar
                    </button>
                    <button onClick={() => setEditingMemoryId(null)} className="text-zinc-500 hover:text-zinc-300 font-bold text-sm bg-white/5 px-2 rounded">
                      Cancelar
                    </button>
                  </div>
                ) : (
                  <span 
                    className="text-zinc-200 text-[14px] flex-grow leading-relaxed cursor-text hover:bg-white/5 rounded px-1 transition-colors"
                    onClick={() => {
                      setEditingMemoryId(mem.id);
                      setEditingFactText(mem.fact);
                    }}
                    title="Clique para editar"
                  >
                    {mem.fact}
                  </span>
                )}
                <button onClick={() => handleDelete(mem.id)} className="text-zinc-500 hover:text-rose-400 transition-colors p-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))
          )}
        </ul>

        <div className="flex gap-3 pt-4 border-t border-white/5 shrink-0">
           <input 
             type="text" 
             value={newFact}
             onChange={e => setNewFact(e.target.value)}
             onKeyDown={e => e.key === 'Enter' && handleAddMemory()}
             placeholder="Novo fato (ex: Gosto de rock)" 
             className="flex-grow bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-brass-500/50"
           />
           <button onClick={handleAddMemory} className="px-6 py-3 bg-gradient-to-r from-brass-400 to-brass-600 hover:from-brass-300 hover:to-brass-500 text-obsidian-900 font-bold rounded-xl shadow-[0_0_15px_rgba(201,162,75,0.2)] transition-all">
             Adicionar
           </button>
        </div>
      </div>

    </div>
  );
}
