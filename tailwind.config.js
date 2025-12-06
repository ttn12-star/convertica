/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './myapp/templates/**/*.html',
    './static/js/**/*.js'
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
