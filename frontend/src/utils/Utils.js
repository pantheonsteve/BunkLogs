export const formatValue = (value) => Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumSignificantDigits: 3,
  notation: 'compact',
}).format(value);

export const formatThousands = (value) => Intl.NumberFormat('en-US', {
  maximumSignificantDigits: 3,
  notation: 'compact',
}).format(value);

export const getCssVariable = (variable) => {
  try {
    const value = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
    if (!value) {
      console.warn(`CSS variable ${variable} returned an empty value`);
      return '#000000'; // Return a default color if the variable is not set
    }
    return value;
  } catch (error) {
    console.error(`Error getting CSS variable ${variable}:`, error);
    return '#000000'; // Return a default color on error
  }
};

const adjustHexOpacity = (hexColor, opacity) => {
  // Remove the '#' if it exists
  hexColor = hexColor.replace('#', '');

  // Convert hex to RGB
  const r = parseInt(hexColor.substring(0, 2), 16);
  const g = parseInt(hexColor.substring(2, 4), 16);
  const b = parseInt(hexColor.substring(4, 6), 16);

  // Return RGBA string
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
};

const adjustHSLOpacity = (hslColor, opacity) => {
  // Convert HSL to HSLA
  return hslColor.replace('hsl(', 'hsla(').replace(')', `, ${opacity})`);
};

const adjustOKLCHOpacity = (oklchColor, opacity) => {
  // Add alpha value to OKLCH color
  return oklchColor.replace(/oklch\((.*?)\)/, (match, p1) => `oklch(${p1} / ${opacity})`);
};

export const adjustColorOpacity = (color, opacity) => {
  // Trim whitespace to handle possible formatting issues
  color = color?.trim();
  
  if (!color) {
    console.warn('Empty or undefined color provided to adjustColorOpacity');
    return 'rgba(0, 0, 0, ' + opacity + ')'; // Return a default color instead of throwing
  }
  
  if (color.startsWith('#')) {
    return adjustHexOpacity(color, opacity);
  } else if (color.startsWith('hsl')) {
    return adjustHSLOpacity(color, opacity);
  } else if (color.startsWith('oklch')) {
    return adjustOKLCHOpacity(color, opacity);
  } else if (color.startsWith('rgb')) {
    // Handle RGB format by converting to RGBA
    return color.replace('rgb(', 'rgba(').replace(')', `, ${opacity})`);
  } else {
    console.warn('Unsupported color format:', color);
    return 'rgba(0, 0, 0, ' + opacity + ')'; // Return a default color instead of throwing
  }
};

export const oklchToRGBA = (oklchColor) => {
  // Create a temporary div to use for color conversion
  const tempDiv = document.createElement('div');
  tempDiv.style.color = oklchColor;
  document.body.appendChild(tempDiv);
  
  // Get the computed style and convert to RGB
  const computedColor = window.getComputedStyle(tempDiv).color;
  document.body.removeChild(tempDiv);
  
  return computedColor;
};