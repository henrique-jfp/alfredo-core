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
  CloudSun,
  BookOpen
} from 'lucide-react';
import { cn } from '../lib/utils';
import { StatusPulse } from './ui/DashboardPrimitives';
import { AlfredoOrb } from './AlfredoOrb';
import { useAlfredoState } from '../hooks/useAlfredoState';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';

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
  | 'clima'
  | 'biblioteca';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const { state: alfredoState } = useAlfredoState();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
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
        { id: 'dispositivos', label: 'Ambientes', icon: SlidersHorizontal },
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
        { id: 'biblioteca', label: 'Biblioteca', icon: BookOpen },
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

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex h-20 items-center justify-between px-4 pb-4 pt-2 border-t border-white/5 bg-[rgba(11,12,14,0.95)] backdrop-blur-2xl">
        <button
          onClick={() => { onTabChange('visao-geral'); setMobileMenuOpen(false); }}
          className={cn("flex flex-col items-center justify-center gap-1.5 w-[20%]", activeTab === 'visao-geral' ? "text-brass-300" : "text-zinc-500 hover:text-zinc-300")}
        >
          <LayoutGrid className={cn("h-[22px] w-[22px] transition-transform", activeTab === 'visao-geral' && "scale-110")} />
          <span className="text-[10px] font-medium tracking-wide">Casa</span>
        </button>

        <button
          onClick={() => { onTabChange('dispositivos'); setMobileMenuOpen(false); }}
          className={cn("flex flex-col items-center justify-center gap-1.5 w-[20%]", activeTab === 'dispositivos' ? "text-brass-300" : "text-zinc-500 hover:text-zinc-300")}
        >
          <SlidersHorizontal className={cn("h-[22px] w-[22px] transition-transform", activeTab === 'dispositivos' && "scale-110")} />
          <span className="text-[10px] font-medium tracking-wide">Ambientes</span>
        </button>

        {/* Empty space for the floating centered WebMic */}
        <div className="w-[20%] flex-shrink-0" />

        <button
          onClick={() => { onTabChange('rotinas'); setMobileMenuOpen(false); }}
          className={cn("flex flex-col items-center justify-center gap-1.5 w-[20%]", activeTab === 'rotinas' ? "text-brass-300" : "text-zinc-500 hover:text-zinc-300")}
        >
          <Clock className={cn("h-[22px] w-[22px] transition-transform", activeTab === 'rotinas' && "scale-110")} />
          <span className="text-[10px] font-medium tracking-wide">Rotinas</span>
        </button>

        <button
          onClick={() => setMobileMenuOpen(true)}
          className={cn("flex flex-col items-center justify-center gap-1.5 w-[20%]", mobileMenuOpen ? "text-brass-300" : "text-zinc-500 hover:text-zinc-300")}
        >
          <Menu className={cn("h-[22px] w-[22px] transition-transform", mobileMenuOpen && "scale-110")} />
          <span className="text-[10px] font-medium tracking-wide">Menu</span>
        </button>
      </nav>

      {/* Mobile Menu BottomSheet */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex flex-col justify-end">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-in fade-in"
            onClick={() => setMobileMenuOpen(false)}
          />
          
          {/* BottomSheet */}
          <aside className="relative flex max-h-[85vh] w-full flex-col rounded-t-[2.5rem] border-t border-white/10 bg-[linear-gradient(180deg,rgba(19,20,23,0.98)_0%,rgba(11,12,14,1)_100%)] px-6 py-8 shadow-2xl animate-in slide-in-from-bottom-full duration-300">
            {/* Grab handle */}
            <div className="absolute top-3 left-1/2 h-1.5 w-12 -translate-x-1/2 rounded-full bg-white/10" />

            {/* Logo */}
            <div className="mb-8 flex items-center justify-between">
              <div className="flex items-center gap-4 rounded-2xl">
                <AlfredoOrb state={alfredoState} size="sm" pulse={false} className="shrink-0" />
                <div className="flex flex-col">
                  <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">Alfredo OS</h2>
                  <span className="text-[11px] font-semibold tracking-[0.2em] text-[color:var(--text-tertiary)] uppercase">Menu Completo</span>
                </div>
              </div>
              <button onClick={() => setMobileMenuOpen(false)} className="rounded-full bg-white/5 p-2 text-zinc-400 hover:bg-white/10 active:scale-95">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex min-h-0 flex-grow flex-col gap-6 overflow-y-auto pb-8 scrollbar-hide">
              {navSections.map((section) => {
                const SectionIcon = section.icon;
                return (
                  <div key={section.label} className="flex flex-col gap-3">
                    <div className="flex items-center gap-2 px-2">
                      <SectionIcon className="h-4 w-4 text-brass-400/80" />
                      <span className="alfredo-section-label">{section.label}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {section.items.map((item) => {
                        const isActive = activeTab === item.id;
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.id}
                            onClick={() => {
                              onTabChange(item.id);
                              setMobileMenuOpen(false);
                            }}
                            className={cn(
                              'relative flex flex-col items-center justify-center gap-2 rounded-2xl border border-white/5 px-2 py-4 text-[13px] transition-all active:scale-95',
                              isActive
                                ? 'bg-brass-500/15 text-brass-300 border-brass-500/20'
                                : 'bg-white/[0.02] text-[color:var(--text-secondary)] hover:bg-white/[0.05]'
                            )}
                          >
                            <Icon className={cn('h-6 w-6 shrink-0', isActive ? 'text-brass-300' : 'text-[color:var(--text-tertiary)]')} strokeWidth={isActive ? 2 : 1.5} />
                            <span className="font-medium tracking-wide">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </nav>
          </aside>
        </div>
      )}
    </>
  );
}
