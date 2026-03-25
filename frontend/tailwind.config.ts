import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#11212b",
        fog: "#f4f1ea",
        line: "#d8d2c8",
        accent: "#0f766e",
        warning: "#c2410c",
        slate: "#425466",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Avenir Next", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 12px 40px rgba(17, 33, 43, 0.10)",
      },
      backgroundImage: {
        "dashboard-grid":
          "linear-gradient(rgba(17,33,43,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(17,33,43,0.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
} satisfies Config;

