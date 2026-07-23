import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../../lib/api';
import { Activity, Brain, Server, ShieldAlert, Zap, Clock, DollarSign, Cpu, Trash2, Edit3, Save, X, Sparkles } from 'lucide-react';
import { Memory, AIMetrics } from '../../types';
import { EmptyState, MetricCard, SectionHeading, StatusPulse, SkeletonBlock, SkeletonKpiGrid } from '../ui/DashboardPrimitives';
import { cn } from '../../lib/utils';

export function IntelligenceTab() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [metrics, setMetrics] = useState<AIMetrics | null>(null);
  const [newFact, setNewFact] = useState('');
  const [editingMemoryId, setEditingMemoryId] = useState<number | null>(null);
  const [editingFactText, setEditingFactText] = useState('');
  const [loadingMemories, setLoadingMemories] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  const fetchAll = async () => {
    // Parallelize both fetches instead of sequential
    setLoadingMemories(true);
    setLoadingMetrics(true);
    await Promise.all([
      (async () => {
        try {
          const data = await api.getMemories();
          setMemories(data);
        } catch (e) {
          console.error('Failed to load memories', e);
        } finally {
          setLoadingMemories(false);
        }
      })(),
      (async () => {
        try {
          const data = await api.getAIMetrics();
          setMetrics(data);
        } catch (e) {
          console.error('Failed to load AI metrics', e);
        } finally {
          setLoadingMetrics(false);
        }
      })(),
    ]);
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => api.getAIMetrics().then(setMetrics).catch(console.error), 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: number) => {
    const confirmed = window.confirm('Tem certeza que deseja excluir esta memória?');
    if (!confirmed) return;
    try {
      await api.deleteMemory(id);
      setMemories(memories.filter((m) => m.id !== id));
    } catch (e) {
      console.error('Failed to delete memory', e);
    }
  };

  const handleAddMemory = async () => {
    if (!newFact.trim()) return;
    try {
      await api.createMemory({ fact: newFact });
      fetchAll();
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
      fetchAll();
    } catch (error) {
      console.error(error);
    }
  };

  const sparkline = useMemo(() => {
    const total = metrics?.global_requests || 0;
    const latency = metrics?.avg_latency_ms || 0;
    return [0.3, 0.45, 0.38, total ? 0.55 : 0.25, latency ? 0.7 : 0.28, 0.82];
  }, [metrics?.global_requests, metrics?.avg_latency_ms]);

  const keyUsage = metrics?.keys?.length
    ? [...metrics.keys].sort((a, b) => b.requests - a.requests)
    : [];

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Cérebro"
        title="Inteligência"
        subtitle="A tela virou um showcase técnico com números grandes, leitura rápida e memória editável."
        action={<StatusPulse label="APIs monitoradas" tone="success" />}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Zap} label="Requisições" value={metrics?.global_requests || 0} detail={metrics?.model || 'Global'} tone="brass" sparkline={sparkline} />
        <MetricCard icon={Clock} label="Latência média" value={`${metrics?.avg_latency_ms || 0} ms`} detail="Últimas 24h" tone="info" sparkline={sparkline.map((n) => Math.min(1, n * 0.9 + 0.05))} />
        <MetricCard icon={DollarSign} label="Economia estimada" value={`$${metrics?.estimated_savings_usd?.toFixed(4) || '0.0000'}`} detail="Uso otimizado" tone="success" sparkline={sparkline.map((n) => Math.min(1, n * 0.8 + 0.1))} />
        <MetricCard icon={Cpu} label="RPM / TPM" value={`${metrics?.rpm || 0} / ${metrics?.tpm || 0}`} detail="Limites ativos" tone="warning" sparkline={sparkline.map((n) => Math.min(1, n * 0.7 + 0.15))} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Telemetria"
            title="Modelos e uso por chave"
            subtitle="Barras proporcionais substituem a tabela plana e aceleram a leitura."
          />

          <div className="mt-5 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {!keyUsage.length ? (
              <EmptyState
                icon={Server}
                tone="info"
                title="Nenhuma métrica de chave disponível"
                description="Assim que a telemetria chegar, o painel mostra o peso de cada chave com barras e valores legíveis."
                className="flex-1"
              />
            ) : (
              keyUsage.map((k, idx) => {
                const maxRequests = keyUsage[0]?.requests || 1;
                const width = Math.max(10, (k.requests / maxRequests) * 100);
                return (
                  <div key={idx} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="text-[15px] font-semibold text-[color:var(--text-primary)]">{k.provider}</div>
                        <div className="mt-1 text-[12px] text-[color:var(--text-secondary)]">{k.requests} requisições • {k.tokens} tokens</div>
                      </div>
                      <StatusPulse label={idx === 0 ? 'Mais usada' : 'Ativa'} tone={idx === 0 ? 'brass' : 'success'} />
                    </div>
                    <div className="mt-4 h-2 overflow-hidden rounded-full bg-black/30">
                      <div className="h-full rounded-full bg-gradient-to-r from-brass-400 to-brass-600" style={{ width: `${width}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-5 rounded-2xl border border-white/5 bg-white/[0.02] p-4 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
            <ShieldAlert className="mb-3 h-5 w-5 text-brass-400" />
            O roteamento Round-Robin continua distribuindo carga entre chaves e mantendo o custo sob controle.
          </div>
        </div>

        <div className="alfredo-card flex min-h-0 flex-col p-5 md:p-6">
          <SectionHeading
            eyebrow="Memória"
            title="Longo prazo"
            subtitle="Cada memória agora ocupa o espaço como um card editável e não como uma lista comprimida."
            action={<StatusPulse label={`${memories.length} fatos`} tone="warning" />}
          />

          <div className="mt-5 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
            {memories.length === 0 ? (
              <EmptyState
                icon={Brain}
                tone="brass"
                title="Nenhum fato na memória"
                description="Adicione um dado sobre você para que o Alfredo use esse contexto nas próximas conversas."
                className="flex-1"
              />
            ) : (
              memories.map((mem) => (
                <div key={mem.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brass-500/10 font-mono text-[12px] font-semibold text-brass-300">
                      #{mem.id}
                    </div>
                    <div className="min-w-0 flex-1">
                      {editingMemoryId === mem.id ? (
                        <div className="flex flex-col gap-3">
                          <input
                            type="text"
                            value={editingFactText}
                            onChange={(e) => setEditingFactText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleUpdateMemory(mem.id);
                              if (e.key === 'Escape') setEditingMemoryId(null);
                            }}
                            className="alfredo-input"
                            autoFocus
                          />
                          <div className="flex gap-2">
                            <button onClick={() => handleUpdateMemory(mem.id)} className="alfredo-pill border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)]">
                              <Save className="h-3.5 w-3.5" />
                              Salvar
                            </button>
                            <button onClick={() => setEditingMemoryId(null)} className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]">
                              <X className="h-3.5 w-3.5" />
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setEditingMemoryId(mem.id);
                            setEditingFactText(mem.fact);
                          }}
                          className="w-full text-left"
                        >
                          <div className="text-[14px] leading-relaxed text-[color:var(--text-primary)]">{mem.fact}</div>
                          <div className="mt-2 text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                            {new Date(mem.created_at).toLocaleDateString('pt-BR')}
                          </div>
                        </button>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col gap-2">
                      <button
                        onClick={() => handleDelete(mem.id)}
                        className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400"
                        title="Excluir"
                        aria-label={`Excluir memória #${mem.id}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => {
                          setEditingMemoryId(mem.id);
                          setEditingFactText(mem.fact);
                        }}
                        className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)]"
                        title="Editar"
                        aria-label={`Editar memória #${mem.id}`}
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-5 flex gap-3 border-t border-white/5 pt-5">
            <input
              type="text"
              value={newFact}
              onChange={(e) => setNewFact(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddMemory()}
              placeholder="Novo fato, ex: Gosto de rock"
              className="alfredo-input"
            />
            <button onClick={handleAddMemory} className="alfredo-pill border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)]">
              <Sparkles className="h-4 w-4" />
              Adicionar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
