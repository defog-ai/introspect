const plugin = require("tailwindcss/plugin");

module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./utils/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@defogdotai/agents-ui-components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // important: true,
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "very-light-blue": "#fafcff",
        "very-light-orange": "#fffcfa",
        "very-light-green": "#fbfef9",
        "light-blue": "#eff2fd",
        "light-orange": "#fff4ed",
        "light-green": "#eaf8e5",
        "light-red": "#fdeff0",
        "medium-blue": "#6381f7",
        "medium-blue-opacity": "rgba(99, 129, 247, 0.3)",
        "medium-light-orange": "#f7caae",
        "medium-orange": "#ffa565",
        "medium-orange-opacity": "rgba(247, 161, 100, 0.3)",
        "medium-green": "#96c880",
        "medium-green-opacity": "rgba(193, 225, 179, 0.3)",
        "medium-red": "#efa1a1",
        "medium-red-opacity": "rgba(239, 161, 161, 0.3)",
        "dark-blue": "#2957ff",
        "dark-orange": "#ff8229",
        "dark-green": "#63b758",
        "dark-red": "#f04646",
        "text-dark": "#171717",
        "text-medium": "#4c4c4c",
        "text-light": "#a0a0a0",
        "text-very-light": "#d0d0d0",
        white: "#ffffff",
        "dark-gray": "#4c4c4c",
        "medium-gray": "#949494",
        "light-gray": "#efefef",
        "very-light-gray": "#fafafa",
        "text-blue": "#6481f7",
        "text-orange": "#f3b289",
        "text-green": "#607158",
        "text-red": "#fca5a5",
        green: "#96c880",
        red: "#fc8e8e",
        "primary-text": "#2B2B2B",
        "primary-highlight": "#2B59FF",
        "secondary-highlight-1": "#6E00A2",
        "secondary-highlight-2": "#7891EE",
        "secondary-highlight-3": "rgba(112, 0, 163, 0.2)",
        "secondary-highlight-4": "hsla(37, 100%, 53%, 0.2)",
        dark: {
          "bg-primary": "#1a1a1a",
          "bg-secondary": "#2d2d2d",
          "text-primary": "#ffffff",
          "text-secondary": "#e0e0e0",
          border: "#404040",
          hover: "#404040",
        },
      },
      boxShadow: {
        custom: " rgba(0, 0, 0, 0.24) 0px 3px 8px",
      },
      height: {
        "10vh": "10vh",
        "20vh": "20vh",
        "30vh": "30vh",
        "40vh": "40vh",
        "50vh": "50vh",
        "60vh": "60vh",
        "70vh": "70vh",
        "80vh": "80vh",
        "90vh": "90vh",
        "100vh": "100vh",
      },
      width: {
        "10vw": "10vw",
        "20vw": "20vw",
        "30vw": "30vw",
        "40vw": "40vw",
        "50vw": "50vw",
        "60vw": "60vw",
        "70vw": "70vw",
        "80vw": "80vw",
        "90vw": "90vw",
        "100vw": "100vw",
      },
      keyframes: {
        "fade-in-down": {
          // first opacity 0 to 1
          // then display none
          "0%": {
            opacity: "0",
            transform: "translateY(-20px)",
          },
          "20%": {
            opacity: "1",
            transform: "translateY(0)",
          },
        },
        "fade-in": {
          "0%": {
            opacity: "0",
          },
          "100%": {
            opacity: "1",
          },
        },
      },
      animation: {
        "fade-in-down": "fade-in-down 1s",
        "fade-in": "fade-in 0.2s",
      },
      fontFamily: {
        platypi: ["Platypi, serif"],
      },
    },
  },

  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
    plugin(function ({ addUtilities }) {
      addUtilities({
        ".writing-vertical": {
          "writing-mode": "tb lr",
          transform: "rotate(-180deg)",
        },
        ".arrow-up": {
          width: "0",
          height: "0",
          borderLeft: "5px solid transparent",
          borderRight: "5px solid transparent",
        },
        ".arrow-down": {
          width: "0",
          height: "0",
          borderLeft: "5px solid transparent",
          borderRight: "5px solid transparent",
        },
        ".text-shadow-none": {
          textShadow: "none",
        },
      });
    }),
  ],
};
