/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        slatepanel: "#111827",
        slatepanelLight: "#1f2937",
        surface: "#f8fafc"
      },
      boxShadow: {
        card: "0 8px 24px rgba(15, 23, 42, 0.08)"
      }
    }
  },
  plugins: []
};
