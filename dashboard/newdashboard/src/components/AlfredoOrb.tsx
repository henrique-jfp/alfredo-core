import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../lib/utils';

export type AlfredoState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'executing' | 'error';

interface AlfredoOrbProps {
  state: AlfredoState;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  pulse?: boolean;
  className?: string;
  onClick?: () => void;
}

const stateConfig: Record<AlfredoState, {
  gradient: string;
  glow: string;
  ring: string;
  pulseColor: string;
  label: string;
}> = {
  idle: {
    gradient: 'from-brass-400/30 via-brass-500/20 to-brass-600/10',
    glow: 'shadow-[0_0_30px_rgba(212,162,78,0.15)]',
    ring: 'border-brass-500/20',
    pulseColor: 'rgba(212,162,78,0.08)',
    label: 'Ocioso',
  },
  listening: {
    gradient: 'from-emerald-400/40 via-emerald-500/30 to-emerald-600/15',
    glow: 'shadow-[0_0_40px_rgba(52,211,153,0.25)]',
    ring: 'border-emerald-400/30',
    pulseColor: 'rgba(52,211,153,0.12)',
    label: 'Ouvindo',
  },
  thinking: {
    gradient: 'from-brass-300/40 via-brass-400/35 to-brass-500/20',
    glow: 'shadow-[0_0_50px_rgba(212,162,78,0.3)]',
    ring: 'border-brass-300/30',
    pulseColor: 'rgba(212,162,78,0.15)',
    label: 'Processando',
  },
  speaking: {
    gradient: 'from-blue-400/40 via-blue-500/30 to-indigo-500/15',
    glow: 'shadow-[0_0_40px_rgba(96,165,250,0.25)]',
    ring: 'border-blue-400/30',
    pulseColor: 'rgba(96,165,250,0.12)',
    label: 'Falando',
  },
  executing: {
    gradient: 'from-amber-400/40 via-amber-500/30 to-amber-600/15',
    glow: 'shadow-[0_0_40px_rgba(245,158,11,0.25)]',
    ring: 'border-amber-400/30',
    pulseColor: 'rgba(245,158,11,0.12)',
    label: 'Executando',
  },
  error: {
    gradient: 'from-rose-400/40 via-rose-500/30 to-rose-600/15',
    glow: 'shadow-[0_0_40px_rgba(248,113,113,0.25)]',
    ring: 'border-rose-400/30',
    pulseColor: 'rgba(248,113,113,0.12)',
    label: 'Erro',
  },
};

const sizeMap = {
  sm: 'w-10 h-10',
  md: 'w-16 h-16',
  lg: 'w-24 h-24',
  xl: 'w-32 h-32',
};

const innerSizeMap = {
  sm: 'w-5 h-5',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
};

const strokeMap = {
  sm: 1.5,
  md: 2,
  lg: 2.5,
  xl: 3,
};

export function AlfredoOrb({ state, size = 'md', pulse = true, className, onClick }: AlfredoOrbProps) {
  const config = stateConfig[state];

  const orbContent = (
    <>
      {/* Outer glow rings */}
      <AnimatePresence>
        {(state === 'listening' || state === 'thinking' || state === 'speaking') && (
          <motion.div
            key="outer-ring"
            className={cn('absolute inset-0 rounded-full border', config.ring)}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: [0.3, 0.6, 0.3], scale: [1, 1.15, 1] }}
            exit={{ opacity: 0, scale: 1.2 }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
      </AnimatePresence>

      {/* Inner ring */}
      <motion.div
        className={cn(
          'absolute inset-1 rounded-full border',
          config.ring,
          'bg-gradient-to-br',
          config.gradient
        )}
        animate={state === 'thinking' ? { rotate: 360 } : {}}
        transition={state === 'thinking' ? { duration: 4, repeat: Infinity, ease: 'linear' } : {}}
        style={{
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
        }}
      />

      {/* Core */}
      <motion.div
        className={cn(
          'relative rounded-full bg-gradient-to-br',
          innerSizeMap[size],
          state === 'idle' ? 'from-brass-300/60 via-brass-400/40 to-brass-500/20' :
          state === 'listening' ? 'from-emerald-300/60 via-emerald-400/40 to-emerald-500/20' :
          state === 'thinking' ? 'from-brass-200/70 via-brass-300/50 to-brass-400/25' :
          state === 'speaking' ? 'from-blue-300/60 via-blue-400/40 to-indigo-400/20' :
          state === 'executing' ? 'from-amber-300/60 via-amber-400/40 to-amber-500/20' :
          'from-rose-300/60 via-rose-400/40 to-rose-500/20'
        )}
        animate={{
          scale: state === 'thinking' ? [1, 1.06, 1] : state === 'listening' ? [1, 1.03, 1] : 1,
        }}
        transition={{
          duration: state === 'thinking' ? 1.2 : 1.8,
          repeat: state !== 'idle' && state !== 'error' ? Infinity : 0,
          ease: 'easeInOut',
        }}
      >
        {/* Center dot */}
        <div className={cn(
          'absolute inset-[30%] rounded-full',
          state === 'idle' ? 'bg-brass-300/40' :
          state === 'listening' ? 'bg-emerald-300/50' :
          state === 'thinking' ? 'bg-brass-200/50' :
          state === 'speaking' ? 'bg-blue-300/50' :
          state === 'executing' ? 'bg-amber-300/50' :
          'bg-rose-300/50'
        )} />
      </motion.div>

      {/* State icon indicator */}
      <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap">
        <span className={cn(
          'text-[9px] font-semibold uppercase tracking-[0.15em] transition-colors duration-500',
          state === 'idle' && 'text-brass-400/50',
          state === 'listening' && 'text-emerald-400/70',
          state === 'thinking' && 'text-brass-300/70',
          state === 'speaking' && 'text-blue-400/70',
          state === 'executing' && 'text-amber-400/70',
          state === 'error' && 'text-rose-400/70',
        )}>
          {config.label}
        </span>
      </div>
    </>
  );

  const sharedMotionProps = {
    animate: {
      scale: pulse && (state === 'listening' || state === 'thinking' || state === 'speaking') ? [1, 1.03, 1] : 1,
    },
    transition: {
      duration: state === 'listening' ? 1.5 : 2,
      repeat: pulse && state !== 'idle' ? Infinity : 0,
      ease: 'easeInOut' as const,
    },
  };

  const sharedClassName = cn(
    'relative flex items-center justify-center rounded-full transition-all duration-700',
    sizeMap[size],
    config.glow,
    className,
  );

  // Sem onClick: elemento puramente visual — usar div com role="img" em vez de button
  if (!onClick) {
    return (
      <motion.div
        {...sharedMotionProps}
        className={sharedClassName}
        role="img"
        aria-label={`Alfredo — ${config.label}`}
      >
        {orbContent}
      </motion.div>
    );
  }

  return (
    <motion.button
      onClick={onClick}
      className={cn(sharedClassName, 'cursor-pointer')}
      {...sharedMotionProps}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      aria-label={`Alfredo — ${config.label}`}
    >
      {orbContent}
    </motion.button>
  );
}

