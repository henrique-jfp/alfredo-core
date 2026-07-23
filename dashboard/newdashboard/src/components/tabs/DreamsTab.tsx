import React, { useState, useEffect, useMemo } from 'react';
import { Cloud, History, Plus, X, Brain, Heart, Zap, Sparkles, Ghost, Compass, ArrowRight, Stars } from 'lucide-react';
import { api } from '../../lib/api';
import { cn } from '../../lib/utils';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { Modal } from '../ui/Modal';
import { DREAM_THEME_GROUPS } from '../../types';

interface Dream {
  id: number;
  themes: string[];
  interpretation: string;
  created_at: string;
  raw_text?: string;
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
    api.getDreams().then((data) => {
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

  const cloudWords = useMemo(
    () =>
      Object.entries(wordFreq)
        .map(([word, freq]) => ({ word, freq }))
        .sort((a, b) => b.freq - a.freq),
    [wordFreq],
  );

  const topWords = cloudWords.slice(0, 4);
  const allThemes = Array.from(new Set(dreams.flatMap((d) => d.themes.map((t) => t.toLowerCase()))));
  const filteredDreams =
    filter === 'Todos'
      ? dreams
      : dreams.filter((d) => d.themes.some((t) => t.toLowerCase() === filter));

  const getThemeStyle = (theme: string) => {
    const t = theme.toLowerCase();
    if (DREAM_THEME_GROUPS.anxiety.some((k) => t.includes(k))) {
      return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20', icon: Ghost };
    }
    if (DREAM_THEME_GROUPS.triumph.some((k) => t.includes(k))) {
      return { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', icon: Zap };
    }
    if (DREAM_THEME_GROUPS.introspection.some((k) => t.includes(k))) {
      return { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', icon: Brain };
    }
    if (DREAM_THEME_GROUPS.love.some((k) => t.includes(k))) {
      return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20', icon: Heart };
    }
    return { bg: 'bg-brass-500/10', text: 'text-brass-400', border: 'border-brass-500/20', icon: Compass };
  };

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <div className="alfredo-card relative overflow-hidden p-5 md:p-6">
        <div className="absolute right-0 top-0 h-56 w-56 translate-x-1/3 -translate-y-1/3 rounded-full bg-brass-500/10 blur-[80px]" />
        <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="alfredo-section-label">Diário onírico</div>
            <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-[color:var(--text-primary)] md:text-[32px]">Diário de Sonhos</h1>
            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
              A tela deixa de parecer vazia e passa a se comportar como um lugar de descoberta, mesmo antes dos dados aparecerem.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="alfredo-pill border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] shadow-[0_0_24px_rgba(212,162,78,0.18)]"
          >
            <Plus className="h-4 w-4" />
            Novo sonho
          </button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Nuvem"
            title="Temas recorrentes"
            subtitle="A nuvem recebe personalidade visual com a mesma seriedade que as telas de dados."
            action={<StatusPulse label={`${cloudWords.length} temas`} tone="brass" />}
          />

          <div className="mt-5 min-h-[340px] flex-1 rounded-2xl border border-white/5 bg-[radial-gradient(circle_at_center,rgba(212,162,78,0.08),transparent_55%)] p-5">
            {cloudWords.length === 0 ? (
              <EmptyState
                icon={Stars}
                tone="brass"
                title="Seus sonhos ainda não viraram estrelas nessa nuvem"
                description="Conte um sonho assim que acordar e eu crio a estrutura visual da memória onírica."
                className="h-full"
              />
            ) : (
              <div className="flex h-full flex-wrap content-center justify-center gap-x-5 gap-y-4">
                {cloudWords.map((w, i) => {
                  const size = Math.min(2.5, 0.9 + w.freq * 0.2);
                  const opacity = Math.min(1, 0.4 + w.freq * 0.15);
                  const isSelected = filter === w.word;
                  return (
                    <button
                      key={w.word}
                      onClick={() => setFilter(isSelected ? 'Todos' : w.word)}
                      className={cn(
                        'font-semibold transition-all duration-200 hover:scale-110',
                        isSelected ? 'scale-110 text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)]' : 'text-brass-300 hover:text-brass-100'
                      )}
                      style={{
                        fontSize: `${size}rem`,
                        opacity: isSelected ? 1 : opacity,
                        transform: `rotate(${i % 2 === 0 ? (i % 3) * -2 : (i % 4) * 2}deg) translateY(${i % 3 === 0 ? -5 : 5}px)`,
                      }}
                      aria-label={`Filtrar por "${w.word}"`}
                    >
                      {w.word}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {topWords.length > 0 && (
            <div className="mt-5 rounded-2xl border border-white/5 bg-white/[0.02] p-4">
              <h3 className="alfredo-section-label mb-4">Recorrência este mês</h3>
              <div className="flex flex-col gap-3">
                {topWords.map((w, i) => (
                  <div key={w.word} className="flex items-center gap-3 text-xs">
                    <span className="w-20 truncate text-[color:var(--text-secondary)]">{w.word}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/30">
                      <div
                        className={cn('h-full rounded-full transition-all duration-1000', i === 0 ? 'bg-brass-400' : i === 1 ? 'bg-emerald-400' : i === 2 ? 'bg-rose-400' : 'bg-indigo-400')}
                        style={{ width: `${(w.freq / topWords[0].freq) * 100}%` }}
                      />
                    </div>
                    <span className="w-4 text-right font-mono text-[color:var(--text-tertiary)]">{w.freq}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Linha do tempo"
            title="Interpretações"
            subtitle="Os estados vazios agora falam com a voz do produto."
          />

          {allThemes.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => setFilter('Todos')}
                className={cn('alfredo-pill', filter === 'Todos' ? 'border-brass-500/25 bg-brass-500/15 text-brass-300' : 'border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]')}
              >
                Todos
              </button>
              {allThemes.map((t) => (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={cn('alfredo-pill capitalize', filter === t ? 'border-brass-500/25 bg-brass-500/15 text-brass-300' : 'border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]')}
                  aria-label={`Filtrar por tema "${t}"`}
                >
                  {t}
                </button>
              ))}
            </div>
          )}

          <div className="mt-5 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {filteredDreams.length === 0 ? (
              <EmptyState
                icon={History}
                tone="info"
                title={filter === 'Todos' ? 'Nenhum sonho registrado ainda' : `Nenhum sonho para "${filter}"`}
                description={filter === 'Todos' ? 'Quando você relatar o primeiro sonho, essa timeline ganha densidade e ritmo.' : 'Troque o filtro ou crie um novo relato para alimentar a nuvem.'}
                className="flex-1"
              />
            ) : (
              filteredDreams.map((dream) => {
                const mainTheme = dream.themes[0] || 'geral';
                const style = getThemeStyle(mainTheme);
                const Icon = style.icon;

                return (
                  <div key={dream.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 transition-colors hover:bg-white/[0.04]">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="text-[11px] font-mono text-[color:var(--text-tertiary)]">
                          {new Date(dream.created_at).toLocaleString('pt-BR')}
                        </div>
                        <p className="mt-3 text-[14px] leading-relaxed text-[color:var(--text-primary)]">
                          {dream.interpretation}
                        </p>
                      </div>
                      <div className={cn('flex shrink-0 items-center gap-1.5 rounded-bl-xl rounded-tr-xl border px-3 py-1 text-[10px] font-bold uppercase tracking-wider', style.bg, style.text, style.border)}>
                        <Icon className="h-3 w-3" />
                        {mainTheme}
                      </div>
                    </div>

                    {dream.themes.length > 1 && (
                      <div className="mt-4 flex flex-wrap gap-1.5">
                        {dream.themes.slice(1).map((t: string) => (
                          <span key={t} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {dream.raw_text && (
                      <div className="mt-4 border-t border-white/5 pt-3">
                        <button
                          onClick={() => setExpandedDreamId(expandedDreamId === dream.id ? null : dream.id)}
                          className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]"
                          aria-label={expandedDreamId === dream.id ? 'Ocultar relato original' : 'Ver relato original'}
                        >
                          {expandedDreamId === dream.id ? 'Ocultar relato original' : 'Ver relato original'}
                          <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                        {expandedDreamId === dream.id && (
                          <div className="mt-3 rounded-2xl border border-white/5 bg-black/20 p-3 text-[12.5px] leading-relaxed italic text-[color:var(--text-secondary)]">
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
      </div>

      <Modal open={isModalOpen} onClose={() => setIsModalOpen(false)} title="Relatar sonho" maxWidth="max-w-lg">
        <p className="mb-4 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
          Descreva o sonho com o máximo de detalhes que você lembrar. O Alfredo interpreta e extrai padrões temáticos.
        </p>
        <form onSubmit={handleSubmit}>
          <textarea
            value={newDreamText}
            onChange={(e) => setNewDreamText(e.target.value)}
            placeholder="Eu sonhei que estava voando sobre uma montanha escura..."
            className="alfredo-input min-h-32 resize-none"
            autoFocus
          />
          <div className="mt-6 flex justify-end gap-3">
            <button type="button" onClick={() => setIsModalOpen(false)} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !newDreamText.trim()}
              className="alfredo-pill border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? 'Analisando...' : 'Analisar e salvar'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
