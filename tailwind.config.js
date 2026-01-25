/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class', // Enable dark mode with 'dark' class
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
    // Related tools gradients (context_processors.py)
    'from-blue-500', 'to-blue-600',
    'from-indigo-500', 'to-indigo-600',
    'from-green-500', 'to-green-600',
    'from-emerald-500', 'to-emerald-600',
    'from-teal-500', 'to-teal-600',
    'from-cyan-500', 'to-cyan-600',
    // Menu icon colors for add_watermark (header.html)
    'bg-cyan-100', 'bg-cyan-200', 'text-cyan-600',
    'from-purple-500', 'to-purple-600',
    'from-pink-500', 'to-pink-600',
    'from-orange-500', 'to-orange-600',
    'from-red-500', 'to-red-600',
    'from-yellow-500', 'to-yellow-600',
    'from-lime-500', 'to-lime-600',
    'from-violet-500', 'to-violet-600',
    'from-fuchsia-500', 'to-fuchsia-600',
    'from-rose-500', 'to-rose-600',
    'from-amber-500', 'to-amber-600',
    'from-sky-500', 'to-sky-600',
    'from-slate-500', 'to-slate-600',
    'from-blue-500', 'to-purple-500',
    'from-purple-500', 'to-blue-500',
    'from-red-500', 'to-orange-500',
    'from-orange-500', 'to-red-500',
    // YouTube video component (youtube_video.html)
    'group-hover:scale-105',
    'group-hover:scale-110',
    'group-hover:bg-red-500',
    'bg-black/20',
    'bg-black/30',
    'from-black/80',
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
