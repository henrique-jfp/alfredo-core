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
  SlidersHorizontal
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
  const navItems = [
    { id: 'visao-geral', label: 'Visão Geral', icon: LayoutGrid },
    { id: 'integracoes', label: 'Integrações', icon: Link2 },
    { id: 'dispositivos', label: 'Dispositivos', icon: SlidersHorizontal },
    { id: 'rotinas', label: 'Rotinas', icon: Clock },
    { id: 'satelites', label: 'Satélites', icon: Cpu },
    { id: 'inteligencia', label: 'Inteligência', icon: Brain },
    { id: 'sonhos', label: 'Sonhos', icon: Cloud },
    { id: 'configuracoes', label: 'Configurações', icon: Settings },
  ] as const;

  return (
    <aside className="w-[260px] flex-shrink-0 flex flex-col p-5 bg-obsidian-800/80 backdrop-blur-3xl border-r border-white/5">
      
      {/* Logo */}
      <div className="flex items-center gap-4 mb-10 px-2">
        <div className="w-12 h-12 rounded-xl bg-obsidian-700 border border-brass-500/30 flex items-center justify-center shadow-[inset_0_0_0_1px_rgba(255,255,255,0.02),0_0_24px_rgba(201,162,75,0.15)] flex-shrink-0">
          <span className="font-bold text-xl text-brass-300">A</span>
        </div>
        <div className="flex flex-col">
          <h2 className="text-[17px] font-bold text-zinc-100 tracking-tight leading-tight">Alfredo OS</h2>
          <span className="text-[9px] font-bold tracking-[0.15em] text-zinc-500 mt-0.5">SISTEMA RESIDENCIAL</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1.5 flex-grow">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "relative flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-300 text-[14px] overflow-hidden text-left",
                isActive 
                  ? "bg-brass-500/10 text-zinc-100 font-semibold" 
                  : "text-zinc-400 font-medium hover:bg-white/5 hover:text-zinc-200"
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-2 bottom-2 w-[3px] bg-gradient-to-b from-brass-300 to-brass-500 rounded-r-full" />
              )}
              <Icon className={cn("w-5 h-5 transition-colors duration-300", isActive ? "text-brass-300" : "text-zinc-500")} strokeWidth={isActive ? 2.5 : 2} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="pt-6 border-t border-white/5 flex items-center gap-3 text-zinc-500 px-2 mt-auto">
        <CircleUser className="w-8 h-8 opacity-50" />
        <div className="flex flex-col">
          <span className="text-[11px] font-medium text-zinc-400">Admin</span>
          <span className="text-[10px] tracking-wide">Alfredo OS • v3.0</span>
        </div>
      </div>
    </aside>
  );
}
