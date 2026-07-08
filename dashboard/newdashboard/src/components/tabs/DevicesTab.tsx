import React from 'react';
import { Lightbulb, Tv, PlugZap, Lock, Settings, Sparkles } from 'lucide-react';
import { TVIntegrationCard } from '../TVIntegrationCard';
import { EmptyState, SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';

export function DevicesTab() {
  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Casa"
        title="Dispositivos conectados"
        subtitle="O grid agora ocupa o espaço com intenção, mesmo quando a quantidade de hardware ainda é pequena."
        action={<StatusPulse label="Telemetria viva" tone="success" />}
      />

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <TVIntegrationCard />

        <div className="alfredo-card p-6">
          <SectionHeading
            eyebrow="Mapa da frota"
            title="Estado visual"
            subtitle="Um resumo rápido do ecossistema de dispositivos e do que ainda está por vir."
          />

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {[
              { icon: Lightbulb, title: 'Lâmpadas smart', copy: 'Zigbee, Matter e Wi-Fi', tone: 'warning' as const },
              { icon: PlugZap, title: 'Tomadas inteligentes', copy: 'Medição e corte', tone: 'success' as const },
              { icon: Lock, title: 'Fechaduras digitais', copy: 'Acesso e segurança', tone: 'danger' as const },
              { icon: Settings, title: 'Sensores', copy: 'Presença e temperatura', tone: 'info' as const },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="alfredo-card p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.03] text-[color:var(--text-secondary)]">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[15px] font-semibold text-[color:var(--text-primary)]">{item.title}</div>
                      <div className="mt-1 text-[13px] text-[color:var(--text-secondary)]">{item.copy}</div>
                    </div>
                  </div>
                  <div className="mt-4">
                    <StatusPulse label="Em breve" tone={item.tone} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="alfredo-card p-6">
        <SectionHeading
          eyebrow="Direção"
          title="Próximos dispositivos"
          subtitle="O espaço vazio virou promessa de expansão, não sobra de layout."
        />
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[
            { icon: Tv, title: 'TVs inteligentes', copy: 'Perfis de áudio e automações visuais.' },
            { icon: Sparkles, title: 'Iluminação ambiente', copy: 'Cenas por horário e presença.' },
            { icon: PlugZap, title: 'Energia monitorada', copy: 'Picos e consumo por cômodo.' },
            { icon: Settings, title: 'Sensores avançados', copy: 'Vazamento, movimento e temperatura.' },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="alfredo-empty min-h-[180px] justify-start p-5 text-left opacity-90">
                <div className="flex w-full items-center justify-between gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/5 bg-white/[0.03] text-[color:var(--text-secondary)]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <StatusPulse label="Em breve" tone="info" />
                </div>
                <div className="mt-5 w-full">
                  <div className="text-[15px] font-semibold text-[color:var(--text-primary)]">{item.title}</div>
                  <p className="mt-2 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{item.copy}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
