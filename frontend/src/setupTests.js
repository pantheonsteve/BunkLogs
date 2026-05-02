import '@testing-library/jest-dom/vitest';

// Mock environment variables for tests
process.env.VITE_GOOGLE_CLIENT_ID = 'test-google-client-id';
process.env.VITE_API_BASE_URL = 'http://localhost:8000';
