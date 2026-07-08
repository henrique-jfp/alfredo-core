import React from 'react';
import { cn } from '../lib/utils';
import { 
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
  Layers3
} from 'lucide-react';

export type TabId = 
  | 'visao-geral'
  | 'satelites'
  | 'inteligencia'
  | 'rotinas'
  | 'integracoes'
  | 'dispositivos'
  | 'sonhos'
  | 'configuracoes';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const navSections = [
    {
      label: 'Casa',
      icon: House,
      items: [
        { id: 'visao-geral', label: 'Visão Geral', icon: LayoutGrid },
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
          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl border border-brass-500/30 bg-[radial-gradient(circle_at_30%_30%,rgba(212,162,78,0.25),rgba(19,20,23,1)_70%)] shadow-[0_0_24px_rgba(212,162,78,0.18)]">
            <span className="text-xl font-bold text-brass-300">A</span>
          </div>
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
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex h-16 items-center justify-around border-t border-white/10 bg-[rgba(11,12,14,0.96)] px-2 backdrop-blur-3xl pb-safe">
        {navSections.flatMap((section) => section.items).map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "flex flex-col items-center justify-center w-14 h-14 rounded-xl transition-all",
                isActive ? "text-brass-400" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              <Icon className={cn("w-5 h-5 mb-1 transition-transform", isActive && "scale-110")} strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-[9px] font-medium tracking-wide truncate max-w-full px-1">{item.label}</span>
            </button>
          );
        })}
      </div>
    </>
  );
}
