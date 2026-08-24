import React, { useEffect, useState } from 'react';
import { Lightbulb, Tv, PlugZap, Lock, Settings, Sparkles, Fan, MonitorSpeaker, Cpu, RadioTower, Power, ArrowUp, ArrowDown } from 'lucide-react';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { cn } from '../../lib/utils';

interface Device {
  type: string;
  name: string;
  entity_id: string;
  state: string;
  stateKnown: boolean;
}

interface Room {
  id: string;
  name: string;
  devices: Device[];
}

export function DevicesTab() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchRooms = async () => {
    try {
      const res = await fetch('/api/dashboard/ambientes');
      if (!res.ok) throw new Error('Falha ao carregar ambientes');
      const data = await res.json();
      setRooms(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load environments', err);
      setError('Falha ao carregar os ambientes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRooms();
  }, []);

  const handleToggleDevice = async (device: Device) => {
    setActionInProgress(device.entity_id);
    try {
      if (device.entity_id.startsWith('text_command:')) {
        const cmd = device.entity_id.split(':')[1];
        await fetch('/api/dashboard/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd })
        });
      } else {
        await fetch('/api/smart-home/offline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            entity_id: device.entity_id,
            action: 'toggle'
          })
        });
      }
      
      await fetchRooms();
    } catch (err) {
      console.error('Action failed', err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleSetFanSpeed = async (device: Device, speed: number) => {
    setActionInProgress(`${device.entity_id}_${speed}`);
    try {
      const cmd = device.entity_id.split(':')[1]; // e.g. "ventilador da sala"
      const finalCmd = speed === 0 ? `desligar ${cmd}` : `${cmd} velocidade ${speed}`;
      await fetch('/api/dashboard/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: finalCmd })
      });
      await fetchRooms();
    } catch (err) {
      console.error('Action failed', err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleSetFanMode = async (device: Device, mode: 'ventilation' | 'exhaust') => {
    setActionInProgress(`${device.entity_id}_${mode}`);
    try {
      const cmd = device.entity_id.split(':')[1] || ''; // e.g. "ventilador quarto do casal"
      const roomStr = cmd.replace('ventilador ', '');
      const finalCmd = mode === 'ventilation' ? `ventilação ${roomStr}` : `exaustão ${roomStr}`;
      await fetch('/api/dashboard/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: finalCmd })
      });
      await fetchRooms();
    } catch (err) {
      console.error('Action failed', err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleSetLightColor = async (device: Device, rgb: number[]) => {
    setActionInProgress(`${device.entity_id}_color`);
    try {
      await fetch('/api/smart-home/offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: device.entity_id, action: 'set_color', rgb_color: rgb })
      });
      await fetchRooms();
    } catch (err) { console.error('Action failed', err); } 
    finally { setActionInProgress(null); }
  };

  const handleSetLightColorTemp = async (device: Device, kelvin: number) => {
    setActionInProgress(`${device.entity_id}_temp`);
    try {
      await fetch('/api/smart-home/offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: device.entity_id, action: 'set_color_temp', color_temp: kelvin })
      });
      await fetchRooms();
    } catch (err) { console.error('Action failed', err); } 
    finally { setActionInProgress(null); }
  };

  const handleSetLightBrightness = async (device: Device, percentage: number) => {
    setActionInProgress(`${device.entity_id}_brightness`);
    try {
      await fetch('/api/smart-home/offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: device.entity_id, action: 'set_brightness', brightness: Math.round((percentage / 100) * 255) })
      });
      await fetchRooms();
    } catch (err) { console.error('Action failed', err); } 
    finally { setActionInProgress(null); }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'light': return Lightbulb;
      case 'fan': 
      case 'fan_speed': return Fan;
      case 'tv': return Tv;
      case 'power_off': return Power;
      default: return Sparkles;
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <StatusPulse label="Carregando ambientes..." tone="success" />
      </div>
    );
  }

  if (error || rooms.length === 0) {
    return (
      <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
        <SectionHeading
          eyebrow="Arquitetura"
          title="Controle por Cômodos"
          subtitle="Agrupamento semântico dos dispositivos espalhados pela casa."
          action={<StatusPulse label="Rede Local Ativa" tone="success" />}
        />
        <EmptyState
          icon={RadioTower}
          title={error || "Nenhum ambiente encontrado"}
          description="Verifique a conexão com o servidor e o house_context.yaml."
          action={
            <button 
              onClick={fetchRooms}
              className="mt-4 rounded bg-white/10 px-4 py-2 text-sm font-medium hover:bg-white/20"
            >
              Tentar Novamente
            </button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Arquitetura"
        title="Controle por Cômodos"
        subtitle="Agrupamento semântico dos dispositivos espalhados pela casa."
        action={<StatusPulse label="Rede Local Ativa" tone="success" />}
      />

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-2">
        {rooms.map((room) => (
          <div key={room.id} className="alfredo-card p-5 md:p-6 flex flex-col min-h-0 transition-colors hover:border-white/10">
            <div className="mb-4">
              <h3 className="text-[16px] font-semibold text-[color:var(--text-primary)] tracking-tight">{room.name}</h3>
            </div>
            
            <div className="grid gap-2 mt-auto">
              {room.devices.map((device, idx) => {
                const Icon = getIcon(device.type);
                const isActive = device.state === 'on';
                const isWorking = actionInProgress === device.entity_id;
                
                const isAdvancedLight = device.entity_id.startsWith('light.');
                
                return (
                  <div key={idx} className={cn(
                    "flex flex-col gap-3 rounded-xl bg-white/[0.02] border border-white/5 p-3",
                    (device.type === 'fan_speed' || isAdvancedLight) ? "items-stretch" : "justify-center"
                  )}>
                    <div className="flex items-center justify-between min-w-0 w-full">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors",
                          isActive ? "bg-brass-500/10 border-brass-500/20 text-brass-400" : "bg-white/[0.03] border-white/5 text-[color:var(--text-tertiary)]",
                          isWorking ? "animate-pulse" : ""
                        )}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <span className="text-[13px] font-medium text-[color:var(--text-primary)] truncate">
                          {device.name}
                        </span>
                      </div>
                      
                      {device.type !== 'fan_speed' && (
                        <button 
                          onClick={() => handleToggleDevice(device)}
                          disabled={isWorking}
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-full transition-colors shrink-0",
                            isActive ? "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25" : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white",
                            isWorking ? "opacity-50 cursor-not-allowed" : ""
                          )}
                          title={device.stateKnown ? (isActive ? "Ligado" : "Desligado") : "Ação s/ Feedback"}
                        >
                          <Power className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                    
                    {device.type === 'fan_speed' && (
                      <div className="flex items-center justify-between gap-1 w-full mt-1">
                        {[0, 1, 2, 3, 4, 5, 6].map(speed => {
                          const isSpeedWorking = actionInProgress === `${device.entity_id}_${speed}`;
                          return (
                            <button
                              key={speed}
                              onClick={() => handleSetFanSpeed(device, speed)}
                              disabled={isSpeedWorking || actionInProgress !== null}
                              className={cn(
                                "flex-1 h-8 flex items-center justify-center rounded text-[11px] font-semibold transition-colors border border-white/5",
                                speed === 0 ? "hover:bg-red-500/20 hover:text-red-400" : "hover:bg-brass-500/20 hover:text-brass-400",
                                isSpeedWorking ? "animate-pulse bg-white/10" : "bg-white/[0.03] text-[color:var(--text-tertiary)]"
                              )}
                            >
                              {speed === 0 ? 'OFF' : speed}
                            </button>
                          );
                        })}
                      </div>
                    )}
                    
                    {device.type === 'fan_speed' && (
                      <div className="flex items-center justify-between gap-2 w-full mt-1">
                        <button
                          onClick={() => handleSetFanMode(device, 'exhaust')}
                          disabled={actionInProgress !== null}
                          className="flex-1 h-8 flex items-center justify-center gap-2 rounded text-[11px] font-semibold transition-colors border border-white/5 bg-white/[0.03] hover:bg-orange-500/20 hover:text-orange-400 text-[color:var(--text-tertiary)]"
                        >
                          <ArrowUp className="w-3 h-3" /> EXAUSTÃO
                        </button>
                        <button
                          onClick={() => handleSetFanMode(device, 'ventilation')}
                          disabled={actionInProgress !== null}
                          className="flex-1 h-8 flex items-center justify-center gap-2 rounded text-[11px] font-semibold transition-colors border border-white/5 bg-white/[0.03] hover:bg-cyan-500/20 hover:text-cyan-400 text-[color:var(--text-tertiary)]"
                        >
                          <ArrowDown className="w-3 h-3" /> VENTILAÇÃO
                        </button>
                      </div>
                    )}

                    {isAdvancedLight && isActive && (
                      <div className="flex flex-col gap-3 mt-2 border-t border-white/5 pt-3">
                        {/* Brilho */}
                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] uppercase tracking-wider text-white/40 font-semibold">Brilho</span>
                          <div className="flex gap-1">
                            {[20, 40, 60, 80, 100].map(pct => (
                              <button
                                key={pct}
                                onClick={() => handleSetLightBrightness(device, pct)}
                                disabled={actionInProgress !== null}
                                className="flex-1 h-6 rounded bg-white/[0.03] hover:bg-white/10 border border-white/5 text-[10px] text-white/60 transition-colors"
                              >
                                {pct}%
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Cores RGB */}
                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] uppercase tracking-wider text-white/40 font-semibold">Cores</span>
                          <div className="flex gap-1">
                            {[
                              { label: 'R', rgb: [255, 0, 0], color: 'bg-red-500' },
                              { label: 'G', rgb: [0, 255, 0], color: 'bg-green-500' },
                              { label: 'B', rgb: [0, 0, 255], color: 'bg-blue-500' },
                              { label: 'P', rgb: [255, 0, 255], color: 'bg-purple-500' },
                              { label: 'Y', rgb: [255, 255, 0], color: 'bg-yellow-400' },
                              { label: 'C', rgb: [0, 255, 255], color: 'bg-cyan-400' },
                            ].map(c => (
                              <button
                                key={c.label}
                                onClick={() => handleSetLightColor(device, c.rgb)}
                                disabled={actionInProgress !== null}
                                className={cn("flex-1 h-6 rounded border border-white/10 transition-transform hover:scale-105", c.color)}
                              />
                            ))}
                          </div>
                        </div>

                        {/* Branco */}
                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] uppercase tracking-wider text-white/40 font-semibold">Temperatura Branca</span>
                          <div className="flex gap-1">
                            {[
                              { label: 'Frio', k: 6500, color: 'bg-blue-100' },
                              { label: 'Neutro', k: 4000, color: 'bg-yellow-100' },
                              { label: 'Quente', k: 2700, color: 'bg-orange-200' },
                            ].map(c => (
                              <button
                                key={c.label}
                                onClick={() => handleSetLightColorTemp(device, c.k)}
                                disabled={actionInProgress !== null}
                                className={cn("flex-1 h-6 rounded border border-white/10 text-[10px] font-semibold text-black/60 transition-transform hover:scale-105", c.color)}
                              >
                                {c.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
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
