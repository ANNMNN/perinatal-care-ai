/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Montserrat', 'sans-serif'],
      },
      colors: {
        navy:         '#023A84',
        'navy-light': '#3C6BB5',
        'navy-faint': '#AFC4E6',
        'card-bg':    '#EEF2F9',
        'page-bg':    '#F4F6FB',
        ink:          '#1A1A1A',
        muted:        '#7A8396',
        green:        '#1E8E4E',
        'green-bg':   '#E4F4EA',
        amber:        '#E0A526',
        'amber-dark': '#B9831A',
        'amber-bg':   '#FBF1DC',
        red:          '#D24B4B',
        'red-dark':   '#C0392B',
        'red-bg':     '#FBE3E3',
        border:       '#E6EAF2',
      },
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in': {
          '0%':   { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      animation: {
        'fade-up':  'fade-up 0.4s ease both',
        'fade-in':  'fade-in 0.3s ease both',
        'slide-in': 'slide-in 0.35s ease both',
      },
    },
  },
  plugins: [],
}
