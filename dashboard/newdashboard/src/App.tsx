import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
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
import { CalendarTab } from './components/tabs/CalendarTab';
import { WeatherTab } from './components/tabs/WeatherTab';
import { VirtualKeyboard } from './components/VirtualKeyboard';
import { WebMic } from './components/WebMic';
import { AmbientBackground } from './components/AmbientBackground';
import { ToastProvider } from './components/Toast';

const tabVariants = {
  initial: { opacity: 0, y: 16, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -8, scale: 0.98 },
};

const tabTransition = {
  type: 'spring' as const,
  stiffness: 300,
  damping: 30,
  mass: 0.8,
};

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
      case 'visao-geral': return { title: 'Visão Geral', sub: 'Centro de controle da sua casa inteligente.', eyebrow: undefined };
      case 'dispositivos': return { title: 'Dispositivos', sub: 'Controle manual de aparelhos, luzes e sensores.', eyebrow: 'Casa Inteligente' };
      case 'integracoes': return { title: 'Integrações', sub: 'Conecte serviços externos para expandir os poderes.', eyebrow: 'Conexões Externas' };
      case 'rotinas': return { title: 'Rotinas Automáticas', sub: 'Ensine o Alfredo a ter iniciativa própria.', eyebrow: 'Automação' };
      case 'satelites': return { title: 'Controle de Frota', sub: 'Gerencie os satélites espalhados pela casa.', eyebrow: 'Rede de Nós' };
      case 'inteligencia': return { title: 'Inteligência', sub: 'Controle o Cérebro, as APIs e a Memória.', eyebrow: 'Núcleo Cognitivo' };
      case 'sonhos': return { title: 'Diário de Sonhos', sub: 'Exploração psicanalítica do seu subconsciente.', eyebrow: 'Astrofísica do Sono' };
      case 'calendario': return { title: 'Calendário', sub: 'Compromissos, eventos e lembretes da agenda.', eyebrow: 'Agenda' };
      case 'clima': return { title: 'Clima', sub: 'Condições atuais e previsão do tempo para sua região.', eyebrow: 'Meteorologia' };
      case 'configuracoes': return { title: 'Configurações', sub: 'Ajuste parâmetros globais, endereços e chaves.', eyebrow: 'Sistema' };
    }
  };

  const currentHeaders = getTabTitle(activeTab);

  const renderTab = () => {
    switch (activeTab) {
      case 'visao-geral': return <OverviewTab />;
      case 'dispositivos': return <DevicesTab />;
      case 'integracoes': return <IntegrationsTab />;
      case 'rotinas': return <RoutinesTab />;
      case 'satelites': return <SatellitesTab />;
      case 'inteligencia': return <IntelligenceTab />;
      case 'sonhos': return <DreamsTab />;
      case 'calendario': return <CalendarTab />;
      case 'clima': return <WeatherTab />;
      case 'configuracoes': return <SettingsTab />;
    }
  };

  return (
    <ToastProvider>
      <AmbientBackground />
      <div className="grain-overlay" />
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
          {activeTab !== 'visao-geral' && <Topbar title={currentHeaders.title} subtitle={currentHeaders.sub} eyebrow={currentHeaders.eyebrow} />}
          
          <div className="relative min-h-0 flex-1 overflow-hidden">
            <div className="h-full overflow-x-hidden overflow-y-auto pb-28 md:pb-6">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  variants={tabVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={tabTransition}
                >
                  {renderTab()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </main>
      </div>
    </ToastProvider>
  );
}
