import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Monochrome palette
        accent: '#ffffff',
        // Backgrounds - Pure darks
        bg: {
          dark: '#0a0a0a',
          card: '#111111',
          surface: '#1a1a1a',
        },
        // Neutrals
        border: '#333333',
        text: {
          primary: '#e5e5e5',
          secondary: '#a0a0a0',
          muted: '#666666',
        },
        // Gray scale for UI elements
        gray: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
        // Legacy terminal colors (mapped to monochrome)
        terminal: {
          bg: '#0a0a0a',
          card: '#111111',
          border: '#333333',
          green: '#e5e5e5',
          amber: '#ffffff',
          red: '#a0a0a0',
          text: '#a0a0a0',
          muted: '#666666',
        },
      },
      fontFamily: {
        mono: [
          'VT323',
          'IBM Plex Mono',
          'Fira Code',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      fontSize: {
        xxs: ['0.625rem', { lineHeight: '0.875rem' }],
        // Semantic typography scale
        'display': ['3.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'display-sm': ['2.5rem', { lineHeight: '1.15', letterSpacing: '-0.01em' }],
        'heading-1': ['2rem', { lineHeight: '1.2' }],
        'heading-2': ['1.5rem', { lineHeight: '1.3' }],
        'heading-3': ['1.125rem', { lineHeight: '1.4' }],
        'body': ['1rem', { lineHeight: '1.6' }],
        'body-sm': ['0.875rem', { lineHeight: '1.5' }],
        'caption': ['0.75rem', { lineHeight: '1.4' }],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        blink: 'blink 1s step-end infinite',
        'float': 'float 3s ease-in-out infinite',
        'coin-collect': 'coinCollect 0.8s ease-out forwards',
        // Pixel miner pickaxe animation (8 frames at 56px each = 448px total)
        'mine': 'mine 0.8s steps(8) infinite',
        // Entrance animations (use 'both' to apply initial state during delay)
        'fade-slide-in': 'fadeSlideIn 0.4s ease-out both',
        'fade-in': 'fadeIn 0.5s ease-out both',
        'count-up': 'countUp 0.6s ease-out both',
        // Shimmer for skeletons
        'shimmer': 'shimmer 1.5s infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        coinCollect: {
          '0%': { transform: 'scale(1) translateY(0)', opacity: '1' },
          '50%': { transform: 'scale(1.2) translateY(-20px)', opacity: '1' },
          '100%': { transform: 'scale(0.5) translateY(-60px)', opacity: '0' },
        },
        // Sprite sheet animation - moves through 8 horizontal frames
        mine: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '-448px 0' },
        },
        // Entrance animations
        fadeSlideIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        countUp: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      boxShadow: {
        'white-glow': '0 0 10px rgba(255, 255, 255, 0.3)',
        'white-strong': '0 0 20px rgba(255, 255, 255, 0.5)',
        'terminal-inset': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.5)',
      },
      backgroundImage: {
        // Monochrome gradients
        'cave-gradient':
          'linear-gradient(180deg, #0a0a0a 0%, #111111 100%)',
        'mobile-gradient': 'linear-gradient(180deg, #0a0a0a 0%, #050505 100%)',
        // Legacy alias
        'terminal-gradient':
          'linear-gradient(180deg, #0a0a0a 0%, #111111 100%)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
    },
  },
  plugins: [],
};

export default config;
