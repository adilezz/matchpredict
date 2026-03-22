/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#0D0F14",
          1: "#12151E",
          2: "#161924",
          3: "#1A1D28",
          4: "#1E2230",
          5: "#222638",
          6: "#2A3040",
        },
        accent: {
          DEFAULT: "#00A83C",
          light: "#2DD45C",
          dark: "#008B32",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
