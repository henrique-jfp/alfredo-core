import React from 'react';
import { Lightbulb, Tv, PlugZap, Lock, Settings, Sparkles, Fan, MonitorSpeaker, Cpu, RadioTower, Power } from 'lucide-react';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { cn } from '../../lib/utils';

const ROOMS = [
  {
    id: 'sala',
    name: 'Sala',
    description: 'Ambiente central da casa',
    devices: [
      { name: 'Cérebro (Servidor)', icon: Cpu, active: true, stateKnown: true },
      { name: 'Satélite Sala', icon: MonitorSpeaker, active: true, stateKnown: true },
      { name: 'TV UHD Samsung 50"', icon: Tv, active: true, stateKnown: true },
      { name: 'Ventilador da Sala (Luz/Motor)', icon: Fan, active: false, stateKnown: false },
    ]
  },
  {
    id: 'quarto_casal',
    name: 'Quarto Casal',
    description: 'Quarto principal',
    devices: [
      { name: 'Satélite Quarto', icon: MonitorSpeaker, active: true, stateKnown: true },
      { name: 'Hub Universal (IR+RF)', icon: RadioTower, active: true, stateKnown: true },
      { name: 'Ventilador do Quarto (Luz/Motor)', icon: Fan, active: false, stateKnown: false },
    ]
  },
  {
    id: 'quarto_laura',
    name: 'Quarto da Filha',
    description: 'Quarto da Laura',
    devices: [
      { name: 'Satélite Laura', icon: MonitorSpeaker, active: true, stateKnown: true },
      { name: 'Ventilador da Laura (Luz/Motor)', icon: Fan, active: false, stateKnown: false },
    ]
  },
  {
    id: 'cozinha',
    name: 'Cozinha',
    description: 'Área de serviço',
    devices: [
      { name: 'Satélite Cozinha', icon: MonitorSpeaker, active: true, stateKnown: true },
      { name: 'Geladeira', icon: PlugZap, active: false, stateKnown: false },
      { name: 'Lava e Seca Brastemp', icon: PlugZap, active: false, stateKnown: false },
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
                    {device.stateKnown ? (
                      <button 
                        className={cn(
                          "flex h-7 w-7 items-center justify-center rounded-full transition-colors shrink-0",
                          device.active ? "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25" : "bg-white/5 text-zinc-600 hover:bg-white/10 hover:text-white"
                        )}
                        title={device.active ? "Ligado" : "Desligado"}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </button>
                    ) : (
                      <span className="text-[10px] uppercase font-semibold tracking-wider text-[color:var(--text-tertiary)] opacity-60">
                        Via RF/IR (S/ Feedback)
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
