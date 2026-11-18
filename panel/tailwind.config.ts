import type { Config } from 'tailwindcss';

const c = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: c('ink'), soft: c('ink-soft'), mute: c('ink-mute') },
        paper: { DEFAULT: c('paper'), alt: c('paper-alt'), line: c('paper-line') },
        accent: { DEFAULT: c('accent'), dark: c('accent-dark'), light: c('accent-light') },
        ok: { DEFAULT: c('ok'), dark: c('ok-dark'), light: c('ok-light') },
        danger: { DEFAULT: c('danger'), light: c('danger-light') },
        chart: c('chart'),
        gold: c('gold'),
      },
      fontFamily: { sans: ['"IBM Plex Sans"', 'Amiri', 'system-ui', 'sans-serif'], arabic: ['Amiri', 'serif'] },
    },
  },
} satisfies Config;
