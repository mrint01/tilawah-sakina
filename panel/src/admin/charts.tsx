import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { motion } from 'framer-motion';

// Hand-drawn SVG charts. One series at a time, in the brand chart colour (rgb(var(--chart))).

function useWidth(ref: React.RefObject<HTMLDivElement>) {
  const [w, setW] = useState(600);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => e && setW(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}
const EASE = [0.22, 1, 0.36, 1] as const;

function niceRange(lo: number, hi: number) {
  const span = Math.max(1, hi - lo);
  const p = 10 ** Math.floor(Math.log10(span));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * p).find((s) => span / s <= 4) ?? 10 * p;
  return { min: Math.floor(lo / step) * step, max: Math.max(Math.ceil(hi / step) * step, Math.floor(lo / step) * step + step), step };
}

function Tooltip({ x, children, width }: { x: number; children: ReactNode; width: number }) {
  const left = x / width > 0.6;
  return (
    <div className="pointer-events-none absolute top-1 z-10 min-w-[120px] rounded-xl bg-ink px-3 py-2 text-xs text-paper shadow-xl"
      style={left ? { right: `${100 - (x / width) * 100 + 2}%` } : { left: `${(x / width) * 100 + 2}%` }}>
      {children}
    </div>
  );
}

/**
 * Area + line over days with a crosshair tooltip. Points with value null are gaps (no data that day).
 * zero: start the y axis at 0 (counts per day); off for a running total like followers.
 */
export function AreaChart({ data, height = 260, format = (v: number) => String(v), zero = true, label }: {
  data: { label: string; value: number | null }[]; height?: number; format?: (v: number) => string; zero?: boolean; label: string;
}) {
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = useWidth(ref);
  const H = height;
  const pad = { t: 14, b: 26, l: 44, r: 10 };
  const vals = data.map((d) => d.value).filter((v): v is number => v != null);
  const { min, max, step } = niceRange(zero ? 0 : Math.min(...vals, Infinity) === Infinity ? 0 : Math.min(...vals), Math.max(0, ...vals));
  const x = (i: number) => pad.l + (data.length < 2 ? (W - pad.l - pad.r) / 2 : (i / (data.length - 1)) * (W - pad.l - pad.r));
  const y = (v: number) => pad.t + (1 - (v - min) / (max - min)) * (H - pad.t - pad.b);
  // line segments between consecutive days that have data
  let line = '';
  let prev = false;
  data.forEach((d, i) => {
    if (d.value == null) { prev = false; return; }
    line += `${prev ? 'L' : 'M'}${x(i).toFixed(1)},${y(d.value).toFixed(1)} `;
    prev = true;
  });
  const idx = data.map((d, i) => (d.value == null ? -1 : i)).filter((i) => i >= 0);
  const area = idx.length > 1 && idx.length === data.length ? `${line} L${x(data.length - 1)},${y(min)} L${x(0)},${y(min)} Z` : '';
  const ticks: number[] = [];
  for (let t = min; t <= max + 1e-9; t += step) ticks.push(t);
  const xLabels = data.length > 2 ? [0, Math.floor((data.length - 1) / 2), data.length - 1] : data.map((_, i) => i);

  const onMove = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, i)));
  };
  const h = hover !== null ? data[hover] : null;

  return (
    <div ref={ref} className="relative touch-pan-y" onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`${label} per day`}>
        <defs>
          <linearGradient id={`${id}-fill`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--chart))" stopOpacity="0.26" />
            <stop offset="100%" stopColor="rgb(var(--chart))" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="stroke-paper-line" strokeDasharray={t !== min ? '3 4' : undefined} />
            <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" className="fill-ink-mute text-[12px]">{format(t)}</text>
          </g>
        ))}
        {xLabels.map((i) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor={data.length < 2 ? 'middle' : i === 0 ? 'start' : i === data.length - 1 ? 'end' : 'middle'} className="fill-ink-mute text-[12px]">{data[i]?.label}</text>
        ))}
        {area && <motion.path key={`a${data.length}${label}`} d={area} fill={`url(#${id}-fill)`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.3 }} />}
        <motion.path key={`l${data.length}${label}`} d={line} fill="none" stroke="rgb(var(--chart))" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, ease: EASE }} />
        {idx.length <= 3 && idx.map((i) => <circle key={i} cx={x(i)} cy={y(data[i].value!)} r={5} fill="rgb(var(--chart))" className="stroke-paper" strokeWidth={2} />)}
        {h && (
          <g>
            <line x1={x(hover!)} x2={x(hover!)} y1={pad.t} y2={y(min)} className="stroke-ink-mute" strokeDasharray="3 3" />
            {h.value != null && <circle cx={x(hover!)} cy={y(h.value)} r={5} fill="rgb(var(--chart))" className="stroke-paper" strokeWidth={2} />}
          </g>
        )}
      </svg>
      {h && (
        <Tooltip x={x(hover!)} width={W}>
          <p className="opacity-70">{h.label}</p>
          <p className="num text-sm font-bold">{h.value == null ? 'No data' : `${format(h.value)} ${label.toLowerCase()}`}</p>
        </Tooltip>
      )}
    </div>
  );
}
