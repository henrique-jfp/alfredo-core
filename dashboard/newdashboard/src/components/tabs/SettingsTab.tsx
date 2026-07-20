import React, { useState, useEffect } from 'react';
import { Settings, MapPin, Mic2, Rss, Palette, CheckCircle2, Sparkles, Trash2, Plus } from 'lucide-react';
import { api } from '../../lib/api';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { cn } from '../../lib/utils';

interface Location {
  id: number;
  name: string;
  latitude: string;
  longitude: string;
  icon: string;
}

export function SettingsTab() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  const [locations, setLocations] = useState<Location[]>([]);
  const [locationsLoading, setLocationsLoading] = useState(true);

  const [isAddingLocation, setIsAddingLocation] = useState(false);
  const [newLocName, setNewLocName] = useState('');
  const [newLocLat, setNewLocLat] = useState('');
  const [newLocLng, setNewLocLng] = useState('');
  const [newLocIcon, setNewLocIcon] = useState('📍');

  useEffect(() => {
    api.getSettings().then((data) => {
      setSettings(data || {});
    }).catch((err) => {
      console.error('Erro ao carregar configurações:', err);
      setSettings({});
    });
    api.getLocations().then((data) => {
      setLocations(Array.isArray(data) ? data : []);
      setLocationsLoading(false);
    }).catch((err) => {
      console.error('Erro ao carregar locais:', err);
      setLocations([]);
      setLocationsLoading(false);
    });
  }, []);

  const handleChange = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.saveSettings(settings);
    } catch (e) {
      console.error('Erro ao salvar:', e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNewLocation = async () => {
    if (!newLocName || !newLocLat || !newLocLng) return;
    const newLoc = { name: newLocName, latitude: newLocLat, longitude: newLocLng, icon: newLocIcon };
    try {
      const created = await api.createLocation(newLoc);
      setLocations([...locations, created]);
      setIsAddingLocation(false);
      setNewLocName('');
      setNewLocLat('');
      setNewLocLng('');
    } catch (e) {
      console.error('Erro ao criar endereço:', e);
    }
  };

  const handleDeleteLocation = async (id: number) => {
    try {
      await api.deleteLocation(id);
      setLocations(locations.filter((l) => l.id !== id));
    } catch (e) {
      console.error('Erro ao excluir endereço:', e);
    }
  };

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Sistema"
        title="Configurações"
        subtitle="A estrutura continua densa, mas agora com a mesma linguagem visual do resto do dashboard."
        action={<StatusPulse label="Persistência ativa" tone="success" />}
      />

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="flex min-h-0 flex-col gap-5">
          <div className="alfredo-card p-6">
            <div className="flex items-center gap-4 border-b border-white/5 pb-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400">
                <Mic2 className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">Assistente</h2>
                <p className="text-[13px] text-[color:var(--text-secondary)]">Nome de ativação e voz</p>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-4">
              <div>
                <label className="alfredo-section-label">Nome (wake word)</label>
                <input
                  type="text"
                  value={settings.assistant_name || 'alfredo'}
                  onChange={(e) => handleChange('assistant_name', e.target.value)}
                  className="alfredo-input mt-1"
                />
              </div>
              <div>
                <label className="alfredo-section-label">Voz do assistente</label>
                <select
                  value={settings.assistant_voice || 'pt-BR-FranciscaNeural'}
                  onChange={(e) => handleChange('assistant_voice', e.target.value)}
                  className="alfredo-input mt-1 appearance-none cursor-pointer"
                >
                  <option value="pt-BR-FranciscaNeural">Francisca (Feminino BR)</option>
                  <option value="pt-BR-AntonioNeural">Antonio (Masculino BR)</option>
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button className="alfredo-pill flex-1 justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-primary)]">
                  Ouvir prévia
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="alfredo-pill flex-1 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSaving ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </div>
          </div>

          <div className="alfredo-card p-6">
            <div className="flex items-center gap-4 border-b border-white/5 pb-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brass-500/10 text-brass-400">
                <Rss className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">APIs e conteúdo</h2>
                <p className="text-[13px] text-[color:var(--text-secondary)]">Chaves externas e feeds</p>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-4">
              <div>
                <label className="alfredo-section-label">Chave API Google Maps</label>
                <input
                  type="password"
                  value={settings.google_maps_key || ''}
                  onChange={(e) => handleChange('google_maps_key', e.target.value)}
                  className="alfredo-input mt-1"
                />
                <p className="mt-1 text-[10px] text-[color:var(--text-tertiary)]">Opcional. Se vazio, usa OSRM gratuito.</p>
              </div>
              <div>
                <label className="alfredo-section-label">URL feed RSS notícias</label>
                <input
                  type="text"
                  value={settings.news_rss_url || 'https://g1.globo.com/rss/g1/'}
                  onChange={(e) => handleChange('news_rss_url', e.target.value)}
                  className="alfredo-input mt-1"
                />
              </div>
              <div>
                <label className="alfredo-section-label">Cidade (clima)</label>
                <input
                  type="text"
                  value={settings.weather_city || 'Rio de Janeiro'}
                  onChange={(e) => handleChange('weather_city', e.target.value)}
                  className="alfredo-input mt-1"
                />
              </div>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="alfredo-pill mt-2 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSaving ? 'Salvando...' : 'Salvar configurações'}
              </button>
            </div>
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-5">
          <div className="alfredo-card p-6">
            <SectionHeading
              eyebrow="Localização"
              title="Meus endereços"
              subtitle="As localizações agora ocupam um card com ritmo próprio."
            />

            <div className="mt-5 flex flex-col gap-3">
              {locationsLoading ? (
                <div className="flex items-center gap-2 text-[color:var(--text-tertiary)] text-sm">
                  <span className="animate-spin">⟳</span> Carregando endereços...
                </div>
              ) : (
                <>
                  {locations.map((loc) => (
                    <div key={loc.id} className="flex items-center gap-4 rounded-2xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.04]">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-brass-500/10 text-xl">
                        {loc.icon}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[14px] font-semibold text-[color:var(--text-primary)]">{loc.name}</div>
                        <div className="mt-0.5 font-mono text-[11px] text-[color:var(--text-tertiary)]">
                          {loc.latitude}, {loc.longitude}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteLocation(loc.id)}
                        className="text-[color:var(--text-tertiary)] transition-colors hover:text-rose-400"
                        title="Excluir endereço"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  ))}
                  {isAddingLocation ? (
                    <div className="flex flex-col gap-3 rounded-2xl border border-brass-500/30 bg-brass-500/5 p-4 mt-2">
                      <div className="text-[13px] font-semibold text-brass-400">Novo Endereço</div>
                      
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder="Nome do local (ex: Casa, Trabalho)"
                          value={newLocName}
                          onChange={(e) => setNewLocName(e.target.value)}
                          className="alfredo-input flex-1 font-medium"
                        />
                      </div>
                      
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder="Latitude"
                          value={newLocLat}
                          onChange={(e) => setNewLocLat(e.target.value)}
                          className="alfredo-input flex-1 font-mono text-sm"
                        />
                        <input
                          type="text"
                          placeholder="Longitude"
                          value={newLocLng}
                          onChange={(e) => setNewLocLng(e.target.value)}
                          className="alfredo-input flex-1 font-mono text-sm"
                        />
                      </div>
                      
                      <div className="flex gap-2 mt-1">
                        <button
                          onClick={() => setIsAddingLocation(false)}
                          className="flex-1 rounded-xl border border-white/10 bg-transparent py-2.5 text-[11px] font-bold uppercase tracking-widest text-[color:var(--text-primary)] transition-colors hover:bg-white/5"
                        >
                          Cancelar
                        </button>
                        <button
                          onClick={handleSaveNewLocation}
                          disabled={!newLocName || !newLocLat || !newLocLng}
                          className="flex-1 rounded-xl bg-brass-600 py-2.5 text-[11px] font-bold uppercase tracking-widest text-[color:var(--bg-base)] transition-colors hover:bg-brass-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Salvar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setIsAddingLocation(true)}
                      className="alfredo-empty mt-2 border-dashed py-4 text-[14px] text-[color:var(--text-secondary)] hover:border-brass-500/30 hover:text-brass-300 flex items-center justify-center gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      Adicionar endereço
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="alfredo-card p-6">
            <SectionHeading
              eyebrow="Aparência"
              title="Swatches com preview"
              subtitle="Cada tema mostra mais do que uma cor solta: ele sugere o clima do dashboard."
            />

            <div className="mt-5 grid gap-4 md:grid-cols-3">
              {[
                { name: 'Brass', tone: 'brass', swatch: 'bg-brass-500', active: true },
                { name: 'Safira', tone: 'info', swatch: 'bg-blue-500', active: false },
                { name: 'Rubi', tone: 'danger', swatch: 'bg-rose-500', active: false },
              ].map((theme) => (
                <button
                  key={theme.name}
                  className={cn(
                    'alfredo-card p-4 text-left transition-all',
                    theme.active ? 'border-brass-500/25 bg-brass-500/10' : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className={cn('h-10 w-10 rounded-2xl', theme.swatch)} />
                    {theme.active ? <CheckCircle2 className="h-4 w-4 text-brass-400" /> : <Palette className="h-4 w-4 text-[color:var(--text-tertiary)]" />}
                  </div>
                  <div className="mt-4 text-[15px] font-semibold text-[color:var(--text-primary)]">{theme.name}</div>
                  <div className="mt-2 rounded-2xl border border-white/5 bg-black/20 p-3">
                    <div className="h-2 w-2/3 rounded-full bg-white/10" />
                    <div className="mt-2 h-2 w-1/2 rounded-full bg-white/8" />
                    <div className="mt-3 flex items-center gap-2">
                      <Sparkles className={cn('h-3.5 w-3.5', theme.active ? 'text-brass-300' : 'text-[color:var(--text-tertiary)]')} />
                      <span className="text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">Preview do dashboard</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
