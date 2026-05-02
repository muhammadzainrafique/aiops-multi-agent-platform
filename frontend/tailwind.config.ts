import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['var(--font-sans)',    'sans-serif'],
        mono:    ['var(--font-mono)',    'monospace'],
        display: ['var(--font-display)', 'sans-serif'],
      },
      colors: {
        ink:    { DEFAULT: '#070d1a', 2: '#0d1729', 3: '#152236', 4: '#1e3050' },
        slate:  { DEFAULT: '#374a6b', 2: '#4a5f84', 3: '#6b7fa0', 4: '#8f9fc0' },
        dim:    { DEFAULT: '#b8c4d8', 2: '#d0d8e8', 3: '#e8edf5' },
        blue:   { DEFAULT: '#2563eb', soft: '#dbeafe', mid: '#93c5fd', glow: '#1d4ed8' },
        green:  { DEFAULT: '#059669', soft: '#d1fae5', mid: '#6ee7b7' },
        amber:  { DEFAULT: '#d97706', soft: '#fef3c7', mid: '#fcd34d' },
        red:    { DEFAULT: '#dc2626', soft: '#fee2e2', mid: '#fca5a5' },
        purple: { DEFAULT: '#7c3aed', soft: '#ede9fe', mid: '#c4b5fd' },
        teal:   { DEFAULT: '#0891b2', soft: '#cffafe', mid: '#67e8f9' },
      },
      animation: {
        'fade-up':    'fadeUp .4s cubic-bezier(.22,1,.36,1) both',
        'fade-in':    'fadeIn .3s ease both',
        'slide-in':   'slideIn .35s cubic-bezier(.22,1,.36,1) both',
        'pulse-dot':  'pulseDot 2s ease-in-out infinite',
        'flow':       'flow 1.8s linear infinite',
        'shimmer':    'shimmer 1.4s infinite',
        'spin-slow':  'spin 3s linear infinite',
        'bounce-msg': 'bounceMsg 1.2s ease infinite',
      },
      keyframes: {
        fadeUp:    { from: { opacity: '0', transform: 'translateY(16px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        fadeIn:    { from: { opacity: '0' }, to: { opacity: '1' } },
        slideIn:   { from: { opacity: '0', transform: 'translateX(-12px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        pulseDot:  { '0%,100%': { transform: 'scale(1)', opacity: '1' }, '50%': { transform: 'scale(1.5)', opacity: '.5' } },
        flow:      { from: { left: '-100%' }, to: { left: '100%' } },
        shimmer:   { from: { backgroundPosition: '-400px 0' }, to: { backgroundPosition: '400px 0' } },
        bounceMsg: { '0%,60%,100%': { transform: 'translateY(0)' }, '30%': { transform: 'translateY(-6px)' } },
      },
      boxShadow: {
        card:  '0 1px 3px rgba(7,13,26,.08), 0 2px 10px rgba(7,13,26,.05)',
        card2: '0 4px 20px rgba(7,13,26,.12), 0 2px 8px rgba(7,13,26,.06)',
        card3: '0 8px 40px rgba(7,13,26,.16)',
        glow:  '0 0 24px rgba(37,99,235,.25)',
        'glow-green':  '0 0 20px rgba(5,150,105,.2)',
        'glow-red':    '0 0 20px rgba(220,38,38,.2)',
        'glow-amber':  '0 0 20px rgba(217,119,6,.2)',
      },
    },
  },
  plugins: [],
}

export default config
