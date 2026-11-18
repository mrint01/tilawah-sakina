import { useEffect, useState, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import {
  Activity, AtSign, BellOff, BellRing, Clapperboard, ChevronLeft, ChevronRight, Gauge, Inbox, ListOrdered, LogOut, Menu, Moon,
  Send, Settings, Sun, X, type LucideIcon,
} from 'lucide-react';
import { cn } from './cn';

/**
 * The admin console shell (YourTurn / ProgressPal design):
 * - sidebar 240px (w-60), collapsible to a 60px icon rail (remembered in localStorage)
 * - header: logo + app name + "CONSOLE" under it; collapse chevron on the right
 * - nav groups with small uppercase titles; 15px icons, strokeWidth 1.75; active = orange tint + left rail
 * - count badges (feedback, errors …); Privacy · Terms · Imprint at the bottom
 * - top bar 48px, same colour as the sidebar: [Alarm] [theme] [admin NAME → Settings] [Sign out] on the right
 * - phones: sidebar becomes a slide-in drawer, menu button in the top bar
 * - content full width on bg-paper-alt, padding p-4 / sm:p-5 / lg:p-6
 * - 14px root + Vercel-like text sizes while mounted (theme.css, data-admin-font)
 *
 * Adapt: NAV_GROUPS, APP_NAME, Logo, BASE, badges, links, and the auth/alarm props.
 */

const APP_NAME = 'Reel Studio';
/** The Instagram page this console manages. Becomes a page switcher once there are several. */
const PAGE_HANDLE = 'tilawah.sakina';
const BASE = '';
const MINI_KEY = 'admin.sidebar';

interface NavItem { to: string; label: string; icon: LucideIcon; end?: boolean; badge?: string }
// Same groups and icons in every console, so they all read the same way. Drop what the app doesn't have.
const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  { title: 'Overview', items: [
    { to: '/', label: 'Overview', icon: Gauge, end: true },
  ] },
  { title: 'Content', items: [
    { to: '/review', label: 'Review', icon: Inbox, badge: 'review' },
    { to: '/queue', label: 'Up next', icon: ListOrdered, badge: 'queue' },
    { to: '/posted', label: 'Posted', icon: Send },
  ] },
  { title: 'Health', items: [
    { to: '/runs', label: 'Workflow runs', icon: Activity, badge: 'failed' },
  ] },
  { title: 'System', items: [
    { to: '/settings', label: 'Settings', icon: Settings },
  ] },
];

/** Logo mark: a clapperboard on the green tile (Reel Studio works for any number of pages). */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span className={cn('flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white', className)} aria-hidden="true">
      <Clapperboard className="h-[60%] w-[60%]" strokeWidth={2} />
    </span>
  );
}

/** Light/dark switch on <html class="dark">; shows the mode you get when you press it. */
function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle('dark', next);
    try { localStorage.setItem('theme', next ? 'dark' : 'light'); } catch { /* convenience */ }
    setDark(next);
  };
  const label = dark ? 'Light mode' : 'Dark mode';
  return (
    <button type="button" onClick={toggle} aria-label={label} title={label}
      className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-paper-line text-ink-soft hover:bg-paper-alt">
      {dark ? <Sun className="h-3.5 w-3.5" aria-hidden="true" /> : <Moon className="h-3.5 w-3.5" aria-hidden="true" />}
    </button>
  );
}

const readMini = () => {
  try { return localStorage.getItem(MINI_KEY) === 'mini'; } catch { return false; }
};

