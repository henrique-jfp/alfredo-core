import React from 'react';
import { type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

type Tone = 'brass' | 'success' | 'info' | 'warning' | 'danger';

const toneStyles: Record<Tone, { ring: string; bg: string; text: string; glow: string }> = {
  brass: {
    ring: 'border-brass-500/30',
    bg: 'bg-brass-500/10',
    text: 'text-brass-300',
    glow: 'shadow-[0_0_24px_rgba(212,162,78,0.18)]',
  },
  success: {
    ring: 'border-emerald-500/20',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    glow: 'shadow-[0_0_24px_rgba(74,222,128,0.12)]',
  },
  info: {
    ring: 'border-blue-500/20',
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    glow: 'shadow-[0_0_24px_rgba(96,165,250,0.12)]',
  },
  warning: {
    ring: 'border-amber-500/20',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    glow: 'shadow-[0_0_24px_rgba(245,158,11,0.12)]',
  },
  danger: {
    ring: 'border-rose-500/20',
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    glow: 'shadow-[0_0_24px_rgba(248,113,113,0.12)]',
  },
};

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  action,
  className,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex items-end justify-between gap-4', className)}>
      <div className="min-w-0">
        {eyebrow && <div className="alfredo-section-label mb-2">{eyebrow}</div>}
        <h2 className="text-[18px] md:text-[20px] font-semibold tracking-tight text-[color:var(--text-primary)]">{title}</h2>
        {subtitle && <p className="mt-1 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = 'brass',
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  const styles = toneStyles[tone];

  return (
    <div className={cn('alfredo-empty gap-4', className)}>
      <div className={cn('flex h-14 w-14 items-center justify-center rounded-2xl border', styles.ring, styles.bg, styles.text, styles.glow)}>
        <Icon className="h-7 w-7" />
      </div>
      <div className="max-w-md">
        <h3 className="text-[16px] font-semibold text-[color:var(--text-primary)]">{title}</h3>
        <p className="mt-2 text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = 'brass',
  sparkline,
  className,
}: {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  tone?: Tone;
  sparkline?: number[];
  className?: string;
}) {
  const styles = toneStyles[tone];
  const points = sparkline && sparkline.length > 1
    ? sparkline.map((point, index) => `${(index / (sparkline.length - 1)) * 100},${100 - point * 100}`).join(' ')
    : '';

  return (
    <div className={cn('alfredo-card p-4 md:p-5 fade-up', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className={cn('flex h-10 w-10 items-center justify-center rounded-xl border', styles.ring, styles.bg, styles.text)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="mt-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">{label}</div>
          <div className="mt-1 text-[28px] md:text-[32px] font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</div>
          {detail && <div className="mt-1 text-[12px] text-[color:var(--text-secondary)]">{detail}</div>}
        </div>
        {sparkline && sparkline.length > 1 && (
          <svg viewBox="0 0 100 40" className="h-12 w-24 shrink-0 overflow-visible">
            <defs>
              <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(212,162,78,0.6)" />
                <stop offset="100%" stopColor="rgba(212,162,78,0.05)" />
              </linearGradient>
            </defs>
            <polyline
              fill="none"
              stroke="rgba(212,162,78,0.85)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          </svg>
        )}
      </div>
    </div>
  );
}

export function StatusPulse({
  label,
  tone = 'success',
  icon: Icon,
  className,
}: {
  label: string;
  tone?: Tone;
  icon?: LucideIcon;
  className?: string;
}) {
  const styles = toneStyles[tone];

  return (
    <span className={cn('alfredo-pill', styles.bg, styles.text, styles.ring, className)}>
      <span className={cn('relative flex h-2 w-2', tone === 'success' && 'motion-safe:animate-pulse')}>
        <span className={cn('absolute inset-0 rounded-full opacity-60', styles.text, 'bg-current')} />
        <span className={cn('relative h-2 w-2 rounded-full bg-current', tone === 'success' && 'shadow-[0_0_8px_rgba(74,222,128,0.45)]')} />
      </span>
      {Icon && <Icon className="h-3.5 w-3.5" />}
      <span>{label}</span>
    </span>
  );
}

export function SkeletonBlock({
  className,
}: {
  className?: string;
}) {
  return <div className={cn('shimmer rounded-2xl bg-white/[0.04]', className)} />;
}
