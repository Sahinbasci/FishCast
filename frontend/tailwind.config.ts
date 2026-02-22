import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "20px",
        "2xl": "24px",
      },
      boxShadow: {
        sm: "0 2px 8px rgba(0,0,0,0.25)",
        md: "0 4px 16px rgba(0,0,0,0.3)",
        lg: "0 8px 32px rgba(0,0,0,0.35)",
        xl: "0 12px 40px rgba(0,0,0,0.4)",
      },
      dropShadow: {
        "glow-green": "0 0 8px rgba(34, 197, 94, 0.5)",
        "glow-orange": "0 0 8px rgba(249, 115, 22, 0.5)",
        "glow-red": "0 0 8px rgba(239, 68, 68, 0.5)",
        "glow-cyan": "0 0 8px rgba(6, 182, 212, 0.5)",
        "glow-blue": "0 0 8px rgba(59, 130, 246, 0.5)",
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both",
        shimmer: "shimmer 1.8s ease-in-out infinite",
        "score-fill":
          "score-ring-fill 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "score-ring-fill": {
          "0%": { strokeDashoffset: "var(--ring-circumference)" },
          "100%": { strokeDashoffset: "var(--ring-target)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
