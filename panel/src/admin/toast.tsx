import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, XCircle } from 'lucide-react';
import { cn } from './cn';

type Tone = 'success' | 'error';
const Ctx = createContext<{ show: (text: string, opts?: { tone?: Tone }) => void }>({ show: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<{ id: number; text: string; tone: Tone }[]>([]);
  const show = useCallback((text: string, opts?: { tone?: Tone }) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, text, tone: opts?.tone ?? 'success' }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500);
  }, []);
  return (
    <Ctx.Provider value={{ show }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-4" role="status" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
              className={cn('pointer-events-auto flex max-w-md items-center gap-2 rounded-xl border bg-paper px-4 py-2.5 text-sm font-medium shadow-lg',
                t.tone === 'error' ? 'border-danger/40 text-danger' : 'border-ok/40 text-ok')}>
              {t.tone === 'error' ? <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />}
              <span className="text-ink">{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);
