import React from 'react';
import { Sidebar, TabId } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { OverviewTab } from './components/tabs/OverviewTab';
import { SatellitesTab } from './components/tabs/SatellitesTab';
import { IntelligenceTab } from './components/tabs/IntelligenceTab';
import { RoutinesTab } from './components/tabs/RoutinesTab';
import { DreamsTab } from './components/tabs/DreamsTab';
import { SettingsTab } from './components/tabs/SettingsTab';
import { IntegrationsTab } from './components/tabs/IntegrationsTab';
import { DevicesTab } from './components/tabs/DevicesTab';
import { VirtualKeyboard } from './components/VirtualKeyboard';

export default function App() {
  const [activeTab, setActiveTab] = React.useState<TabId>('visao-geral');

  const getTabTitle = (tab: TabId) => {
    switch (tab) {
      case 'visao-geral': return { title: 'Visão Geral', sub: 'Centro de controle da sua casa inteligente.' };
      case 'dispositivos': return { title: 'Dispositivos', sub: 'Controle manual de aparelhos, luzes e sensores.' };
      case 'integracoes': return { title: 'Integrações', sub: 'Conecte serviços externos para expandir os poderes.' };
      case 'rotinas': return { title: 'Rotinas Automáticas', sub: 'Ensine o Alfredo a ter iniciativa própria.' };
      case 'satelites': return { title: 'Controle de Frota', sub: 'Gerencie os satélites espalhados pela casa.' };
      case 'inteligencia': return { title: 'Inteligência', sub: 'Controle o Cérebro, as APIs e a Memória.' };
      case 'sonhos': return { title: 'Diário de Sonhos', sub: 'Exploração psicanalítica do seu subconsciente.' };
      case 'configuracoes': return { title: 'Configurações', sub: 'Ajuste parâmetros globais, endereços e chaves.' };
    }
  };

  const currentHeaders = getTabTitle(activeTab);

  return (
    <div className="flex h-screen w-full bg-obsidian-900 text-zinc-100 overflow-hidden selection:bg-brass-500/30">
      <VirtualKeyboard />
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="flex-grow flex flex-col pt-6 px-8 h-full min-w-0 relative z-10">
        <Topbar title={currentHeaders.title} subtitle={currentHeaders.sub} />
        
        <div className="flex-grow min-h-0 relative">
          <div className="absolute inset-0 animate-in fade-in duration-500">
            {activeTab === 'visao-geral' && <OverviewTab />}
            {activeTab === 'dispositivos' && <DevicesTab />}
            {activeTab === 'integracoes' && <IntegrationsTab />}
            {activeTab === 'rotinas' && <RoutinesTab />}
            {activeTab === 'satelites' && <SatellitesTab />}
            {activeTab === 'inteligencia' && <IntelligenceTab />}
            {activeTab === 'sonhos' && <DreamsTab />}
            {activeTab === 'configuracoes' && <SettingsTab />}
          </div>
        </div>
      </main>
    </div>
  );
}
