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
        // Brand - Copper tones (keep)
        copper: {
          DEFAULT: '#B87333',
          glow: '#CD7F32',
          dim: '#7a5a2a',
          light: '#d4956b',
        },
        // Backgrounds - Warm browns (replaces terminal blacks)
        bg: {
          dark: '#1a1410',
          card: '#241c16',
          surface: '#2e241c',
        },
        // Pixel semantic colors (16-bit game palette)
        pixel: {
          green: '#6abe30',   // Success, rewards
          red: '#ac3232',     // Errors, negative
          gold: '#fbf236',    // Highlights, special
          blue: '#5b6ee1',    // Info, links
        },
        // Neutrals
        border: '#3d352d',
        text: {
          primary: '#f5f5f5',
          secondary: '#a08060',
          muted: '#6b5a4a',
        },
        // Legacy terminal colors (for gradual migration)
        terminal: {
          bg: '#1a1410',
          card: '#241c16',
          border: '#3d352d',
          green: '#6abe30',
          amber: '#fbf236',
          red: '#ac3232',
          text: '#a08060',
          muted: '#6b5a4a',
        },
      },
      fontFamily: {
        mono: [
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
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        blink: 'blink 1s step-end infinite',
        'float': 'float 3s ease-in-out infinite',
        'coin-collect': 'coinCollect 0.8s ease-out forwards',
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
      },
      boxShadow: {
        'copper-glow': '0 0 10px rgba(184, 115, 51, 0.3)',
        'copper-strong': '0 0 20px rgba(184, 115, 51, 0.5)',
        'terminal-inset': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
      },
      backgroundImage: {
        // Warm brown gradients (replaces terminal blacks)
        'cave-gradient':
          'linear-gradient(180deg, #1a1410 0%, #241c16 100%)',
        'mobile-gradient': 'linear-gradient(180deg, #1a1410 0%, #0f0c09 100%)',
        // Legacy alias
        'terminal-gradient':
          'linear-gradient(180deg, #1a1410 0%, #241c16 100%)',
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
