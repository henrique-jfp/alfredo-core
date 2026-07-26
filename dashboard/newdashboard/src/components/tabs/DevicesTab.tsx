import React from 'react';
import { Lightbulb, Tv, PlugZap, Lock, Settings, Sparkles, Fan, MonitorSpeaker, Cpu, RadioTower, Power } from 'lucide-react';
import { TVIntegrationCard } from '../TVIntegrationCard';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { cn } from '../lib/utils';

const ROOMS = [
  {
    id: 'sala',
    name: 'Sala de Estar',
    description: 'Central principal da casa',
    devices: [
      { name: 'Cérebro (Servidor)', icon: Cpu, active: true },
      { name: 'Satélite Sala', icon: MonitorSpeaker, active: true },
      { name: 'Luz Principal', icon: Lightbulb, active: false },
      { name: 'Ventilador Teto', icon: Fan, active: false },
    ]
  },
  {
    id: 'quarto_casal',
    name: 'Quarto Casal',
    description: 'Controle mestre via IR e RF',
    devices: [
      { name: 'Satélite Quarto', icon: MonitorSpeaker, active: true },
      { name: 'Hub Universal (IR+RF)', icon: RadioTower, active: true },
      { name: 'Luzes (RF)', icon: Lightbulb, active: false },
      { name: 'Ventilador (RF)', icon: Fan, active: false },
      { name: 'TV Samsung', icon: Tv, active: false },
      { name: 'Box da Claro/Net', icon: PlugZap, active: false },
    ]
  },
  {
    id: 'quarto_laura',
    name: 'Quarto da Laura',
    description: 'Automação conforto',
    devices: [
      { name: 'Satélite Laura', icon: MonitorSpeaker, active: true },
      { name: 'Luzes', icon: Lightbulb, active: false },
      { name: 'Ventilador Teto', icon: Fan, active: false },
    ]
  },
  {
    id: 'servicos',
    name: 'Áreas Frias',
    description: 'Escritório, Cozinha e Banheiro',
    devices: [
      { name: 'Lâmpadas Smart', icon: Lightbulb, active: false },
      { name: 'Sensores de Presença', icon: Settings, active: false },
    ]
  }
];

export function DevicesTab() {
  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Arquitetura"
        title="Controle por Cômodos"
        subtitle="Agrupamento semântico dos dispositivos espalhados pela casa."
        action={<StatusPulse label="Rede Local Ativa" tone="success" />}
      />

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-2">
        {ROOMS.map((room) => (
          <div key={room.id} className="alfredo-card p-5 md:p-6 flex flex-col min-h-0 transition-colors hover:border-white/10">
            <div className="mb-4">
              <h3 className="text-[16px] font-semibold text-[color:var(--text-primary)] tracking-tight">{room.name}</h3>
              <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">{room.description}</p>
            </div>
            
            <div className="grid gap-2 mt-auto">
              {room.devices.map((device, idx) => {
                const Icon = device.icon;
                return (
                  <div key={idx} className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/5 p-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
                        device.active ? "bg-brass-500/10 border-brass-500/20 text-brass-400" : "bg-white/[0.03] border-white/5 text-[color:var(--text-tertiary)]"
                      )}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <span className="text-[13px] font-medium text-[color:var(--text-primary)] truncate">
                        {device.name}
                      </span>
                    </div>
                    
                    <button 
                      disabled={!device.active && device.name.includes('Satélite') === false} 
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-full transition-colors shrink-0",
                        device.active ? "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25" : "bg-white/5 text-zinc-600 cursor-not-allowed"
                      )}
                    >
                      <Power className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4">
        <SectionHeading
          eyebrow="Integração Direta"
          title="Televisão Mestre"
          subtitle="Controle focado na TV do Quarto Casal via protocolo local."
        />
        <div className="mt-4 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <TVIntegrationCard />
        </div>
      </div>
    </div>
  );
}
