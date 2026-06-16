import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#E8F0FE",
          100: "#C5D7FB",
          200: "#9CBBF8",
          300: "#6B9CF5",
          400: "#4285F4",
          500: "#1A73E8",
          600: "#1557B0",
          700: "#0D3D8C",
          800: "#082B69",
          900: "#041A47",
        },
        safe: {
          low:      "#34A853",
          medium:   "#FBBC04",
          high:     "#EA4335",
          critical: "#C62828",
        },
        surface: {
          DEFAULT: "#F8FAFC",
          card:    "#FFFFFF",
          border:  "#E2E8F0",
        },
      },
      fontFamily: {
        sans: ["Inter", "Google Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "8px",
        lg: "12px",
        xl: "16px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)",
        modal: "0 4px 24px rgba(0,0,0,0.16)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
