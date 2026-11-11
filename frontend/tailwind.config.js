/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        deep: "#0f0f10",
        base: "#141415",
        surface: "#19191b",
        raised: "#232325",
        input: "#111113",
        line: "rgba(237, 237, 237, 0.08)",
        lineStrong: "rgba(237, 237, 237, 0.16)",
        lineHover: "rgba(237, 237, 237, 0.28)",
        fg: {
          DEFAULT: "#ededed",
          secondary: "#a1a1a6",
          muted: "#85858b",
        },
        accent: {
          DEFAULT: "#b8f352",
          ink: "#0d1305",
          soft: "rgba(184, 243, 82, 0.12)",
        },
        danger: "#e5484d",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      borderRadius: {
        panel: "16px",
        card: "12px",
        control: "8px",
        tag: "4px",
      },
      maxWidth: {
        content: "1440px",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 240ms cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};
