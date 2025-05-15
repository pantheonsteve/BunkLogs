import { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext({
  currentTheme: 'light',
  themeLoaded: false,
  changeCurrentTheme: () => {},
});

export default function ThemeProvider({children}) {  
  // Get theme from localStorage or use default
  const persistedTheme = typeof window !== 'undefined' ? localStorage.getItem('theme') : null;
  const [theme, setTheme] = useState(persistedTheme || 'light');
  const [themeLoaded, setThemeLoaded] = useState(false);

  const changeCurrentTheme = (newTheme) => {
    setTheme(newTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme);
    }
  };

  useEffect(() => {
    try {
      document.documentElement.classList.add('**:transition-none!');
      if (theme === 'light') {
        document.documentElement.classList.remove('dark');
        document.documentElement.style.colorScheme = 'light';
      } else {
        document.documentElement.classList.add('dark');
        document.documentElement.style.colorScheme = 'dark';
      }

      const transitionTimeout = setTimeout(() => {
        document.documentElement.classList.remove('**:transition-none!');
        setThemeLoaded(true);
      }, 1);
      
      return () => clearTimeout(transitionTimeout);
    } catch (error) {
      console.error('Error applying theme:', error);
      setThemeLoaded(true); // Still mark as loaded even on error
    }
  }, [theme]);

  return <ThemeContext.Provider value={{ currentTheme: theme, themeLoaded, changeCurrentTheme }}>{children}</ThemeContext.Provider>;
}

export const useThemeProvider = () => useContext(ThemeContext);