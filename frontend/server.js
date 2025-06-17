const express = require('express');
const path = require('path');
const app = express();

// Security headers
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  next();
});

// Serve static files from the dist directory with proper MIME types
app.use(express.static(path.join(__dirname, 'dist'), {
  // Set cache headers for static assets
  setHeaders: (res, path) => {
    if (path.endsWith('.js') || path.endsWith('.css')) {
      res.setHeader('Cache-Control', 'public, max-age=31536000'); // 1 year
    }
  }
}));

// Handle client-side routing - serve index.html for all non-static file routes
app.get('*', (req, res) => {
  // Don't serve index.html for static assets
  if (req.path.match(/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map)$/)) {
    return res.status(404).send('File not found');
  }
  
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

const port = process.env.PORT || 3000;
app.listen(port, '0.0.0.0', () => {
  console.log(`Server running on port ${port}`);
});