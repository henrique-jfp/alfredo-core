import React from 'react';
import { Lightbulb, Tv, PlugZap, Lock, Settings } from 'lucide-react';
import { TVIntegrationCard } from '../TVIntegrationCard';

export function DevicesTab() {
  return (
    <div className="flex flex-col gap-6 h-full pb-10 overflow-y-auto custom-scrollbar pr-2">
      <div className="flex items-center justify-between mb-2 shrink-0">
        <div>
          <h2 className="text-xl font-bold text-zinc-100">Dispositivos Conectados</h2>
          <p className="text-sm text-zinc-400">Controle e gerencie o hardware da sua Casa Inteligente</p>
        </div>
      </div>

      {/* Dispositivos Ativos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 shrink-0">
        <TVIntegrationCard />
      </div>

      {/* Futuros Dispositivos */}
      <div className="mt-8 shrink-0">
        <h2 className="text-[18px] font-bold text-zinc-100 flex items-center gap-2 mb-4">
          Futuros Dispositivos <span className="text-xs bg-white/5 text-zinc-500 px-2 py-0.5 rounded-full border border-white/10">Em breve</span>
        </h2>
        
        <div className="flex flex-nowrap md:grid md:grid-cols-3 lg:grid-cols-4 gap-4 overflow-x-auto overflow-y-hidden custom-scrollbar pb-4 -mx-4 px-4 md:mx-0 md:px-0 md:pb-0">
          
          <div className="glass-panel p-5 opacity-50 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed flex flex-col items-center justify-center text-center gap-3 min-w-[160px] shrink-0">
            <div className="w-12 h-12 rounded-full bg-yellow-500/10 flex items-center justify-center text-yellow-500">
              <Lightbulb className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-zinc-200">Lâmpadas Smart</h3>
              <p className="text-[11px] text-zinc-500 mt-1">Zigbee / Matter / Wi-Fi</p>
            </div>
          </div>

          <div className="glass-panel p-5 opacity-50 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed flex flex-col items-center justify-center text-center gap-3 min-w-[160px] shrink-0">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
              <PlugZap className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-zinc-200">Tomadas Inteligentes</h3>
              <p className="text-[11px] text-zinc-500 mt-1">Medição e Corte</p>
            </div>
          </div>

          <div className="glass-panel p-5 opacity-50 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed flex flex-col items-center justify-center text-center gap-3 min-w-[160px] shrink-0">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-500">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-zinc-200">Fechaduras Digitais</h3>
              <p className="text-[11px] text-zinc-500 mt-1">Acesso e Segurança</p>
            </div>
          </div>
          
          <div className="glass-panel p-5 opacity-50 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed flex flex-col items-center justify-center text-center gap-3 min-w-[160px] shrink-0">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
              <Settings className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-zinc-200">Sensores</h3>
              <p className="text-[11px] text-zinc-500 mt-1">Presença, Temperatura</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
