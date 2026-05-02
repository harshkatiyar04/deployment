import { useState, useEffect } from 'react';
import { FastAverageColor } from 'fast-average-color';

// Simple hex tint/shade utility
function adjustColor(color, amount) {
    return '#' + color.replace(/^#/, '').replace(/../g, color => 
        ('0' + Math.min(255, Math.max(0, parseInt(color, 16) + amount)).toString(16)).substr(-2)
    );
}

// Convert hex to rgb string for rgba()
function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r}, ${g}, ${b}`;
}

export function useBrandColor(imageUrl) {
  // Default to ZenK Orange while loading
  const [theme, setTheme] = useState({ 
    start: '#c85a17', 
    mid: '#e67e22', 
    end: '#f39c12', 
    shadow: 'rgba(200, 90, 23, 0.8)' 
  });

  useEffect(() => {
    if (!imageUrl) return;

    const fac = new FastAverageColor();
    const img = new Image();
    // Required to prevent CORS tainted canvas error when extracting from external domains
    img.crossOrigin = 'anonymous'; 
    img.src = imageUrl;

    img.onload = () => {
      try {
        const color = fac.getColor(img);
        
        let baseHex = color.hex;
        
        // Handle black & white / grayscale logos to create a premium sleek dark theme
        const r = color.value[0], g = color.value[1], b = color.value[2];
        const isGrayscale = Math.abs(r - g) < 20 && Math.abs(g - b) < 20 && Math.abs(r - b) < 20;
        
        if (isGrayscale) {
            if (color.isLight) {
                baseHex = '#48484a'; // Sleek dark gray for white logos
            } else {
                baseHex = '#1c1c1e'; // Pitch sleek black for dark logos
            }
        }

        // Generate dynamic 3-stop gradient
        const start = adjustColor(baseHex, -20);
        const mid = baseHex;
        const end = adjustColor(baseHex, 35);
        
        const rgb = hexToRgb(baseHex);
        const shadow = `rgba(${rgb}, 0.8)`;

        setTheme({ start, mid, end, shadow });
      } catch (e) {
        console.error('Error extracting dominant color from logo:', e);
      }
    };
  }, [imageUrl]);

  return theme;
}
