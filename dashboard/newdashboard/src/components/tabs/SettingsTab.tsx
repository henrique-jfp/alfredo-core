import React, { useState, useEffect } from 'react';
import { Settings, MapPin, Mic2, Rss } from 'lucide-react';
import { api } from '../../lib/api';

export function SettingsTab() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  const [locations, setLocations] = useState([
    { id: 1, name: 'Casa', lat: '-22.9738', lon: '-43.1868', icon: '🏠' },
    { id: 2, name: 'Trabalho', lat: '-22.9321', lon: '-43.1787', icon: '💼' },
  ]);

  const handleAddLocation = () => {
    setLocations([
      ...locations, 
      { id: Date.now(), name: 'Novo Endereço', lat: '-23.000', lon: '-43.000', icon: '📍' }
    ]);
  };

  useEffect(() => {
    api.getSettings().then(data => {
      setSettings(data);
    });
  }, []);

  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.saveSettings(settings);
      // alert('Configurações salvas!'); // optional
    } catch (e) {
      console.error("Erro ao salvar:", e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex gap-6 h-full pb-10 overflow-y-auto custom-scrollbar">
      <div className="flex flex-col gap-6 w-1/2">
        {/* Assistente */}
        <div className="glass-panel p-6">
          <div className="flex items-center gap-4 border-b border-white/5 pb-4 mb-5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
              <Mic2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-zinc-100">Assistente</h2>
              <p className="text-[12px] text-zinc-500">Nome de ativação e voz</p>
            </div>
          </div>
          
          <div className="flex flex-col gap-4">
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Nome (Wake Word)</label>
              <input 
                type="text" 
                value={settings.assistant_name || 'alfredo'} 
                onChange={e => handleChange('assistant_name', e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" 
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Voz do Assistente</label>
              <select 
                value={settings.assistant_voice || 'pt-BR-FranciscaNeural'}
                onChange={e => handleChange('assistant_voice', e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none appearance-none cursor-pointer"
              >
                <option value="pt-BR-FranciscaNeural">Francisca (Feminino BR)</option>
                <option value="pt-BR-AntonioNeural">Antonio (Masculino BR)</option>
              </select>
            </div>
            <div className="flex gap-2 mt-2">
              <button className="flex-1 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium transition-all">
                 Ouvir Prévia
              </button>
              <button 
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 py-2.5 bg-gradient-to-r from-brass-400 to-brass-600 hover:from-brass-300 hover:to-brass-500 text-obsidian-900 font-bold rounded-lg shadow-lg transition-all disabled:opacity-50"
              >
                 {isSaving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>

        {/* APIs */}
        <div className="glass-panel p-6">
          <div className="flex items-center gap-4 border-b border-white/5 pb-4 mb-5">
            <div className="w-10 h-10 rounded-xl bg-brass-500/10 text-brass-400 flex items-center justify-center shrink-0">
              <Rss className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-zinc-100">APIs e Conteúdo</h2>
              <p className="text-[12px] text-zinc-500">Chaves externas e feeds</p>
            </div>
          </div>
          
          <div className="flex flex-col gap-4">
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Chave API Google Maps</label>
              <input 
                type="password" 
                value={settings.google_maps_key || ''} 
                onChange={e => handleChange('google_maps_key', e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" 
              />
              <p className="text-[10px] text-zinc-500 mt-1">Opcional. Se vazio, usa OSRM (gratuito).</p>
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">URL Feed RSS Notícias</label>
              <input 
                type="text" 
                value={settings.news_rss_url || 'https://g1.globo.com/rss/g1/'}
                onChange={e => handleChange('news_rss_url', e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" 
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 block">Cidade (Clima)</label>
              <input 
                type="text" 
                value={settings.weather_city || 'Rio de Janeiro'}
                onChange={e => handleChange('weather_city', e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-[14px] text-zinc-100 focus:border-brass-500/50 outline-none" 
              />
            </div>
            <button 
              onClick={handleSave}
              disabled={isSaving}
              className="w-full py-2.5 mt-2 bg-gradient-to-r from-brass-400 to-brass-600 hover:from-brass-300 hover:to-brass-500 text-obsidian-900 font-bold rounded-lg shadow-lg transition-all disabled:opacity-50"
            >
               {isSaving ? 'Salvando...' : 'Salvar Configurações'}
            </button>
          </div>
        </div>
      </div>

      <div className="w-1/2 flex flex-col gap-6">
         {/* Endereços */}
         <div className="glass-panel p-6 flex-grow">
          <div className="flex items-center gap-4 border-b border-white/5 pb-4 mb-5">
            <div className="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center shrink-0">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-zinc-100">Meus Endereços</h2>
              <p className="text-[12px] text-zinc-500">Localizações salvas para trânsito e clima</p>
            </div>
          </div>

          <div className="flex flex-col gap-3">
             {locations.map(loc => (
               <div key={loc.id} className="bg-white/[0.015] border border-white/5 hover:border-brass-500/20 p-4 rounded-xl flex items-center gap-4 transition-all">
                 <div className="w-10 h-10 rounded-lg bg-brass-500/10 flex items-center justify-center text-xl shrink-0">
                   {loc.icon}
                 </div>
                 <div className="flex-grow">
                   <div className="font-semibold text-[14px] text-zinc-100">{loc.name}</div>
                   <div className="text-[11px] font-mono text-zinc-500 mt-0.5">{loc.lat}, {loc.lon}</div>
                 </div>
                 <button className="text-zinc-500 hover:text-rose-400 transition-colors">🗑️</button>
               </div>
             ))}
             <button onClick={handleAddLocation} className="w-full py-3 mt-4 border border-dashed border-white/10 hover:border-brass-500/40 hover:bg-white/5 rounded-xl text-sm font-medium text-zinc-400 hover:text-brass-400 transition-all">
               + Adicionar Endereço
             </button>
          </div>
         </div>

         {/* Aparência (Temas) */}
         <div className="glass-panel p-6 flex-grow">
          <div className="flex items-center gap-4 border-b border-white/5 pb-4 mb-5">
            <div className="w-10 h-10 rounded-xl bg-pink-500/10 text-pink-400 flex items-center justify-center shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-zinc-100">Aparência</h2>
              <p className="text-[12px] text-zinc-500">Temas e cores (Preview)</p>
            </div>
          </div>
          <div className="flex gap-4">
             <div className="flex-1 border-2 border-brass-500/50 rounded-xl p-4 flex flex-col items-center cursor-pointer bg-white/5">
                <div className="w-8 h-8 rounded-full bg-brass-500 mb-2" />
                <span className="text-xs font-bold text-zinc-200">Brass (Atual)</span>
             </div>
             <div className="flex-1 border-2 border-transparent hover:border-white/20 rounded-xl p-4 flex flex-col items-center cursor-pointer bg-white/5 opacity-50 grayscale hover:grayscale-0 transition-all">
                <div className="w-8 h-8 rounded-full bg-blue-500 mb-2" />
                <span className="text-xs font-bold text-zinc-200">Safira</span>
             </div>
             <div className="flex-1 border-2 border-transparent hover:border-white/20 rounded-xl p-4 flex flex-col items-center cursor-pointer bg-white/5 opacity-50 grayscale hover:grayscale-0 transition-all">
                <div className="w-8 h-8 rounded-full bg-rose-500 mb-2" />
                <span className="text-xs font-bold text-zinc-200">Rubi</span>
             </div>
          </div>
         </div>
      </div>

    </div>
  );
}
