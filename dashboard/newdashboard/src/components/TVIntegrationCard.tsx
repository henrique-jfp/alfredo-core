import React, { useState, useEffect } from 'react';
import { Tv, CheckCircle } from 'lucide-react';
import { SkeletonBlock } from './ui/DashboardPrimitives';

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
      <div className="alfredo-card flex h-[300px] w-full flex-col gap-4 p-6 md:w-[400px]">
        <div className="flex items-center gap-4">
          <SkeletonBlock className="h-[52px] w-[52px] rounded-2xl" />
          <div className="flex-1 space-y-2">
            <SkeletonBlock className="h-4 w-32 rounded-full" />
            <SkeletonBlock className="h-3 w-24 rounded-full" />
          </div>
          <SkeletonBlock className="h-6 w-24 rounded-full" />
        </div>
        <div className="space-y-3">
          <SkeletonBlock className="h-3 w-full rounded-full" />
          <SkeletonBlock className="h-3 w-5/6 rounded-full" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <SkeletonBlock className="h-12 rounded-xl" />
          <SkeletonBlock className="h-12 rounded-xl" />
        </div>
        <div className="space-y-3">
          <SkeletonBlock className="h-12 rounded-xl" />
          <SkeletonBlock className="h-12 rounded-xl" />
        </div>
        <div className="flex gap-2 pt-1">
          <SkeletonBlock className="h-11 flex-1 rounded-full" />
          <SkeletonBlock className="h-11 w-28 rounded-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="alfredo-card flex h-fit w-full flex-col gap-4 p-6 md:w-[400px]">
      <div className="flex items-center gap-4 relative">
        <div className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1428A0] to-[#0D1B6E] text-white shadow-[0_0_20px_rgba(20,40,160,0.22)]">
          <Tv className="w-7 h-7" />
        </div>
        <div className="flex-1">
          <h2 className="text-[18px] font-semibold text-[color:var(--text-primary)]">Samsung TV</h2>
        </div>
        {config?.configured ? (
          <span className="alfredo-pill border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
            <CheckCircle className="w-3 h-3" /> Configurado
          </span>
        ) : (
          <span className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400">
            Não configurado
          </span>
        )}
      </div>

      <p className="text-[13px] leading-relaxed text-[color:var(--text-secondary)]">
        Controle o volume, abra apps (Netflix, YT) via voz e use o Auto-Mute para falar com o Alfredo.
      </p>

      <div className="mt-2 flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="alfredo-section-label">IP Address</label>
            <input
              type="text"
              value={ipAddress}
              onChange={e => setIpAddress(e.target.value)}
              placeholder="192.168.1.100"
              className="alfredo-input mt-1"
            />
          </div>
          <div>
            <label className="alfredo-section-label">MAC Address (WoL)</label>
            <input
              type="text"
              value={macAddress}
              onChange={e => setMacAddress(e.target.value)}
              placeholder="00:11:22:33:44:55"
              className="alfredo-input mt-1"
            />
          </div>
        </div>

        <div>
          <label className="alfredo-section-label">SmartThings PAT (Opcional)</label>
          <input
            type="password"
            value={stPat}
            onChange={e => setStPat(e.target.value)}
            placeholder="Personal Access Token"
            className="alfredo-input mt-1"
          />
        </div>
        
        <div>
          <label className="alfredo-section-label">SmartThings Device ID (Opcional)</label>
          <input
            type="text"
            value={stDeviceId}
            onChange={e => setStDeviceId(e.target.value)}
            placeholder="Device ID"
            className="alfredo-input mt-1"
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
            className="alfredo-pill flex-1 justify-center border-white/10 bg-white/[0.03] text-[color:var(--text-primary)] disabled:opacity-50"
          >
            {saving ? 'Salvando...' : 'Salvar Configuração'}
          </button>
          
          {config?.configured && (
            <button
              onClick={handleTestMute}
              className="alfredo-pill border-blue-500/20 bg-blue-500/10 text-blue-400"
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
