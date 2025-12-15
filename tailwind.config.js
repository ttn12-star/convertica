/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './myapp/templates/**/*.html',
    './static/js/**/*.js'
  ],
  // Safelist classes used in dynamic JS that Tailwind might miss
  safelist: [
    // Patience message classes (utils.js)
    'from-emerald-100',
    'to-teal-100',
    'border-emerald-400',
    'bg-emerald-500',
    'text-emerald-800',
    'text-emerald-700',
    'animate-fade-in',
  ],
  theme: {
    extend: {
      width: {
        '1100': '1100px',
      },
    },
  },
  plugins: [],
}
