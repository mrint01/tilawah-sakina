import { useEffect, useRef, useState, type ReactNode } from 'react';
import { animate, motion } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight, ChevronLeft, ChevronRight, X, type LucideIcon } from 'lucide-react';
import { cn } from './cn';

export const EASE = [0.22, 1, 0.36, 1] as const;

const euro = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR' });
const euroShort = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', notation: 'compact', maximumFractionDigits: 1 });
export const money = (cents: number) => euro.format(cents / 100);
export const moneyShort = (cents: number) => euroShort.format(cents / 100);
export const int = new Intl.NumberFormat('en-GB');
const dt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
export const dateTime = (iso: string | null) => (iso ? dt.format(new Date(iso)) : '–');

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
export function ago(iso: string | null) {
  if (!iso) return '–';
  const s = (new Date(iso).getTime() - Date.now()) / 1000;
  const units: [Intl.RelativeTimeFormatUnit, number][] = [['year', 31536000], ['month', 2592000], ['day', 86400], ['hour', 3600], ['minute', 60]];
  for (const [u, n] of units) if (Math.abs(s) >= n) return rtf.format(Math.round(s / n), u);
  return 'just now';
}

/** Number that counts up to its value (formatted). */
export function AnimatedNumber({ value, format = (v) => int.format(Math.round(v)) }: { value: number; format?: (v: number) => string }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const c = animate(0, value, { duration: 1.2, ease: EASE, onUpdate: setShown });
    return () => c.stop();
  }, [value]);
  return <span className="num">{format(shown)}</span>;
}

export function PageHeader({ title, text, actions }: { title: string; text?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-1">
        <h1 className="text-xl font-bold tracking-tight">{title}</h1>
        {text && <p className="mt-0.5 text-sm text-ink-soft">{text}</p>}
      </div>
      {actions}
    </div>
  );
}

/** Card that rises in with a short delay (for staggered grids). */
export function Panel({ title, action, children, className, delay = 0 }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; delay?: number }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE, delay }}
      className={cn('rounded-xl border border-paper-line bg-paper p-4 shadow-sm', className)}
    >
      {(title || action) && (
        <div className="mb-3 flex items-center gap-3">
          {title && <h2 className="flex-1 text-sm font-semibold">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </motion.section>
  );
}

const TONES = {
  orange: 'bg-accent-light text-accent',
  green: 'bg-ok-light text-ok',
  blue: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  violet: 'bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  red: 'bg-danger-light text-danger',
  slate: 'bg-paper-alt text-ink-soft',
} as const;

export function Delta({ now, before, invert }: { now: number; before: number; invert?: boolean }) {
  if (!before && !now) return null;
  const pct = before ? ((now - before) / before) * 100 : 100;
  const up = pct >= 0;
  const good = invert ? !up : up;
  return (
    <span className={cn('inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs font-semibold', good ? 'bg-ok-light text-ok-dark' : 'bg-danger-light text-danger')}>
      {up ? <ArrowUpRight className="h-3 w-3" aria-hidden="true" /> : <ArrowDownRight className="h-3 w-3" aria-hidden="true" />}
      <span className="num">{Math.abs(pct).toFixed(0)}%</span>
    </span>
  );
}

export function KpiCard({ icon: Icon, label, value, format, tone = 'orange', footer, extra, delay = 0, onClick }: {
  icon: LucideIcon; label: string; value: number; format?: (v: number) => string; tone?: keyof typeof TONES; footer?: ReactNode; extra?: ReactNode; delay?: number; onClick?: () => void;
}) {
  const Tag = onClick ? motion.button : motion.div;
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE, delay }}
      whileHover={{ y: -3 }}
      className={cn('group relative flex flex-col overflow-hidden rounded-2xl border border-paper-line bg-paper p-5 text-start shadow-sm transition-shadow hover:shadow-lg', onClick && 'cursor-pointer')}
    >
      <div className="flex items-start gap-3">
        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', TONES[tone])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <p className="flex-1 pt-0.5 text-sm font-medium text-ink-soft">{label}</p>
      </div>
      <div className="mt-4 flex items-end justify-between gap-2">
        <p className="text-3xl font-bold tracking-tight">
          <AnimatedNumber value={value} format={format} />
        </p>
        {extra}
      </div>
      {footer && <div className="mt-2 flex items-center gap-2 text-xs text-ink-mute">{footer}</div>}
    </Tag>
  );
}

export function Badge({ children, tone = 'slate', className }: { children: ReactNode; tone?: keyof typeof TONES; className?: string }) {
  return <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold', TONES[tone], className)}>{children}</span>;
}

