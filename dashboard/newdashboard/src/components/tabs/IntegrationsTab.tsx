import React, { useState, useEffect } from 'react';
import { Music2, HelpCircle, X, ExternalLink, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface SpotifyStatus {
  is_configured: boolean;
  is_connected: boolean;
}

interface IntegrationsData {
  local_ip: string;
  spotify: SpotifyStatus;
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

  const handleConnect = () => {
    window.location.href = '/api/spotify/login';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  const sp = data?.spotify;
  const localIp = data?.local_ip || 'localhost:10001';

  return (
    <>
      <div className="flex gap-6 h-full pb-10 overflow-y-auto custom-scrollbar pr-2">
        <div className="flex flex-col gap-6 w-full">
          <div className="w-full max-w-[400px] glass-panel p-6 flex flex-col gap-4 h-fit">
            <div className="flex items-center gap-4 relative">
              <div className="w-[52px] h-[52px] rounded-xl bg-gradient-to-br from-[#1DB954] to-[#169c46] flex items-center justify-center text-white shrink-0 shadow-[0_0_20px_rgba(29,185,84,0.3)]">
                <Music2 className="w-7 h-7" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-[18px] font-bold text-zinc-100">Spotify</h2>
                  <button
                    onClick={() => setShowHelp(true)}
                    className="text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Ajuda: como configurar"
                  >
                    <HelpCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {sp?.is_connected ? (
                <span className="bg-emerald-500/10 text-emerald-400 text-[9px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border border-emerald-500/20 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Conectado
                </span>
              ) : (
                <span className="bg-rose-500/10 text-rose-400 text-[9px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border border-rose-500/20">
                  {sp?.is_configured ? 'Não conectado' : 'Não configurado'}
                </span>
              )}
            </div>

            <p className="text-[13px] text-zinc-400 leading-relaxed">
              Controle músicas, playlists e alto-falantes pela voz em toda a casa de forma nativa.
            </p>

            <div className="flex flex-col gap-3 mt-2">
              <div>
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">Client ID</label>
                <input
                  type="text"
                  value={clientId}
                  onChange={e => setClientId(e.target.value)}
                  placeholder="seu-client-id-do-spotify"
                  className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1DB954]/50 transition-colors"
                />
              </div>
              <div>
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">Client Secret</label>
                <input
                  type="password"
                  value={clientSecret}
                  onChange={e => setClientSecret(e.target.value)}
                  placeholder="seu-client-secret-do-spotify"
                  className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1DB954]/50 transition-colors"
                />
              </div>
              
              {saveMsg && (
                <p className={`text-xs ${saveMsg.startsWith('✓') ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {saveMsg}
                </p>
              )}

              <div className="flex gap-2 mt-1">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium transition-all text-zinc-200 disabled:opacity-50"
                >
                  {saving ? 'Salvando...' : 'Salvar Credenciais'}
                </button>
                {sp?.is_connected ? (
                  <button
                    onClick={handleTestSpotify}
                    className="flex-1 py-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-blue-400 font-bold rounded-lg text-sm transition-all shadow-[0_0_15px_rgba(59,130,246,0.1)]"
                  >
                    Testar
                  </button>
                ) : (
                  <button
                    onClick={handleConnect}
                    disabled={!sp?.is_configured}
                    className="flex-1 py-2.5 bg-[#1DB954] hover:bg-[#1ed760] text-black font-bold rounded-lg text-sm transition-all disabled:opacity-30 disabled:hover:bg-[#1DB954] shadow-[0_0_15px_rgba(29,185,84,0.3)] disabled:shadow-none"
                  >
                    Log In
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Coming Soon Cards Space */}
        <div className="flex-1 flex flex-col gap-6">
          <h2 className="text-[18px] font-bold text-zinc-100 flex items-center gap-2">
            Futuras Integrações <span className="text-xs bg-white/5 text-zinc-500 px-2 py-0.5 rounded-full border border-white/10">Em breve</span>
          </h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-panel p-5 opacity-40 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400">
                  <span className="font-bold text-lg">P</span>
                </div>
                <h3 className="text-[15px] font-bold text-zinc-100">Philips Hue</h3>
              </div>
              <p className="text-xs text-zinc-400">Controle avançado de lâmpadas, zonas e cenas.</p>
            </div>
            
            <div className="glass-panel p-5 opacity-40 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center text-orange-400">
                  <span className="font-bold text-lg">T</span>
                </div>
                <h3 className="text-[15px] font-bold text-zinc-100">Tuya / SmartLife</h3>
              </div>
              <p className="text-xs text-zinc-400">Integração nativa via local key e cloud API.</p>
            </div>

            <div className="glass-panel p-5 opacity-40 border-dashed border-white/10 select-none grayscale hover:grayscale-0 transition-all duration-500 cursor-not-allowed">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-rose-500/20 flex items-center justify-center text-rose-400">
                  <span className="font-bold text-lg">G</span>
                </div>
                <h3 className="text-[15px] font-bold text-zinc-100">Google Calendar</h3>
              </div>
              <p className="text-xs text-zinc-400">Resumo matinal com sua agenda do dia.</p>
            </div>
          </div>
        </div>

      </div>

      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-zinc-100">Como configurar o Spotify</h3>
              <button onClick={() => setShowHelp(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-5 h-5" />
              </button>
            </div>

            <ol className="flex flex-col gap-5 text-sm text-zinc-300">
              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-[#1DB954]/20 text-[#1DB954] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">1</span>
                <div>
                  <p className="font-medium text-zinc-100">Acesse o Spotify for Developers</p>
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

            <button
              onClick={() => setShowHelp(false)}
              className="w-full mt-6 py-3 bg-[#1DB954] hover:bg-[#169c46] rounded-xl text-sm font-bold text-black transition-all"
            >
              Entendi, vou configurar!
            </button>
          </div>
        </div>
      )}
    </>
  );
}
