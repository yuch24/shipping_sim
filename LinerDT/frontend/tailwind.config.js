/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        marine: {
          50: '#eef6ff',
          100: '#d9ebff',
          200: '#badbff',
          300: '#7cc4ff',
          400: '#36aaff',
          500: '#0057b7',
          600: '#004494',
          700: '#003374',
          800: '#002455',
          900: '#001f3f',
        },
        carbon: {
          low: '#4ade80',
          mid: '#facc15',
          high: '#ef4444',
        },
        surface: {
          glass: 'rgba(255,255,255,0.08)',
          panel: 'rgba(10,25,47,0.85)',
          hover: 'rgba(255,255,255,0.12)',
        },
        ship: {
          idle: '#9CA3AF',
          sailing: '#3B82F6',
          arriving: '#F59E0B',
          berthing: '#10B981',
          waiting: '#EF4444',
        },
      },
      borderRadius: {
        'panel': '12px',
        'widget': '8px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(0,87,183,0.3)',
        'glow-sm': '0 0 10px rgba(0,87,183,0.2)',
        'inner-glow': 'inset 0 0 20px rgba(0,87,183,0.1)',
      },
      backdropBlur: {
        'panel': '16px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
