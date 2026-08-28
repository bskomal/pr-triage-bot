/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: {
                    50: '#f8fafc',
                    100: '#1a1f2e',
                    200: '#151929',
                    300: '#0f1117',
                    400: '#0a0c12',
                },
                brand: {
                    blue: '#58a6ff',
                    green: '#3fb950',
                    yellow: '#d29922',
                    red: '#f85149',
                    purple: '#bc8cff',
                    orange: '#ffa657',
                    cyan: '#39d5ff',
                    pink: '#ff6eb4',
                }
            },
            backgroundImage: {
                'gradient-radial':
                    'radial-gradient(var(--tw-gradient-stops))',
                'gradient-conic':
                    'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'glass':
                    'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))',
                'card-glow':
                    'linear-gradient(135deg, rgba(88,166,255,0.1), rgba(188,140,255,0.05))',
            },
            boxShadow: {
                'glow-blue':
                    '0 0 20px rgba(88,166,255,0.3), 0 0 60px rgba(88,166,255,0.1)',
                'glow-green':
                    '0 0 20px rgba(63,185,80,0.3), 0 0 60px rgba(63,185,80,0.1)',
                'glow-red':
                    '0 0 20px rgba(248,81,73,0.3), 0 0 60px rgba(248,81,73,0.1)',
                'glow-purple':
                    '0 0 20px rgba(188,140,255,0.3), 0 0 60px rgba(188,140,255,0.1)',
                'glass':
                    '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)',
                'card':
                    '0 4px 24px rgba(0,0,0,0.3)',
            },
            animation: {
                'float': 'float 6s ease-in-out infinite',
                'float-slow': 'float 8s ease-in-out infinite',
                'float-fast': 'float 4s ease-in-out infinite',
                'pulse-slow': 'pulse 4s cubic-bezier(0.4,0,0.6,1) infinite',
                'spin-slow': 'spin 8s linear infinite',
                'glow': 'glow 2s ease-in-out infinite alternate',
                'slide-up': 'slideUp 0.5s ease-out',
                'slide-in': 'slideIn 0.3s ease-out',
                'fade-in': 'fadeIn 0.4s ease-out',
                'bounce-slow': 'bounce 3s infinite',
                'shimmer': 'shimmer 2s infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-20px)' },
                },
                glow: {
                    '0%': { boxShadow: '0 0 20px rgba(88,166,255,0.3)' },
                    '100%': { boxShadow: '0 0 40px rgba(88,166,255,0.6), 0 0 80px rgba(88,166,255,0.2)' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: 0 },
                    '100%': { transform: 'translateY(0)', opacity: 1 },
                },
                slideIn: {
                    '0%': { transform: 'translateX(-20px)', opacity: 0 },
                    '100%': { transform: 'translateX(0)', opacity: 1 },
                },
                fadeIn: {
                    '0%': { opacity: 0 },
                    '100%': { opacity: 1 },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
            },
            backdropBlur: {
                xs: '2px',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
        },
    },
    plugins: [],
}