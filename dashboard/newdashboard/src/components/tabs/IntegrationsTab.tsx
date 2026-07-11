import React, { useState, useEffect } from 'react';
import { Music2, HelpCircle, X, ExternalLink, CheckCircle, Sparkles, Shield, Radio, Calendar, Link as LinkIcon, Loader2 } from 'lucide-react';
import { SectionHeading, StatusPulse, SkeletonBlock } from '../ui/DashboardPrimitives';

interface IntegrationStatus {
  is_configured: boolean;
  is_connected: boolean;
}

interface IntegrationsData {
  local_ip: string;
  spotify: IntegrationStatus;
  google_calendar: IntegrationStatus;
}

export function IntegrationsTab() {
  const [data, setData] = useState<IntegrationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    fetch('/api/dashboard/integrations')
      .then(r => r.json())
      .then(d => {
        setData(d);
        setClientId(d.spotify.is_configured ? '••••••••' : '');
        setClientSecret(d.spotify.is_configured ? '••••••••' : '');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (clientId === '••••••••' || clientSecret === '••••••••') {
      setSaveMsg('Preencha os campos com as credenciais do Spotify.');
      return;
    }
    if (!clientId || !clientSecret) {
      setSaveMsg('Preencha o Client ID e o Client Secret.');
      return;
    }
    setSaving(true);
    setSaveMsg('');
    try {
      const r = await fetch('/api/dashboard/integrations/spotify/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
      });
      const d = await r.json();
      if (r.ok) {
        setSaveMsg('Credenciais salvas com sucesso!');
        setData(prev => prev ? { ...prev, spotify: { ...prev.spotify, is_configured: true } } : prev);
      } else {
        setSaveMsg('Erro ao salvar: ' + (d.detail || 'desconhecido'));
      }
    } catch {
      setSaveMsg('Erro de conexão com o servidor.');
    } finally {
      setSaving(false);
    }
  };

  const handleTestSpotify = async () => {
    try {
      const res = await fetch('/api/dashboard/integrations/spotify/test', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        alert('Teste bem-sucedido! O Spotify respondeu.');
      } else {
        alert('Erro no teste: ' + data.error);
      }
    } catch (e) {
      alert('Erro de rede ao testar.');
    }
  };

  const handleConnectSpotify = () => {
    window.location.href = '/api/spotify/login';
  };

  const handleConnectGoogleCalendar = () => {
    window.location.href = '/api/auth/google/authorize';
  };

  if (loading) {
    return (
      <div className="grid h-full gap-5 pb-10 pr-2 overflow-y-auto xl:grid-cols-[1.1fr_0.9fr]">
        <div className="flex min-w-0 flex-col gap-5">
          <div className="alfredo-card p-6">
            <div className="flex items-center gap-4">
              <SkeletonBlock className="h-[52px] w-[52px] rounded-2xl" />
              <div className="flex-1 space-y-2">
                <SkeletonBlock className="h-4 w-32 rounded-full" />
                <SkeletonBlock className="h-3 w-24 rounded-full" />
              </div>
              <SkeletonBlock className="h-6 w-28 rounded-full" />
            </div>
            <div className="mt-5 space-y-3">
              <SkeletonBlock className="h-3 w-full rounded-full" />
              <SkeletonBlock className="h-3 w-5/6 rounded-full" />
            </div>
            <div className="mt-5 space-y-4">
              <SkeletonBlock className="h-12 rounded-xl" />
              <SkeletonBlock className="h-12 rounded-xl" />
              <div className="flex gap-2">
                <SkeletonBlock className="h-11 flex-1 rounded-full" />
                <SkeletonBlock className="h-11 flex-1 rounded-full" />
              </div>
            </div>
          </div>
        </div>
        <div className="alfredo-card p-6">
          <div className="space-y-3">
            <SkeletonBlock className="h-4 w-36 rounded-full" />
            <SkeletonBlock className="h-3 w-48 rounded-full" />
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <SkeletonBlock className="h-36 rounded-2xl" />
            <SkeletonBlock className="h-36 rounded-2xl" />
            <SkeletonBlock className="h-36 rounded-2xl" />
            <SkeletonBlock className="h-36 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  const sp = data?.spotify;
  const gc = data?.google_calendar;
  const localIp = data?.local_ip || 'localhost:10001';

  return (
    <>
      <div className="grid h-full gap-5 pb-10 pr-2 overflow-y-auto xl:grid-cols-[1.1fr_0.9fr]">
        <div className="flex min-w-0 flex-col gap-5">
          <div className="alfredo-card p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1DB954] to-[#169c46] text-white shadow-[0_0_20px_rgba(29,185,84,0.22)]">
                <Music2 className="w-7 h-7" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">Spotify</h2>
                  <button
                    onClick={() => setShowHelp(true)}
                    className="text-[color:var(--text-tertiary)] transition-colors hover:text-[color:var(--text-primary)]"
                    title="Ajuda: como configurar"
                  >
                    <HelpCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {sp?.is_connected ? (
                <StatusPulse label="Conectado" tone="success" />
              ) : (
                <span className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400">
                  {sp?.is_configured ? 'Não conectado' : 'Não configurado'}
                </span>
              )}
            </div>

            <p className="mt-4 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
              Controle músicas, playlists e alto-falantes pela voz em toda a casa de forma nativa.
            </p>

            <div className="mt-5 flex flex-col gap-3">
              <div>
                <label className="alfredo-section-label">Client ID</label>
                <input
                  type="text"
                  value={clientId}
                  onChange={e => setClientId(e.target.value)}
                  placeholder="seu-client-id-do-spotify"
                  className="alfredo-input mt-1"
                />
              </div>
              <div>
                <label className="alfredo-section-label">Client Secret</label>
                <input
                  type="password"
                  value={clientSecret}
                  onChange={e => setClientSecret(e.target.value)}
                  placeholder="seu-client-secret-do-spotify"
                  className="alfredo-input mt-1"
                />
              </div>
              
              {saveMsg && (
                <p className={`text-xs ${saveMsg.startsWith('✓') ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {saveMsg}
                </p>
              )}

              <div className="mt-1 flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="alfredo-pill flex-1 justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-primary)]"
                >
                  {saving ? 'Salvando...' : 'Salvar credenciais'}
                </button>
                {sp?.is_connected ? (
                  <button
                    onClick={handleTestSpotify}
                    className="alfredo-pill flex-1 justify-center border-blue-500/20 bg-blue-500/10 text-blue-400"
                  >
                    Testar
                  </button>
                ) : (
                  <button
                    onClick={handleConnectSpotify}
                    disabled={!sp?.is_configured}
                    className="alfredo-pill flex-1 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Log in
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="alfredo-card p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#4285F4] to-[#34a853] text-white shadow-[0_0_20px_rgba(66,133,244,0.22)]">
                <Calendar className="w-7 h-7" />
              </div>
              <div className="flex-1">
                <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">Google Calendar</h2>
              </div>
              {gc?.is_connected ? (
                <StatusPulse label="Conectado" tone="success" />
              ) : (
                <span className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400">
                  {gc?.is_configured ? 'Não conectado' : 'Não configurado'}
                </span>
              )}
            </div>

            <p className="mt-4 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
              Sincronize sua agenda: eventos, lembretes e resumo matinal automático pela voz.
            </p>

            <div className="mt-5 flex gap-2">
              {gc?.is_connected ? (
                <button className="alfredo-pill flex-1 justify-center border-blue-500/20 bg-blue-500/10 text-blue-400">
                  Sincronizar agora
                </button>
              ) : (
                <button
                  onClick={handleConnectGoogleCalendar}
                  className="alfredo-pill flex-1 justify-center border-brass-500/25 bg-brass-500 text-[color:var(--bg-base)]"
                >
                  Conectar Google Calendar
                </button>
              )}
            </div>
          </div>

          <div className="alfredo-card p-6">
            <SectionHeading
              eyebrow="Estado"
              title="Integração ativa"
              subtitle={`IP local: ${localIp}`}
              action={<StatusPulse label={sp?.is_connected || gc?.is_connected ? 'Online' : 'Aguardando'} tone={sp?.is_connected || gc?.is_connected ? 'success' : 'warning'} />}
            />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="alfredo-surface p-4">
                <div className="alfredo-section-label">Fluxo</div>
                <div className="mt-2 text-[15px] text-[color:var(--text-primary)]">Spotify via OAuth / Google Calendar via OAuth</div>
                <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">Conecte para tocar e controlar mídia e agenda por voz.</p>
              </div>
              <div className="alfredo-surface p-4">
                <div className="alfredo-section-label">Atalhos</div>
                <div className="mt-2 text-[15px] text-[color:var(--text-primary)]">`/api/spotify/login` · `/api/auth/google/authorize`</div>
                <p className="mt-1 text-[13px] text-[color:var(--text-secondary)]">Abre os fluxos de autenticação das contas.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-5">
          <div className="alfredo-card p-6">
            <SectionHeading
              eyebrow="Próximas conexões"
              title="Futuras integrações"
              subtitle="Os cards em breve ocupam o grid com peso e intenção, mesmo sem dados configurados."
            />

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {[
                { name: 'Philips Hue', subtitle: 'Cenas, zonas e automações', tone: 'info', icon: Sparkles },
                { name: 'Casa Segura', subtitle: 'Sensores, portas e alertas', tone: 'danger', icon: Shield },
                { name: 'Música local', subtitle: 'Players e rádios internos', tone: 'success', icon: Music2 },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.name} className="alfredo-card border-dashed border-white/10 p-4 opacity-80">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.03] text-[color:var(--text-secondary)]">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-[15px] font-semibold text-[color:var(--text-primary)]">{item.name}</div>
                        <div className="mt-1 text-[13px] text-[color:var(--text-secondary)]">{item.subtitle}</div>
                      </div>
                    </div>
                    <div className="mt-4">
                      <StatusPulse label="Em breve" tone="info" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

      </div>

      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="alfredo-card mx-4 max-h-[80vh] w-full max-w-lg overflow-y-auto p-8">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-[color:var(--text-primary)]">Como configurar o Spotify</h3>
              <button onClick={() => setShowHelp(false)} className="text-[color:var(--text-tertiary)] hover:text-[color:var(--text-primary)]">
                <X className="w-5 h-5" />
              </button>
            </div>

            <ol className="flex flex-col gap-5 text-sm text-[color:var(--text-secondary)]">
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#1DB954]/20 text-xs font-bold text-[#1DB954] mt-0.5">1</span>
                <div>
                  <p className="font-medium text-[color:var(--text-primary)]">Acesse o Spotify for Developers</p>
                  <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener noreferrer"
                     className="text-[#1DB954] hover:underline flex items-center gap-1 mt-1">
                    developer.spotify.com/dashboard <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">2</span>
                <div>
                  <p className="font-medium text-zinc-100">Crie um App</p>
                  <p className="text-zinc-400 mt-1">Clique em "Create App", dê qualquer nome e descrição.</p>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">3</span>
                <div>
                  <p className="font-medium text-zinc-100">Copie as credenciais</p>
                  <p className="text-zinc-400 mt-1">Na tela do App, copie o <strong>Client ID</strong> e o <strong>Client Secret</strong>.</p>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">4</span>
                <div>
                  <p className="font-medium text-zinc-100">Cole os dados aqui no Dashboard</p>
                  <p className="text-zinc-400 mt-1">Preencha os campos acima e clique em <strong>"Salvar Credenciais"</strong>.</p>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">5</span>
                <div>
                  <p className="font-medium text-zinc-100">Adicione o Redirect URI no Spotify</p>
                  <p className="text-zinc-400 mt-1">No seu App em "Edit Settings" → "Redirect URIs", adicione:</p>
                  <code className="block mt-2 px-3 py-2 bg-zinc-800 rounded-lg text-[#1DB954] text-xs break-all">
                    http://127.0.0.1:10001/api/spotify/callback
                  </code>
                  <p className="text-zinc-500 text-xs mt-2">Clique em "Add" e depois "Save".</p>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">6</span>
                <div>
                  <p className="font-medium text-zinc-100">Abra um SSH Tunnel</p>
                  <p className="text-zinc-400 mt-1">No seu computador, abra o terminal e execute:</p>
                  <code className="block mt-2 px-3 py-2 bg-zinc-800 rounded-lg text-[#1DB954] text-xs break-all">
                    ssh -L 10001:localhost:10001 pvserver@192.168.0.56
                  </code>
                  <p className="text-zinc-500 text-xs mt-2">Isso faz com que <strong>127.0.0.1:10001</strong> no seu PC aponte para o servidor Alfredo (necessário porque o Spotify bloqueia HTTP em IPs não-loopback).</p>
                </div>
              </li>

              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">7</span>
                <div>
                  <p className="font-medium text-zinc-100">Conecte sua conta</p>
                  <p className="text-zinc-400 mt-1">Com o SSH tunnel aberto, acesse <strong>http://127.0.0.1:10001</strong> no navegador e clique em <strong>"Conectar Spotify"</strong>. Faça login e autorize. Pronto!</p>
                  <p className="text-zinc-500 text-xs mt-2">Após conectar, você pode fechar o SSH tunnel e voltar a usar o endereço normal <strong>http://192.168.0.56:10001</strong>.</p>
                </div>
              </li>
            </ol>

            <div className="mt-6 p-4 bg-zinc-800/50 rounded-xl">
              <p className="text-xs text-zinc-400">
                <strong className="text-zinc-300">Requerimento:</strong> Sua conta Spotify precisa ser
                {' '}<strong className="text-zinc-300">Premium</strong> para controle de reprodução por API.
                Contas Free não conseguem tocar música pelo Alfredo.
              </p>
            </div>

              <button onClick={() => setShowHelp(false)} className="mt-6 w-full rounded-xl bg-[#1DB954] py-3 text-sm font-bold text-black transition-all hover:bg-[#169c46]">
                Entendi, vou configurar!
              </button>
          </div>
        </div>
      )}
    </>
  );
}
