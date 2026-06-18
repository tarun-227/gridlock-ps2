/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy:  '#0D1B3E',
        teal:  '#00C2A8',
        'teal-light': '#E0FAF6',
        ice:   '#C8DEFF',
        'light-bg': '#F2F6FC',
        sub:   '#5A6A8A',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      }
    }
  },
  plugins: []
}