export function Empty({ icon: Icon, text }: { icon: LucideIcon; text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center text-ink-mute">
      <Icon className="h-8 w-8" aria-hidden="true" />
      <p>{text}</p>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-paper-alt', className)} />;
}

/** Pill tabs used as filters above lists. */
export function FilterTabs<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: { value: T; label: string; count?: number }[] }) {
  return (
    <div className="flex flex-wrap gap-1 rounded-xl bg-paper p-1 ring-1 ring-paper-line" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn('relative flex min-h-[40px] cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors', value === o.value ? 'text-white' : 'text-ink-soft hover:text-ink')}
        >
          {value === o.value && <motion.span layoutId={`tabs-${options.map((x) => x.value).join()}`} className="absolute inset-0 -z-0 rounded-lg bg-night dark:bg-accent" transition={{ type: 'spring', stiffness: 500, damping: 38 }} />}
          <span className="relative">{o.label}</span>
          {o.count !== undefined && <span className={cn('num relative rounded-full px-1.5 text-xs', value === o.value ? 'bg-white/20' : 'bg-paper-alt')}>{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

/**
 * One page of a list. Goes back to page 1 when `resetKey` changes (a new filter or search);
 * stays on the last page that still exists when the list gets shorter (e.g. after a delete).
 */
export function usePaged<T>(items: T[] | undefined, resetKey: unknown = null, size = 10) {
  const [page, setPage] = useState(0);
  const [key, setKey] = useState(resetKey);
  if (key !== resetKey) {
    setKey(resetKey);
    setPage(0);
  }
  const total = items?.length ?? 0;
  const pages = Math.max(1, Math.ceil(total / size));
  const current = Math.min(page, pages - 1);
  return { items: items?.slice(current * size, (current + 1) * size), page: current, pages, total, size, setPage };
}

/** "11–20 of 37" + Previous / page numbers / Next. Hidden for an empty list. */
export function Pager({ paged, className }: { paged: ReturnType<typeof usePaged<unknown>>; className?: string }) {
  const { page, pages, total, size, setPage } = paged;
  if (!total) return null;
  // Up to 5 numbers around the current page.
  const start = Math.max(0, Math.min(page - 2, pages - 5));
  const numbers = Array.from({ length: Math.min(5, pages) }, (_, i) => start + i);
  const btn = 'flex h-9 min-w-9 cursor-pointer items-center justify-center rounded-lg px-2 text-sm font-medium disabled:cursor-default disabled:opacity-40';
  return (
    <nav aria-label="Pages" className={cn('flex flex-wrap items-center gap-2 text-sm', className)}>
      <span className="text-ink-mute">
        <span className="num">{page * size + 1}–{Math.min(total, (page + 1) * size)}</span> of <span className="num">{total}</span>
      </span>
      <span className="flex-1" />
      {pages > 1 && (
        <div className="flex items-center gap-1">
          <button type="button" className={cn(btn, 'text-ink-soft hover:bg-paper-alt')} disabled={page === 0} onClick={() => setPage(page - 1)} aria-label="Previous page">
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          {numbers.map((n) => (
            <button key={n} type="button" aria-current={n === page ? 'page' : undefined} onClick={() => setPage(n)}
              className={cn(btn, 'num', n === page ? 'bg-accent text-white' : 'text-ink-soft hover:bg-paper-alt')}>
              {n + 1}
            </button>
          ))}
          <button type="button" className={cn(btn, 'text-ink-soft hover:bg-paper-alt')} disabled={page >= pages - 1} onClick={() => setPage(page + 1)} aria-label="Next page">
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      )}
    </nav>
  );
}

/**
 * Popup (native <dialog>: focus trap, Esc, backdrop). Open while `open` is true; a click on the
 * backdrop or Esc calls onClose. `tone="danger"` gives the red icon for deletes.
 */
export function Modal({ open, onClose, title, text, icon: Icon, tone = 'accent', children, wide }: {
  open: boolean; onClose: () => void; title: ReactNode; text?: ReactNode; icon?: LucideIcon; tone?: 'accent' | 'danger'; children: ReactNode; wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    else if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} onClick={(e) => e.target === e.currentTarget && onClose()} aria-label={typeof title === 'string' ? title : undefined}
      className={cn('rounded-2xl border border-paper-line bg-paper p-0 text-ink shadow-2xl backdrop:bg-black/70', wide ? 'w-[min(94vw,560px)]' : 'w-[min(92vw,420px)]')}>
      {open && (
        <div className="relative flex flex-col gap-4 p-6">
          <button type="button" onClick={onClose} aria-label="Close" className="absolute end-3 top-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-ink-mute hover:bg-paper-alt hover:text-ink">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
          <div className="flex items-start gap-3 pe-8">
            {Icon && (
              <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', tone === 'danger' ? 'bg-danger-light text-danger' : 'bg-accent-light text-accent')}>
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
            )}
            <div className="min-w-0">
              <h2 className="text-lg font-bold">{title}</h2>
              {text && <p className="mt-0.5 text-sm text-ink-soft">{text}</p>}
            </div>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

/** Small bordered input/select styles shared by the console's forms and filters. */
export const INPUT = 'h-10 w-full rounded-lg border border-paper-line bg-paper px-3 text-sm text-ink placeholder:text-ink-mute focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30';
export const SELECT = 'h-9 cursor-pointer rounded-lg border border-paper-line bg-paper px-2 text-sm text-ink focus:border-accent focus:outline-none';

/** Label + control + hint/error, for popup forms. */
export function FormRow({ label, hint, error, children }: { label: string; hint?: ReactNode; error?: ReactNode; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-ink-mute">{label}</span>
      {children}
      {error ? <span className="text-xs text-danger">{error}</span> : hint ? <span className="text-xs text-ink-mute">{hint}</span> : null}
    </label>
  );
}
