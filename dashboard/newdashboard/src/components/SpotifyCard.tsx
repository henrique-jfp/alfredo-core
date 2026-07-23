import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Play, Pause, SkipForward, SkipBack, Music } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';
import type { SpotifyState } from '../types';

export function SpotifyCard() {
  const [state, setState] = useState<SpotifyState | null>(null);
  const [localProgress, setLocalProgress] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const previousStateRef = useRef<SpotifyState | null>(null);

  useEffect(() => {
    const connectSSE = () => {
      const es = new EventSource('/api/spotify/now-playing/stream');
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (!data.error) {
            setState(data);
            if (data.progress_ms) {
              setLocalProgress(data.progress_ms);
            }
          } else {
            setState({ is_playing: false });
          }
        } catch (e) {
          console.error("Failed to parse SSE data", e);
        }
      };

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        setTimeout(connectSSE, 3000);
      };
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

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

  const handleControl = useCallback(async (action: string) => {
    // Snapshot previous state for rollback on failure
    previousStateRef.current = state;

    // Optimistic update
    if (state) {
      if (action === 'play') setState({ ...state, is_playing: true });
      if (action === 'pause') setState({ ...state, is_playing: false });
    }

    try {
      await api.controlSpotify(action);
    } catch (e) {
      console.error("Failed to send command", e);
      // Rollback on failure
      if (previousStateRef.current) {
        setState(previousStateRef.current);
      }
    }
  }, [state]);

  if (!state || (!state.is_playing && !state.track_name)) {
    return (
      <div className="alfredo-card flex h-[200px] flex-col items-center justify-center p-6">
        <Music className="mb-3 h-10 w-10 text-emerald-400/70" />
        <p className="text-sm font-medium text-[color:var(--text-secondary)]">Spotify desconectado ou pausado</p>
      </div>
    );
  }

  const progressPercent = state.duration_ms
    ? Math.min((localProgress / state.duration_ms) * 100, 100)
    : 0;

  return (
    <div className="alfredo-card group relative overflow-hidden p-5 transition-colors hover:bg-[color:var(--bg-surface-2)]">
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
            className="text-sm font-medium text-emerald-400 truncate mt-0.5"
          >
            {state.artist_name}
          </motion.p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[color:var(--text-secondary)] bg-white/[0.04] px-2 py-0.5 rounded-full border border-white/5">
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

        <div className="flex items-center gap-3">
            <button
              onClick={() => handleControl('prev')}
            className="rounded-full p-2.5 text-[color:var(--text-secondary)] transition-colors hover:bg-white/[0.05] hover:text-[color:var(--text-primary)] active:scale-95"
            aria-label="Faixa anterior"
          >
            <SkipBack className="w-5 h-5 fill-current" />
          </button>

          <button
            onClick={() => handleControl(state.is_playing ? 'pause' : 'play')}
            className="rounded-full bg-brass-500 p-3 text-[color:var(--bg-base)] transition-all hover:bg-brass-400 active:scale-95 shadow-[0_0_20px_rgba(212,162,78,0.2)] hover:shadow-[0_0_28px_rgba(212,162,78,0.25)]"
            aria-label={state.is_playing ? 'Pausar' : 'Tocar'}
          >
            {state.is_playing ? (
              <Pause className="w-6 h-6 fill-current" />
            ) : (
              <Play className="w-6 h-6 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={() => handleControl('next')}
            className="rounded-full p-2.5 text-[color:var(--text-secondary)] transition-colors hover:bg-white/[0.05] hover:text-[color:var(--text-primary)] active:scale-95"
            aria-label="Próxima faixa"
          >
            <SkipForward className="w-5 h-5 fill-current" />
          </button>
        </div>
      </div>

      <div className="absolute bottom-0 left-0 h-1 w-full overflow-hidden bg-white/10">
        <motion.div
          className="h-full w-full origin-left bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.6)]"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progressPercent / 100 }}
          transition={{ ease: "linear", duration: 1 }}
        />
      </div>
    </div>
  );
}
