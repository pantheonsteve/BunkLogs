import '@testing-library/jest-dom/vitest';
import 'fake-indexeddb/auto';
import React from 'react';
import { vi } from 'vitest';

// Quill is heavy and not jsdom-friendly. Replace the Wysiwyg widget with a
// plain textarea for tests so render paths that include rich text (e.g.
// reflection textarea fields, BunkLog Daily Report) stay fast and stable.
vi.mock('./components/form/Wysiwyg', () => ({
  default: function MockWysiwyg(props) {
    return React.createElement('textarea', {
      'data-testid': 'mock-wysiwyg',
      defaultValue: props.value || '',
      readOnly: !!props.readOnly,
      onChange: (e) => props.onChange && props.onChange(e.target.value),
    });
  },
}));

// Mock environment variables for tests
process.env.VITE_GOOGLE_CLIENT_ID = 'test-google-client-id';
process.env.VITE_API_BASE_URL = 'http://localhost:8000';
