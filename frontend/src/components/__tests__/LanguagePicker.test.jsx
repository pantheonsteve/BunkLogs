import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../../api', () => ({
  __esModule: true,
  default: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

import api from '../../api';
import initI18n, { i18n } from '../../i18n';
import LanguagePicker from '../LanguagePicker';

describe('LanguagePicker', () => {
  beforeEach(() => {
    initI18n({ lng: 'en' });
    api.get.mockReset();
    api.patch.mockReset();
    api.get.mockResolvedValue({ data: { preferred_language: 'en', translation_preference: 'translation_first' } });
    api.patch.mockResolvedValue({ data: { preferred_language: 'es' } });
  });

  afterEach(() => {
    i18n.changeLanguage('en');
  });

  it('renders the three supported languages with native labels', async () => {
    render(<LanguagePicker />);
    const select = await screen.findByTestId('language-picker-select');
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);
    expect(options).toEqual([
      'English',
      'Español',
      expect.stringMatching(/עברית.*content only/),
    ]);
  });

  it('hydrates the saved server-side preference on mount', async () => {
    api.get.mockResolvedValueOnce({
      data: { preferred_language: 'es', translation_preference: 'translation_first' },
    });
    render(<LanguagePicker />);
    await waitFor(() => {
      expect(screen.getByTestId('language-picker-select').value).toBe('es');
    });
  });

  it('PATCHes the new language and flips the i18n locale', async () => {
    const user = userEvent.setup();
    render(<LanguagePicker />);
    await user.selectOptions(screen.getByTestId('language-picker-select'), 'es');
    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith(
        '/api/v1/me/preferences/',
        { preferred_language: 'es' },
      );
    });
    expect(i18n.resolvedLanguage).toBe('es');
    expect(await screen.findByTestId('language-picker-status')).toHaveTextContent(
      /Idioma actualizado|Language updated/,
    );
  });

  it('treats 404 from PATCH as a success (orphan user)', async () => {
    const user = userEvent.setup();
    api.patch.mockRejectedValueOnce({ response: { status: 404 } });
    render(<LanguagePicker />);
    await user.selectOptions(screen.getByTestId('language-picker-select'), 'es');
    await waitFor(() => {
      expect(screen.getByTestId('language-picker-status')).not.toHaveTextContent(
        /Could not update|saveFailed/,
      );
    });
    expect(i18n.resolvedLanguage).toBe('es');
  });

  it('surfaces an error message when the PATCH fails', async () => {
    const user = userEvent.setup();
    api.patch.mockRejectedValueOnce({ response: { status: 500 } });
    render(<LanguagePicker />);
    await user.selectOptions(screen.getByTestId('language-picker-select'), 'es');
    await waitFor(() => {
      expect(screen.getByTestId('language-picker-status')).toHaveTextContent(
        /No se pudo actualizar|Could not update/,
      );
    });
  });
});
