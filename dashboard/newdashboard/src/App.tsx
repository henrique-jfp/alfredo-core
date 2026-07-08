import React, { useEffect, useState } from 'react';
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
import { WebMic } from './components/WebMic';

export default function App() {
  const [activeTab, setActiveTab] = React.useState<TabId>('visao-geral');
  const [isServerMode, setIsServerMode] = useState(false);
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    // Check if mode is forced via URL or localStorage
    const params = new URLSearchParams(window.location.search);
    const urlMode = params.get('mode');
    
    if (urlMode === 'server') {
      setIsServerMode(true);
      localStorage.setItem('mode', 'server');
    } else if (urlMode === 'desktop' || urlMode === 'mobile') {
      setIsServerMode(false);
      localStorage.setItem('mode', urlMode);
    } else {
      const storedMode = localStorage.getItem('mode');
      if (storedMode === 'server') {
        setIsServerMode(true);
      }
    }
  }, []);

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
    <div className="flex h-[100dvh] w-full flex-col overflow-hidden bg-[color:var(--bg-base)] text-[color:var(--text-primary)] selection:bg-[rgba(212,162,78,0.28)] md:flex-row">
      {isServerMode && (
        <VirtualKeyboard onHeightChange={setKeyboardHeight} />
      )}
      <WebMic />
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main 
        className="relative z-10 flex min-w-0 flex-1 flex-col px-4 pt-4 transition-all duration-300 ease-out md:px-8 md:pt-6"
        style={{
          paddingBottom: keyboardHeight > 0 ? `${keyboardHeight}px` : undefined,
          height: '100dvh'
        }}
      >
        <Topbar title={currentHeaders.title} subtitle={currentHeaders.sub} />
        
        <div className="relative min-h-0 flex-1 overflow-hidden">
          <div className="h-full overflow-x-hidden overflow-y-auto pb-28 md:pb-6 fade-up">
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
