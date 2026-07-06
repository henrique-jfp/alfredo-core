import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipForward, SkipBack, Music } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface SpotifyState {
  is_playing: boolean;
  track_name?: string;
  artist_name?: string;
  album_art?: string;
  progress_ms?: number;
  duration_ms?: number;
  device_name?: string;
  error?: string;
}

export function SpotifyCard() {
  const [state, setState] = useState<SpotifyState | null>(null);
  const [localProgress, setLocalProgress] = useState(0);

  useEffect(() => {
    const fetchNowPlaying = async () => {
      try {
        const res = await fetch('/api/spotify/now-playing');
        const data = await res.json();
        if (!data.error) {
          setState(data);
          if (data.progress_ms) {
            setLocalProgress(data.progress_ms);
          }
        } else {
          setState({ is_playing: false });
        }
      } catch (e) {
        console.error("Failed to fetch spotify state", e);
      }
    };

    fetchNowPlaying();
    const interval = setInterval(fetchNowPlaying, 3000);
    return () => clearInterval(interval);
  }, []);

  // Animação de progresso local
  useEffect(() => {
    if (!state?.is_playing || !state.duration_ms) return;
    
    const interval = setInterval(() => {
      setLocalProgress(p => {
        const next = p + 1000;
        return next > state.duration_ms! ? state.duration_ms! : next;
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [state?.is_playing, state?.duration_ms, state?.track_name]);

  const handleControl = async (action: string) => {
    // Otimista
    if (action === 'play' && state) setState({ ...state, is_playing: true });
    if (action === 'pause' && state) setState({ ...state, is_playing: false });
    
    try {
      await fetch('/api/spotify/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      // Força fetch após 500ms para pegar estado real
      setTimeout(async () => {
        const res = await fetch('/api/spotify/now-playing');
        setState(await res.json());
      }, 500);
    } catch (e) {
      console.error("Failed to send command", e);
    }
  };

  if (!state || (!state.is_playing && !state.track_name)) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 flex flex-col items-center justify-center border border-white/10 h-[200px] shadow-lg">
        <Music className="w-10 h-10 text-emerald-500 mb-3 opacity-50" />
        <p className="text-white/50 text-sm font-medium">Spotify Desconectado ou Pausado</p>
      </div>
    );
  }

  const progressPercent = state.duration_ms 
    ? Math.min((localProgress / state.duration_ms) * 100, 100)
    : 0;

  return (
    <div className="relative overflow-hidden bg-black/40 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl transition-colors hover:bg-black/50 group">
      {/* Imagem de fundo borrada otimizada */}
      {state.album_art && (
        <>
          <div 
            className="absolute inset-0 opacity-30 bg-cover bg-center transition-opacity duration-1000"
            style={{ backgroundImage: `url(${state.album_art})` }}
          />
          <div className="absolute inset-0 backdrop-blur-3xl bg-black/40" />
        </>
      )}
      
      <div className="relative z-10 flex items-center gap-5">
        {/* Capa do Álbum com animação de entrada e hover */}
        <div className="relative w-20 h-20 rounded-xl overflow-hidden shadow-lg flex-shrink-0 group-hover:shadow-emerald-500/20 transition-all">
          <AnimatePresence mode="popLayout">
            <motion.img 
              key={state.album_art}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              src={state.album_art || "/default-album.png"} 
              alt="Album" 
              className="w-full h-full object-cover"
            />
          </AnimatePresence>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <motion.h3 
            key={state.track_name}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-white font-bold text-lg truncate drop-shadow-sm tracking-tight"
          >
            {state.track_name}
          </motion.h3>
          <motion.p 
            key={state.artist_name}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-emerald-400 text-sm font-medium truncate mt-0.5"
          >
            {state.artist_name}
          </motion.p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] uppercase font-bold tracking-wider text-white/40 bg-white/10 px-2 py-0.5 rounded-full">
              {state.device_name || "Spotify Connect"}
            </span>
            {state.is_playing && (
              <span className="flex gap-0.5 items-end h-3">
                <motion.span animate={{ height: [4, 10, 4] }} transition={{ repeat: Infinity, duration: 1 }} className="w-1 bg-emerald-500 rounded-full" />
                <motion.span animate={{ height: [8, 4, 8] }} transition={{ repeat: Infinity, duration: 1.2 }} className="w-1 bg-emerald-500 rounded-full" />
                <motion.span animate={{ height: [5, 12, 5] }} transition={{ repeat: Infinity, duration: 0.8 }} className="w-1 bg-emerald-500 rounded-full" />
              </span>
            )}
          </div>
        </div>

        {/* Controles */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => handleControl('prev')}
            className="p-2.5 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition-colors active:scale-95"
          >
            <SkipBack className="w-5 h-5 fill-current" />
          </button>
          
          <button 
            onClick={() => handleControl(state.is_playing ? 'pause' : 'play')}
            className="p-3 rounded-full bg-emerald-500 hover:bg-emerald-400 text-black transition-all active:scale-95 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40"
          >
            {state.is_playing ? (
              <Pause className="w-6 h-6 fill-current" />
            ) : (
              <Play className="w-6 h-6 fill-current ml-0.5" />
            )}
          </button>
          
          <button 
            onClick={() => handleControl('next')}
            className="p-2.5 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition-colors active:scale-95"
          >
            <SkipForward className="w-5 h-5 fill-current" />
          </button>
        </div>
      </div>

      {/* Barra de Progresso Animada */}
      <div className="absolute bottom-0 left-0 w-full h-1 bg-white/10 overflow-hidden">
        <motion.div 
          className="w-full h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)] origin-left"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progressPercent / 100 }}
          transition={{ ease: "linear", duration: 1 }}
        />
      </div>
    </div>
  );
}
