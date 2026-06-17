import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          root: "#050810",
          panel: "#0d1526",
          surface: "#111d35",
          elevated: "#162540",
          glass: "rgba(13, 21, 38, 0.7)",
        },
        teal: {
          DEFAULT: "#00d4c8",
          dim: "#00a8a0",
          faint: "rgba(0, 212, 200, 0.08)",
        },
        gold: { DEFAULT: "#f5c542", faint: "rgba(245, 197, 66, 0.1)" },
        muted: "#4a6080",
        second: "#8ba3cc",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 0 0 rgba(0,212,200,0.4)" },
          "50%": { opacity: "0.8", boxShadow: "0 0 0 8px rgba(0,212,200,0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      backdropBlur: {
        glass: "20px",
      },
    },
  },
  plugins: [],
};

export default config;