export function AdminLayout({ children, email, name, onSignOut, badges = {}, alarm }: {
  children: ReactNode;
  email?: string;
  /** The admin's own name (Settings → Profile). Shown top right instead of the email; the email until it is set. */
  name?: string | null;
  onSignOut: () => void;
  /** Counts shown next to nav items, by NavItem.badge. */
  badges?: Record<string, number>;
  /** Optional error alarm (see ErrorWatch.tsx). */
  alarm?: { armed: boolean; setArmed: (on: boolean) => void };
}) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);

  // Denser console: 14px root, with the text-size rules from theme.css.
  useEffect(() => {
    const html = document.documentElement;
    const before = html.style.fontSize;
    html.style.fontSize = '14px';
    html.dataset.adminFont = '2';
    return () => {
      html.style.fontSize = before;
      delete html.dataset.adminFont;
    };
  }, []);

  const [mini, setMiniState] = useState(readMini);
  const setMini = (v: boolean) => {
    setMiniState(v);
    try { localStorage.setItem(MINI_KEY, v ? 'mini' : 'full'); } catch { /* convenience */ }
  };

  /** `compact` = icon rail (desktop, collapsed). */
  const sidebar = (compact: boolean) => (
    <div className="flex h-full flex-col">
      <div className={cn('flex shrink-0 items-center border-b border-paper-line py-3.5', compact ? 'justify-center px-2' : 'gap-2.5 px-4')}>
        {compact ? (
          // Closed: the whole header is the way back — logo + arrow in one bordered button, tinted on hover.
          <button type="button" onClick={() => setMini(false)} aria-label="Expand sidebar" title="Expand sidebar"
            className="flex w-full cursor-pointer items-center justify-center gap-1 rounded-md border border-paper-line py-1.5 text-accent transition-colors duration-150 hover:border-accent hover:bg-accent/10">
            <LogoMark className="!h-[18px] !w-[18px] !rounded" />
            <ChevronRight className="h-3.5 w-3.5" strokeWidth={2.25} aria-hidden="true" />
          </button>
        ) : (
          <>
            <LogoMark className="shrink-0" />
            <span className="min-w-0 flex-1 leading-tight">
              <span className="block truncate text-[13px] font-semibold tracking-tight text-ink">{APP_NAME}</span>
              <span className="block text-[10.5px] uppercase tracking-[0.13em] text-ink-mute">Console</span>
            </span>
            <button type="button" onClick={() => setMini(true)} aria-label="Collapse sidebar" title="Collapse sidebar"
              className="hidden h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-mute hover:bg-paper-alt hover:text-ink lg:flex">
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </>
        )}
      </div>
      <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Admin">
        {NAV_GROUPS.map((g) => (
          <div key={g.title} className="mb-4 last:mb-0">
            {compact ? <div className="mx-3 mb-1.5 border-t border-paper-line" aria-hidden="true" /> : (
              <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-ink-mute">{g.title}</p>
            )}
            {g.items.map((n) => {
              const count = n.badge ? badges[n.badge] ?? 0 : 0;
              return (
                <NavLink key={n.to} to={BASE + n.to || '/'} end={n.end}
                  title={compact ? (count ? `${n.label} (${count})` : n.label) : undefined}
                  className={({ isActive }) => cn('group relative flex cursor-pointer items-center rounded-md py-[7px] text-[13px] transition-colors duration-150',
                    compact ? 'justify-center px-0' : 'gap-2.5 px-3',
                    isActive ? 'bg-accent/10 font-medium text-accent' : 'text-ink-soft hover:bg-paper-alt hover:text-ink')}>
                  {({ isActive }) => (
                    <>
                      {/* The active rail: position, not just colour. No animated highlight (it jumps). */}
                      <span className={cn('absolute start-0 top-1/2 h-4 w-[2.5px] -translate-y-1/2 rounded-e', isActive ? 'bg-accent' : 'bg-transparent')} aria-hidden="true" />
                      <n.icon className="h-[15px] w-[15px] shrink-0" strokeWidth={1.75} aria-hidden="true" />
                      {compact ? (
                        <>
                          <span className="sr-only">{n.label}</span>
                          {count > 0 && <span className="num absolute end-1 top-0.5 min-w-[1rem] rounded-full bg-accent px-1 text-center text-[9px] font-bold leading-4 text-white">{count}</span>}
                        </>
                      ) : (
                        <>
                          <span className="flex-1 truncate">{n.label}</span>
                          {count > 0 && <span className="num rounded-full bg-accent/15 px-1.5 text-[11px] font-semibold leading-[18px] text-accent">{count}</span>}
                        </>
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
      {!compact && (
        <p className="flex shrink-0 flex-wrap gap-x-1.5 border-t border-paper-line px-4 py-2.5 text-[10.5px] text-ink-mute">
          <a href="https://www.instagram.com/tilawah.sakina/" target="_blank" rel="noreferrer" className="hover:text-ink-soft">Instagram</a>·
          <a href="https://github.com/mrint01/tilawah-sakina" target="_blank" rel="noreferrer" className="hover:text-ink-soft">GitHub</a>
        </p>
      )}
    </div>
  );

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen bg-paper-alt">
        <aside className={cn('fixed inset-y-0 start-0 z-30 hidden border-e border-paper-line bg-paper transition-[width] duration-200 lg:block', mini ? 'w-[60px]' : 'w-60')}>{sidebar(mini)}</aside>
        <AnimatePresence>
          {open && (
            <>
              <motion.div className="fixed inset-0 z-40 bg-black/50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} />
              <motion.aside className="fixed inset-y-0 start-0 z-50 w-64 border-e border-paper-line bg-paper lg:hidden"
                initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'spring', stiffness: 400, damping: 40 }}>
                <button type="button" onClick={() => setOpen(false)} aria-label="Close menu"
                  className="absolute end-2 top-2.5 flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg text-ink-soft hover:bg-paper-alt">
                  <X className="h-5 w-5" />
                </button>
                {sidebar(false)}
              </motion.aside>
            </>
          )}
        </AnimatePresence>
        <div className={cn('transition-[margin] duration-200', mini ? 'lg:ms-[60px]' : 'lg:ms-60')}>
          {/* Top bar: same solid colour as the sidebar. */}
          <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b border-paper-line bg-paper px-3 sm:px-5">
            <button type="button" onClick={() => setOpen(true)} aria-label="Open menu"
              className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md hover:bg-paper-alt lg:hidden">
              <Menu className="h-5 w-5" />
            </button>
            <span className="lg:hidden"><LogoMark /></span>
            <a href={`https://www.instagram.com/${PAGE_HANDLE}/`} target="_blank" rel="noreferrer" title="The Instagram page this console manages"
              className="flex h-8 min-w-0 items-center gap-1 rounded-md border border-paper-line px-2.5 text-xs font-medium text-ink-soft hover:border-accent hover:text-accent">
              <AtSign className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> <span className="truncate">{PAGE_HANDLE}</span>
            </a>
            <span className="flex-1" />
            {alarm && (
              <button type="button" onClick={() => alarm.setArmed(!alarm.armed)} aria-pressed={alarm.armed}
                title={alarm.armed ? 'Error alarm on — click to mute' : 'Error alarm off — click to turn on'}
                className={cn('flex h-8 cursor-pointer items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors',
                  alarm.armed ? 'border-ok/60 text-ok hover:bg-ok-light' : 'border-paper-line text-ink-soft hover:bg-paper-alt')}>
                {alarm.armed ? <BellRing className="h-3.5 w-3.5" aria-hidden="true" /> : <BellOff className="h-3.5 w-3.5" aria-hidden="true" />}
                <span className="hidden sm:inline">{alarm.armed ? 'Alarm on' : 'Alarm off'}</span>
                {alarm.armed && <span className="h-1.5 w-1.5 rounded-full bg-ok" aria-hidden="true" />}
              </button>
            )}
            <ThemeToggle />
            {/* The admin's NAME, not the email (email only as tooltip / fallback); links to Settings. */}
            {(name || email) && (
              <NavLink to={`${BASE}/settings`} title={email} className="hidden max-w-[16rem] truncate rounded-md px-1.5 py-1 text-xs font-medium text-ink-soft hover:bg-paper-alt hover:text-ink md:inline">
                {name || email}
              </NavLink>
            )}
            <button type="button" onClick={onSignOut} title="Sign out"
              className="flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-paper-line px-2.5 text-xs font-medium text-ink-soft hover:bg-paper-alt">
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" /> <span className="hidden sm:inline">Sign out</span>
            </button>
          </header>
          {/* Full width, no max-width container. */}
          <main className="p-4 sm:p-5 lg:p-6">{children}</main>
        </div>
      </div>
    </MotionConfig>
  );
}
