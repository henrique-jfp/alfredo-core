import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { cn } from '../lib/utils';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: number;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  toast: (type: ToastType, title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export const useToast = () => useContext(ToastContext);

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
  error: <AlertCircle className="w-5 h-5 text-rose-400" />,
  info: <Info className="w-5 h-5 text-blue-400" />,
  warning: <AlertTriangle className="w-5 h-5 text-amber-400" />,
};

const borderColors: Record<ToastType, string> = {
  success: 'border-emerald-500/20',
  error: 'border-rose-500/20',
  info: 'border-blue-500/20',
  warning: 'border-amber-500/20',
};

const bgColors: Record<ToastType, string> = {
  success: 'bg-emerald-500/[0.06]',
  error: 'bg-rose-500/[0.06]',
  info: 'bg-blue-500/[0.06]',
  warning: 'bg-amber-500/[0.06]',
};

let toastId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, title: string, message?: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed bottom-28 right-4 z-[100] flex flex-col gap-2 pointer-events-none md:bottom-20">
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 80, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              className={cn(
                'pointer-events-auto flex items-start gap-3 rounded-2xl border p-4 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl min-w-[280px] max-w-[380px]',
                borderColors[t.type],
                bgColors[t.type],
                'bg-[color:var(--bg-surface)]/95'
              )}
            >
              <div className="shrink-0 mt-0.5">{icons[t.type]}</div>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-[color:var(--text-primary)]">{t.title}</p>
                {t.message && (
                  <p className="mt-1 text-[12px] text-[color:var(--text-secondary)]">{t.message}</p>
                )}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 rounded-full p-1 text-[color:var(--text-tertiary)] hover:bg-white/5 hover:text-[color:var(--text-primary)] transition-colors"
                aria-label="Fechar notificação"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
