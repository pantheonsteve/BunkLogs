import { describe, it, expect } from 'vitest';
import { hasHtmlMarkup, htmlToPlainText } from '../RichText';

describe('htmlToPlainText', () => {
  it('returns plain strings unchanged', () => {
    expect(htmlToPlainText('missed family')).toBe('missed family');
    expect(htmlToPlainText('')).toBe('');
  });

  it('strips Quill HTML to readable text', () => {
    expect(htmlToPlainText('<p>Great day</p>')).toBe('Great day');
    expect(htmlToPlainText('<p>Line one</p><p>Line two</p>')).toBe('Line one\nLine two');
  });
});

describe('hasHtmlMarkup', () => {
  it('detects HTML tags', () => {
    expect(hasHtmlMarkup('<p>x</p>')).toBe(true);
    expect(hasHtmlMarkup('plain')).toBe(false);
  });
});
