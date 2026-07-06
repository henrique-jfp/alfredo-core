import React, { useState, useEffect } from 'react';
import { Tv, CheckCircle, Loader2 } from 'lucide-react';

interface TVConfig {
  configured: boolean;
  room_id: string;
  ip_address: string;
  mac_address: string;
  smartthings_pat: string;
  smartthings_device_id: string;
}

export function TVIntegrationCard() {
  const [config, setConfig] = useState<TVConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // Form states
  const [ipAddress, setIpAddress] = useState('');
  const [macAddress, setMacAddress] = useState('');
  const [stPat, setStPat] = useState('');
  const [stDeviceId, setStDeviceId] = useState('');

  const roomId = 'ROOM_LIVING'; // Using hardcoded room for now

  useEffect(() => {
    fetch(`/api/tv/config/${roomId}`)
      .then(res => res.json())
      .then(data => {
        setConfig(data);
        if (data.configured) {
          setIpAddress(data.ip_address || '');
          setMacAddress(data.mac_address || '');
          setStPat(data.smartthings_pat || '');
          setStDeviceId(data.smartthings_device_id || '');
        }
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [roomId]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await fetch('/api/tv/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          ip_address: ipAddress,
          mac_address: macAddress,
          smartthings_pat: stPat,
          smartthings_device_id: stDeviceId
        }),
      });
      if (res.ok) {
        setSaveMsg('✓ Configuração salva com sucesso!');
        setConfig(prev => prev ? { ...prev, configured: true } : { configured: true } as any);
      } else {
        setSaveMsg('Erro ao salvar configuração.');
      }
    } catch (e) {
      setSaveMsg('Erro de conexão.');
    } finally {
      setSaving(false);
    }
  };

  const handleTestMute = async () => {
    try {
      await fetch(`/api/tv/control/${roomId}/mute?state=true`, { method: 'POST' });
      setTimeout(() => {
        fetch(`/api/tv/control/${roomId}/mute?state=false`, { method: 'POST' });
      }, 3000);
    } catch (e) {
      alert("Erro ao testar mute");
    }
  };

  if (loading) {
    return (
      <div className="w-[400px] glass-panel p-6 flex items-center justify-center h-[300px]">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="w-[400px] glass-panel p-6 flex flex-col gap-4 h-fit">
      <div className="flex items-center gap-4 relative">
        <div className="w-[52px] h-[52px] rounded-xl bg-gradient-to-br from-[#1428A0] to-[#0D1B6E] flex items-center justify-center text-white shrink-0 shadow-[0_0_20px_rgba(20,40,160,0.3)]">
          <Tv className="w-7 h-7" />
        </div>
        <div className="flex-1">
          <h2 className="text-[18px] font-bold text-zinc-100">Samsung TV</h2>
        </div>
        {config?.configured ? (
          <span className="bg-emerald-500/10 text-emerald-400 text-[9px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border border-emerald-500/20 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Configurado
          </span>
        ) : (
          <span className="bg-rose-500/10 text-rose-400 text-[9px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border border-rose-500/20">
            Não configurado
          </span>
        )}
      </div>

      <p className="text-[13px] text-zinc-400 leading-relaxed">
        Controle o volume, abra apps (Netflix, YT) via voz e use o Auto-Mute para falar com o Alfredo.
      </p>

      <div className="flex flex-col gap-3 mt-2">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">IP Address</label>
            <input
              type="text"
              value={ipAddress}
              onChange={e => setIpAddress(e.target.value)}
              placeholder="192.168.1.100"
              className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1428A0]/50 transition-colors"
            />
          </div>
          <div>
            <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">MAC Address (WoL)</label>
            <input
              type="text"
              value={macAddress}
              onChange={e => setMacAddress(e.target.value)}
              placeholder="00:11:22:33:44:55"
              className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1428A0]/50 transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">SmartThings PAT (Opcional)</label>
          <input
            type="password"
            value={stPat}
            onChange={e => setStPat(e.target.value)}
            placeholder="Personal Access Token"
            className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1428A0]/50 transition-colors"
          />
        </div>
        
        <div>
          <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium">SmartThings Device ID (Opcional)</label>
          <input
            type="text"
            value={stDeviceId}
            onChange={e => setStDeviceId(e.target.value)}
            placeholder="Device ID"
            className="w-full mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#1428A0]/50 transition-colors"
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
            {saving ? 'Salvando...' : 'Salvar Configuração'}
          </button>
          
          {config?.configured && (
            <button
              onClick={handleTestMute}
              className="px-4 py-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-blue-400 font-bold rounded-lg text-sm transition-all shadow-[0_0_15px_rgba(59,130,246,0.1)]"
              title="Muta a TV por 3 segundos para testar"
            >
              Testar Mute
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
