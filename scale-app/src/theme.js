import { createContext, useState, useMemo } from "react";
import { createTheme } from "@mui/material";

// color design tokens
export const tokens = (mode) => ({
  ...(mode === "dark"
    ? {
        purpleAccent: {
          100: "#d7d5d6",
          200: "#afacae",
          300: "#878285",
          400: "#5f595d",
          500: "#372f34",
          600: "#2c262a",
          700: "#211c1f",
          800: "#161315",
          900: "#0b090a",
        },

        grayAccent: {
          100: "#e4eacf",
          200: "#cad59f",
          300: "#afbf6f",
          400: "#95aa3f",
          500: "#7a950f",
          600: "#62770c",
          700: "#495909",
          800: "#313c06",
          900: "#181e03",
        },

        greenAccent: {
          100: "#dad9d3",
          200: "#b4b4a7",
          300: "#8f8e7a",
          400: "#69694e",
          500: "#444322",
          600: "#36361b",
          700: "#292814",
          800: "#1b1b0e",
          900: "#0e0d07",
        },

        brownAccent: {
          100: "#dad9d7",
          200: "#b4b3af",
          300: "#8f8d86",
          400: "#69675e",
          500: "#444136",
          600: "#36342b",
          700: "#292720",
          800: "#1b1a16",
          900: "#0e0d0b",
        },

        primary: {
          100: "#ccd1d2",
          200: "#99a2a5",
          300: "#667479",
          400: "#33454c",
          500: "#00171f",
          600: "#001219",
          700: "#000e13",
          800: "#00090c",
          900: "#000506",
        },
      }
    : {
        purpleAccent: {
          100: "#0b090a",
          200: "#161315",
          300: "#211c1f",
          400: "#2c262a",
          500: "#372f34",
          600: "#5f595d",
          700: "#878285",
          800: "#afacae",
          900: "#d7d5d6",
        },

        grayAccent: {
          100: "#181e03",
          200: "#313c06",
          300: "#495909",
          400: "#62770c",
          500: "#7a950f",
          600: "#95aa3f",
          700: "#afbf6f",
          800: "#cad59f",
          900: "#e4eacf",
        },

        greenAccent: {
          100: "#0e0d07",
          200: "#1b1b0e",
          300: "#292814",
          400: "#36361b",
          500: "#444322",
          600: "#69694e",
          700: "#8f8e7a",
          800: "#b4b4a7",
          900: "#dad9d3",
        },

        brownAccent: {
          100: "#0e0d0b",
          200: "#1b1a16",
          300: "#292720",
          400: "#36342b",
          500: "#444136",
          600: "#69675e",
          700: "#8f8d86",
          800: "#b4b3af",
          900: "#dad9d7",
        },

        primary: {
          100: "#000506",
          200: "#00090c",
          300: "#000e13",
          400: "#001219",
          500: "#00171f",
          600: "#33454c",
          700: "#667479",
          800: "#99a2a5",
          900: "#ccd1d2",
        },
      }),
});

export const themeSettings = (mode) => {
  const colors = tokens(mode);

  return {
    palette: {
      mode: mode,
      ...(mode === "dark"
        ? {
            primary: {
              main: colors.primary[500],
            },
            secondary: {
              main: colors.greenAccent[500],
            },
            neutral: {
              dark: colors.grayAccent[700],
              main: colors.grayAccent[500],
              light: colors.grayAccent[100],
            },
            background: {
              default: "#171612",
              paper: "#c7c7c7b4",
            },
          }
        : {
            // palette values for light mode
            primary: {
              main: colors.primary[100],
            },
            secondary: {
              main: colors.greenAccent[500],
            },
            neutral: {
              dark: colors.grayAccent[700],
              main: colors.grayAccent[500],
              light: colors.grayAccent[100],
            },
            background: {
              default: "#fcfcfc",
              paper: "#fff9f9c5",
            },
          }),
    },
    typography: {
      fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
      fontSize: 12,
      h1: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 40,
      },
      h2: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 32,
      },
      h3: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 24,
      },
      h4: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 20,
      },
      h5: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 16,
      },
      h6: {
        fontFamily: ["Cal Sans","Inter", "sans-serif"].join(","),
        fontSize: 14,
      },
    },
  };
};

// context for color mode
export const ColorModeContext = createContext({
  toggleColorMode: () => {},
});

export const useMode = () => {
  const [mode, setMode] = useState("dark");

  const colorMode = useMemo(
    () => ({
      toggleColorMode: () =>
        setMode((prev) => (prev === "light" ? "dark" : "light")),
    }),
    []
  );

  const theme = useMemo(() => createTheme(themeSettings(mode)), [mode]);
  return [theme, colorMode];
};
