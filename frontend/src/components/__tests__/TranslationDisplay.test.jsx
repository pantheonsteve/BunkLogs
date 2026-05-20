import { describe, it, expect, vi, beforeEach } from 'vitest';
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
import initI18n from '../../i18n';
import TranslationDisplay from '../TranslationDisplay';

const ORIGINAL = 'Hoy fue un buen día.';
const ENGLISH = 'Today was a good day.';

describe('TranslationDisplay', () => {
  beforeEach(() => {
    initI18n({ lng: 'en' });
    api.get.mockReset();
    api.patch.mockReset();
    api.get.mockResolvedValue({
      data: { preferred_language: 'en', translation_preference: 'translation_first' },
    });
    api.patch.mockResolvedValue({ data: {} });
  });

  it('renders only the original when no translation metadata is passed', () => {
    render(<TranslationDisplay originalText={ORIGINAL} sourceLanguage="es" translation={null} />);
    expect(screen.getByTestId('translation-display-original-only')).toHaveTextContent(ORIGINAL);
  });

  it('shows the pending message in the translated block while translation is in progress', () => {
    render(
      <TranslationDisplay
        originalText={ORIGINAL}
        sourceLanguage="es"
        translation={{ status: 'pending' }}
        initialPreference="translation_first"
      />,
    );
    expect(screen.getByTestId('translation-display-pending')).toBeInTheDocument();
  });

  it('renders both blocks when completed and respects the translation_first preference', () => {
    render(
      <TranslationDisplay
        originalText={ORIGINAL}
        sourceLanguage="es"
        translation={{ status: 'completed', translated_text: ENGLISH }}
        initialPreference="translation_first"
      />,
    );
    expect(screen.getByTestId('translation-display-completed')).toHaveTextContent(ENGLISH);
    expect(screen.getByTestId('translation-display-original')).toHaveTextContent(ORIGINAL);
    const root = screen.getByTestId('translation-display');
    const completedIdx = root.innerHTML.indexOf('translation-display-completed');
    const originalIdx = root.innerHTML.indexOf('translation-display-original');
    expect(completedIdx).toBeLessThan(originalIdx);
  });

  it('flips block order when the reader prefers the original first', async () => {
    const user = userEvent.setup();
    render(
      <TranslationDisplay
        originalText={ORIGINAL}
        sourceLanguage="es"
        translation={{ status: 'completed', translated_text: ENGLISH }}
        initialPreference="translation_first"
      />,
    );
    await user.click(screen.getByTestId('translation-display-preference-toggle'));
    const root = screen.getByTestId('translation-display');
    const completedIdx = root.innerHTML.indexOf('translation-display-completed');
    const originalIdx = root.innerHTML.indexOf('translation-display-original');
    expect(originalIdx).toBeLessThan(completedIdx);
    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith(
        '/api/v1/me/preferences/',
        { translation_preference: 'original_first' },
      );
    });
  });

  it('shows the retry CTA in failed_retryable state and calls onRetry when clicked', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn().mockResolvedValue(undefined);
    render(
      <TranslationDisplay
        originalText={ORIGINAL}
        sourceLanguage="es"
        translation={{ status: 'failed_retryable' }}
        initialPreference="translation_first"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByTestId('translation-display-failed-retryable')).toBeInTheDocument();
    await user.click(screen.getByTestId('translation-display-retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows the terminal error message without a retry CTA', () => {
    render(
      <TranslationDisplay
        originalText={ORIGINAL}
        sourceLanguage="he"
        translation={{ status: 'failed_terminal' }}
        initialPreference="translation_first"
      />,
    );
    expect(screen.getByTestId('translation-display-failed-terminal')).toBeInTheDocument();
    expect(screen.queryByTestId('translation-display-retry')).not.toBeInTheDocument();
  });

  it('marks Hebrew originals as RTL', () => {
    render(
      <TranslationDisplay
        originalText="שלום"
        sourceLanguage="he"
        translation={{ status: 'completed', translated_text: 'Hello' }}
        initialPreference="translation_first"
      />,
    );
    const original = screen.getByTestId('translation-display-original');
    expect(original).toHaveAttribute('dir', 'rtl');
    expect(original).toHaveAttribute('lang', 'he');
  });
});
