// Import Chart.js
import { Chart, Tooltip } from 'chart.js';
// Import Tailwind config
import { adjustColorOpacity, getCssVariable } from '../utils/Utils';

// Safely get color values with fallbacks
function safeGetColor(variableName, fallbackColor = '#000000') {
  try {
    return getCssVariable(variableName) || fallbackColor;
  } catch (error) {
    console.warn(`Error getting color for ${variableName}:`, error);
    return fallbackColor;
  }
}

// Safely adjust opacity with error handling
function safeAdjustOpacity(variableName, opacity, fallbackColor = 'rgba(0,0,0,0.6)') {
  try {
    const color = safeGetColor(variableName);
    return adjustColorOpacity(color, opacity);
  } catch (error) {
    console.warn(`Error adjusting opacity for ${variableName}:`, error);
    return fallbackColor;
  }
}

// Define chartColors first before using it in functions
export const chartColors = {
  textColor: {
    light: safeGetColor('--color-gray-400', '#9ca3af'),
    dark: safeGetColor('--color-gray-500', '#6b7280'),
  },
  gridColor: {
    light: safeGetColor('--color-gray-100', '#f3f4f6'),
    dark: safeAdjustOpacity('--color-gray-700', 0.6, 'rgba(55,65,81,0.6)'),
  },
  backdropColor: {
    light: safeGetColor('--color-white', '#ffffff'),
    dark: safeGetColor('--color-gray-800', '#1f2937'),
  },
  tooltipTitleColor: {
    light: safeGetColor('--color-gray-800', '#1f2937'),
    dark: safeGetColor('--color-gray-100', '#f3f4f6'),
  },
  tooltipBodyColor : {
    light: safeGetColor('--color-gray-500', '#6b7280'),
    dark: safeGetColor('--color-gray-400', '#9ca3af')
  },
  tooltipBgColor: {
    light: safeGetColor('--color-white', '#ffffff'),
    dark: safeGetColor('--color-gray-700', '#374151'),
  },
  tooltipBorderColor: {
    light: safeGetColor('--color-gray-200', '#e5e7eb'),
    dark: safeGetColor('--color-gray-600', '#4b5563'),
  },
};

function updateChartTheme(isDarkMode) {
  const theme = isDarkMode ? 'dark' : 'light';
  Chart.defaults.color = chartColors.textColor[theme];
  Chart.defaults.borderColor = chartColors.gridColor[theme];
  Chart.defaults.backgroundColor = chartColors.backdropColor[theme];
  Chart.defaults.plugins.tooltip.titleColor = chartColors.tooltipTitleColor[theme];
  Chart.defaults.plugins.tooltip.bodyColor = chartColors.tooltipBodyColor[theme];
  Chart.defaults.plugins.tooltip.backgroundColor = chartColors.tooltipBgColor[theme];
  Chart.defaults.plugins.tooltip.borderColor = chartColors.tooltipBorderColor[theme];
}

// Initialize Chart.js safely - wait for DOM to be ready
function initChartJs() {
  try {
    Chart.register(Tooltip);

    // Define Chart.js default settings
    Chart.defaults.font.family = '"Inter", sans-serif';
    Chart.defaults.font.weight = 500;
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    
    // Set initial theme values
    const isDarkMode = document.documentElement.classList.contains('dark');
    updateChartTheme(isDarkMode);
    
    // Listen for theme changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          const isDarkMode = document.documentElement.classList.contains('dark');
          updateChartTheme(isDarkMode);
        }
      });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    console.log('Chart.js initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Chart.js:', error);
  }
}

// Initialize once DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChartJs);
  } else {
    initChartJs();
  }
}

// Function that generates a gradient for line charts
export const chartAreaGradient = (ctx, chartArea, colorStops) => {
  if (!ctx || !chartArea || !colorStops || colorStops.length === 0) {
    return 'transparent';
  }
  const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
  colorStops.forEach(({ stop, color }) => {
    gradient.addColorStop(stop, color);
  });
  return gradient;
};
