import React from 'react';
import { type LucideIcon, 
  LayoutGrid, 
  Link2, 
  Clock, 
  Cpu, 
  Brain, 
  Cloud, 
  Settings,
  CircleUser,
  SlidersHorizontal,
  House,
  Sparkles,
  Layers3,
  RefreshCw,
  CalendarDays,
  CloudSun
} from 'lucide-react';
import { cn } from '../lib/utils';
import { StatusPulse } from './ui/DashboardPrimitives';
import { AlfredoOrb } from './AlfredoOrb';
import { useAlfredoState } from '../hooks/useAlfredoState';

export type TabId = 
  | 'visao-geral'
  | 'satelites'
  | 'inteligencia'
  | 'rotinas'
  | 'integracoes'
  | 'dispositivos'
  | 'sonhos'
  | 'configuracoes'
  | 'calendario'
  | 'clima';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const { state: alfredoState } = useAlfredoState();
  const navSections: {
    label: string;
    icon: LucideIcon;
    items: { id: TabId; label: string; icon: LucideIcon }[];
  }[] = [
    {
      label: 'Casa',
      icon: House,
      items: [
        { id: 'visao-geral', label: 'Visão Geral', icon: LayoutGrid },
        { id: 'calendario', label: 'Calendário', icon: CalendarDays },
        { id: 'clima', label: 'Clima', icon: CloudSun },
        { id: 'integracoes', label: 'Integrações', icon: Link2 },
        { id: 'dispositivos', label: 'Dispositivos', icon: SlidersHorizontal },
        { id: 'rotinas', label: 'Rotinas', icon: Clock },
      ],
    },
    {
      label: 'Alfredo',
      icon: Sparkles,
      items: [
        { id: 'satelites', label: 'Satélites', icon: Cpu },
        { id: 'inteligencia', label: 'Inteligência', icon: Brain },
        { id: 'sonhos', label: 'Sonhos', icon: Cloud },
      ],
    },
    {
      label: 'Sistema',
      icon: Layers3,
      items: [
        { id: 'configuracoes', label: 'Configurações', icon: Settings },
      ],
    },
  ] as const;

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-[288px] flex-shrink-0 flex-col border-r border-white/5 bg-[linear-gradient(180deg,rgba(19,20,23,0.95)_0%,rgba(11,12,14,0.98)_100%)] px-5 py-5 backdrop-blur-3xl z-40">
        {/* Logo */}
        <div className="mb-8 flex items-center gap-4 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-4 shadow-[0_8px_24px_rgba(0,0,0,0.28)]">
          <AlfredoOrb state={alfredoState} size="md" pulse={false} className="shrink-0" />
          <div className="flex flex-col">
            <h2 className="text-[18px] font-semibold tracking-tight text-[color:var(--text-primary)]">Alfredo OS</h2>
            <span className="mt-0.5 text-[10px] font-semibold tracking-[0.2em] text-[color:var(--text-tertiary)]">OBSIDIAN &amp; BRASS</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex min-h-0 flex-grow flex-col gap-6 overflow-y-auto pr-1">
          {navSections.map((section) => {
            const SectionIcon = section.icon;
            return (
              <div key={section.label} className="flex flex-col gap-3">
                <div className="flex items-center gap-2 px-2">
                  <SectionIcon className="h-4 w-4 text-brass-400/80" />
                  <span className="alfredo-section-label">{section.label}</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {section.items.map((item) => {
                    const isActive = activeTab === item.id;
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => onTabChange(item.id)}
                        className={cn(
                          'relative flex items-center gap-3 overflow-hidden rounded-2xl px-4 py-3 text-left text-[14px] transition-all duration-200',
                          isActive
                            ? 'border border-brass-500/25 bg-brass-500/10 text-[color:var(--text-primary)] shadow-[0_0_24px_rgba(212,162,78,0.12)]'
                            : 'border border-transparent text-[color:var(--text-secondary)] hover:border-white/5 hover:bg-white/[0.03] hover:text-[color:var(--text-primary)]'
                        )}
                      >
                        {isActive && <div className="absolute left-0 top-3 bottom-3 w-[3px] rounded-r-full bg-gradient-to-b from-brass-300 to-brass-600" />}
                        <Icon className={cn('h-5 w-5 shrink-0 transition-colors', isActive ? 'text-brass-300' : 'text-[color:var(--text-tertiary)]')} strokeWidth={isActive ? 2.4 : 2} />
                        <span className="font-medium">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="mt-6 flex items-center gap-2">
          <StatusPulse label="Sistema online" tone="success" className="flex-1 justify-center" />
          <button
            onClick={() => window.location.reload()}
            className="alfredo-pill border-brass-500/25 bg-brass-500/10 text-brass-300 hover:bg-brass-500/15"
            title="Recarregar Dashboard"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Recarregar
          </button>
        </div>

        {/* Footer */}
        <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-3 py-3 text-[color:var(--text-tertiary)]">
          <CircleUser className="h-8 w-8 opacity-60" />
          <div className="flex flex-col">
            <span className="text-[11px] font-medium text-[color:var(--text-secondary)]">Admin</span>
            <span className="text-[10px] tracking-[0.16em] uppercase">Alfredo OS • v3.0</span>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Navigation */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-white/10 bg-[rgba(11,12,14,0.96)] backdrop-blur-3xl pb-safe">
        <div
          className="flex h-16 items-center gap-1 overflow-x-auto px-2 hide-scrollbar"
          style={{ scrollSnapType: 'x mandatory', WebkitOverflowScrolling: 'touch' }}
        >
          {navSections.map((section, sectionIndex) => (
            <React.Fragment key={section.label}>
              {sectionIndex > 0 && (
                <div className="mx-1 h-6 w-px flex-shrink-0 bg-white/10" aria-hidden="true" />
              )}
              {section.items.map((item) => {
                const isActive = activeTab === item.id;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    style={{ scrollSnapAlign: 'start' }}
                    className={cn(
                      "flex flex-shrink-0 flex-col items-center justify-center gap-0.5 rounded-xl px-2.5 py-1.5 transition-all min-w-[52px]",
                      isActive ? "bg-brass-500/15 text-brass-400" : "text-zinc-500 hover:text-zinc-300"
                    )}
                    aria-pressed={isActive}
                    aria-label={item.label}
                  >
                    <Icon className={cn("w-5 h-5 transition-transform", isActive && "scale-110")} strokeWidth={isActive ? 2.5 : 2} />
                    <span className="text-[9px] font-medium tracking-tight truncate max-w-[52px] leading-tight">{item.label}</span>
                  </button>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </>
  );
}
