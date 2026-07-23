import React, { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
  maxWidth?: string;
}

export function Modal({ open, onClose, title, children, className, maxWidth = 'max-w-lg' }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Focus trapping
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    if (e.key === 'Tab' && dialogRef.current) {
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
  }, [onClose]);

  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';

      // Focus first focusable element after render
      requestAnimationFrame(() => {
        if (dialogRef.current) {
          const firstFocusable = dialogRef.current.querySelector<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          firstFocusable?.focus();
        }
      });
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      if (!open && previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Diálogo'}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        className={cn(
          'alfredo-card relative w-full max-h-[85vh] flex flex-col overflow-hidden shadow-[0_24px_48px_rgba(0,0,0,0.6)]',
          maxWidth,
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-white/5 px-6 py-5">
            <h2 className="text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-full p-2 text-[color:var(--text-tertiary)] hover:bg-white/5 hover:text-[color:var(--text-primary)] transition-colors"
              aria-label="Fechar diálogo"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
