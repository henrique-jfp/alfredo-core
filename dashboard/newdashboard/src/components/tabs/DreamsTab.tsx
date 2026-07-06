import React, { useState, useEffect } from 'react';
import { Cloud, History, Plus, X, Brain, Heart, Zap, Sparkles, Droplets, Ghost, Compass } from 'lucide-react';
import { api } from '../../lib/api';
import { cn } from '../../lib/utils';

interface Dream {
  id: number;
  themes: string[];
  interpretation: string;
  created_at: string;
}

export function DreamsTab() {
  const [dreams, setDreams] = useState<Dream[]>([]);
  const [wordFreq, setWordFreq] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState<string>('Todos');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newDreamText, setNewDreamText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedDreamId, setExpandedDreamId] = useState<number | null>(null);

  useEffect(() => {
    fetchDreams();
  }, []);

  const fetchDreams = () => {
    api.getDreams().then(data => {
      setDreams(data.history || []);
      setWordFreq(data.word_freq || {});
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDreamText.trim()) return;
    setIsSubmitting(true);
    try {
      await api.createDream(newDreamText);
      setNewDreamText('');
      setIsModalOpen(false);
      fetchDreams();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const cloudWords = Object.entries(wordFreq)
    .map(([word, freq]) => ({ word, freq }))
    .sort((a, b) => b.freq - a.freq); // sort by freq desc

  // Get top 4 words for recurrence chart
  const topWords = cloudWords.slice(0, 4);

  // Extract unique themes for filters
  const allThemes = Array.from(new Set(dreams.flatMap(d => d.themes.map(t => t.toLowerCase()))));
  
  const filteredDreams = filter === 'Todos' 
    ? dreams 
    : dreams.filter(d => d.themes.some(t => t.toLowerCase() === filter));

  // Determine badge color and icon based on theme keyword
  const getThemeStyle = (theme: string) => {
    const t = theme.toLowerCase();
    if (['ansiedade', 'medo', 'pesadelo', 'dragão', 'escuridão', 'queda', 'tsunami'].some(k => t.includes(k))) {
      return { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', icon: Ghost };
    }
    if (['superação', 'vitória', 'voar', 'poder', 'força', 'luz'].some(k => t.includes(k))) {
      return { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', icon: Zap };
    }
    if (['introspecção', 'passado', 'infância', 'água', 'casa', 'família'].some(k => t.includes(k))) {
      return { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', icon: Brain };
    }
    if (['amor', 'paixão', 'encontro', 'abraço'].some(k => t.includes(k))) {
      return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20', icon: Heart };
    }
    return { bg: 'bg-brass-500/10', text: 'text-brass-400', border: 'border-brass-500/20', icon: Compass };
  };

  return (
    <div className="flex gap-6 h-full pb-10">
      
      {/* Coluna Esquerda: Nuvem e Recorrência */}
      <div className="w-[45%] flex flex-col gap-6 h-full min-h-0">
        
        <div className="flex justify-between items-center bg-black/20 p-4 rounded-2xl border border-white/5">
           <div>
             <h2 className="text-xl font-bold text-zinc-100">Diário de sonhos</h2>
             <p className="text-xs text-zinc-500">Exploração psicanalítica do seu subconsciente.</p>
           </div>
           <button 
             onClick={() => setIsModalOpen(true)}
             className="bg-brass-500 hover:bg-brass-400 text-obsidian-900 font-bold px-4 py-2 rounded-xl text-sm flex items-center gap-2 transition-transform hover:scale-105 shadow-[0_0_15px_rgba(201,162,75,0.3)]"
           >
             <Plus className="w-4 h-4" /> Novo sonho
           </button>
        </div>

        <div className="glass-panel p-6 flex flex-col min-h-[300px] relative overflow-hidden flex-grow">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-[16px] font-semibold text-zinc-100 flex items-center gap-2">
              <Cloud className="w-5 h-5 text-brass-400" /> Nuvem de Temas
            </h2>
            {cloudWords.length > 0 && <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Toque para filtrar</span>}
          </div>
          
          {cloudWords.length === 0 ? (
            <div className="flex-grow flex flex-col items-center justify-center text-zinc-500 gap-3 opacity-50">
              <Sparkles className="w-10 h-10 mb-2" />
              <p className="text-sm text-center max-w-[200px]">Nenhum sonho registrado ainda. Os padrões surgirão aqui.</p>
            </div>
          ) : (
            <>
              {/* Organic Word Cloud Layout */}
              <div className="flex-grow flex flex-wrap content-center justify-center gap-x-6 gap-y-4 p-4">
                 {cloudWords.map((w, i) => {
                   const size = Math.min(2.5, 0.9 + (w.freq * 0.2));
                   const opacity = Math.min(1, 0.4 + (w.freq * 0.15));
                   const isSelected = filter === w.word;
                   return (
                     <span 
                       key={w.word}
                       onClick={() => setFilter(isSelected ? 'Todos' : w.word)}
                       className={cn(
                         "font-bold transition-all cursor-pointer hover:scale-110",
                         isSelected ? "text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)] scale-110" : "text-brass-300 hover:text-brass-100 drop-shadow-[0_2px_10px_rgba(201,162,75,0.2)]"
                       )}
                       style={{ 
                         fontSize: `${size}rem`,
                         opacity: isSelected ? 1 : opacity,
                         transform: `rotate(${i % 2 === 0 ? (i%3)*-2 : (i%4)*2}deg) translateY(${i%3===0?-5:5}px)` // Organic scatter
                       }}
                     >
                       {w.word}
                     </span>
                   )
                 })}
              </div>

              {/* Recurrence Chart */}
              <div className="mt-6 border-t border-white/5 pt-5">
                <h3 className="text-[11px] text-zinc-500 uppercase tracking-widest font-bold mb-4">Recorrência este mês</h3>
                <div className="flex flex-col gap-3">
                  {topWords.map((w, i) => (
                    <div key={w.word} className="flex items-center gap-3 text-xs">
                      <span className="w-20 text-zinc-400 truncate">{w.word}</span>
                      <div className="flex-grow h-1.5 bg-black/40 rounded-full overflow-hidden">
                        <div 
                          className={cn("h-full rounded-full transition-all duration-1000", 
                            i === 0 ? "bg-brass-400" : i === 1 ? "bg-emerald-400" : i === 2 ? "bg-rose-400" : "bg-indigo-400"
                          )} 
                          style={{ width: `${(w.freq / topWords[0].freq) * 100}%` }}
                        />
                      </div>
                      <span className="w-4 text-right text-zinc-500 font-mono">{w.freq}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Coluna Direita: Timeline */}
      <div className="w-[55%] glass-panel p-6 flex flex-col h-full min-h-0 relative">
        <h2 className="text-[16px] font-semibold text-zinc-100 mb-6 flex items-center gap-2">
          <History className="w-5 h-5 text-brass-400" /> Timeline de Interpretações
        </h2>
        
        {/* Filtros */}
        {allThemes.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            <button 
              onClick={() => setFilter('Todos')}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors", filter === 'Todos' ? "bg-brass-500/20 border-brass-500/40 text-brass-400" : "bg-white/5 border-white/10 text-zinc-400 hover:bg-white/10")}
            >
              Todos
            </button>
            {allThemes.map(t => (
              <button 
                key={t}
                onClick={() => setFilter(t)}
                className={cn("px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors capitalize", filter === t ? "bg-brass-500/20 border-brass-500/40 text-brass-400" : "bg-white/5 border-white/10 text-zinc-400 hover:bg-white/10")}
              >
                {t}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-2 flex-grow">
           {filteredDreams.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-zinc-500 opacity-60">
                <Brain className="w-12 h-12 mb-3" />
                <p>Nenhum sonho encontrado para o filtro "{filter}".</p>
              </div>
           ) : (
             filteredDreams.map(dream => {
               // Use the first theme for the main badge styling
               const mainTheme = dream.themes[0] || 'geral';
               const style = getThemeStyle(mainTheme);
               const Icon = style.icon;

               return (
                 <div key={dream.id} className="bg-white/[0.02] border border-white/5 rounded-xl p-5 relative overflow-hidden group hover:border-brass-500/20 hover:bg-white/[0.04] transition-all">
                   
                   {/* Badge Categoria Emocional */}
                   <div className={cn("absolute top-0 right-0 px-3 py-1 text-[10px] font-bold tracking-wider rounded-bl-xl border-b border-l uppercase flex items-center gap-1.5", style.bg, style.text, style.border)}>
                     <Icon className="w-3 h-3" />
                     {mainTheme}
                   </div>
                   
                   <div className="text-[11px] text-zinc-500 mb-4 font-mono">
                     {new Date(dream.created_at).toLocaleString('pt-BR')}
                   </div>
                   
                   <p className="text-[14px] text-zinc-200 leading-relaxed">
                     {dream.interpretation}
                   </p>

                   {/* Outras Tags */}
                   {dream.themes.length > 1 && (
                     <div className="mt-4 flex flex-wrap gap-1.5">
                       {dream.themes.slice(1).map((t: string) => (
                         <span key={t} className="text-[9px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-md bg-white/5 text-zinc-400 border border-white/5">
                           {t}
                         </span>
                       ))}
                     </div>
                   )}

                   {/* Accordion para Raw Text */}
                   {dream.raw_text && (
                     <div className="mt-4 border-t border-white/5 pt-3">
                       <button 
                         onClick={() => setExpandedDreamId(expandedDreamId === dream.id ? null : dream.id)}
                         className="text-[11px] text-brass-400/70 hover:text-brass-400 font-bold uppercase tracking-wider flex items-center gap-2 transition-colors"
                       >
                         {expandedDreamId === dream.id ? 'Ocultar Relato Original ▲' : 'Ver Relato Original ▼'}
                       </button>
                       {expandedDreamId === dream.id && (
                         <div className="mt-3 bg-black/40 p-3 rounded-lg border border-white/5 text-[12.5px] text-zinc-400 leading-relaxed italic">
                           "{dream.raw_text}"
                         </div>
                       )}
                     </div>
                   )}
                 </div>
               );
             })
           )}
        </div>
      </div>

      {/* Modal Novo Sonho */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-obsidian-900 border border-white/10 w-full max-w-lg rounded-2xl p-6 shadow-2xl scale-in-center">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-brass-400 flex items-center gap-2">
                <Cloud className="w-5 h-5" /> Relatar Sonho
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-zinc-500 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-sm text-zinc-400 mb-4">
              Descreva o seu sonho com o máximo de detalhes que conseguir se lembrar. A IA irá analisá-lo e extrair significados psicanalíticos.
            </p>
            
            <form onSubmit={handleSubmit}>
              <textarea 
                value={newDreamText}
                onChange={e => setNewDreamText(e.target.value)}
                placeholder="Eu sonhei que estava voando sobre uma montanha escura..."
                className="w-full bg-black/40 border border-white/10 rounded-xl p-4 text-zinc-200 text-sm h-32 resize-none focus:outline-none focus:border-brass-500/50 transition-colors custom-scrollbar mb-6"
                autoFocus
              />
              <div className="flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-zinc-400 hover:bg-white/5 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={isSubmitting || !newDreamText.trim()}
                  className="px-6 py-2 rounded-xl text-sm font-bold bg-brass-500 text-obsidian-900 hover:bg-brass-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmitting ? <span className="animate-pulse">Analisando...</span> : 'Analisar e Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
