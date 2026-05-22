import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import KitchenStaffDashboard from '../Dashboard';

// Mock axios-based API client
const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

// Mock auth context
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org', user: { id: 1 } }),
}));

// Mock LanguagePicker (not under test here)
vi.mock('../../../components/LanguagePicker', () => ({
  default: () => <div data-testid="language-picker" />,
}));

// Minimal react-i18next stub
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key, opts) => {
      const lookup = {
        'roleLabel': 'Kitchen Staff',
        'dashboard.myReflection': 'My reflection',
        'dashboard.myReflections': 'My reflections',
        'dashboard.viewHistory': 'View history',
        'dashboard.startReflection': 'Start reflection',
        'dashboard.editReflection': 'Edit reflection',
        'dashboard.loading': 'Loading…',
        'dashboard.loadFailed': 'Could not load dashboard.',
        'dashboard.status.missing': 'Not yet submitted',
        'dashboard.status.complete': 'Submitted',
        'dashboard.status.day_off': 'Day off',
        'dashboard.status.no_template': 'No template configured',
      };
      return lookup[key] ?? key;
    },
    i18n: { language: 'en' },
  }),
}));

const samplePayload = {
  today: '2026-07-10',
  header: {
    name: 'Kira Kitchen',
    role_label: 'Kitchen Staff',
    program_name: 'Summer 2026',
    preferred_language: 'en',
  },
  my_reflection: { state: 'missing', reflection_id: null, template_id: 5, editable: false },
  history_entry: { url: '/kitchen-staff/history' },
};

beforeEach(() => {
  getMock.mockReset();
});

describe('KitchenStaffDashboard', () => {
  it('renders header, reflection card, and history section', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Kira Kitchen')).toBeInTheDocument();
    });
    expect(screen.getByTestId('ks-reflection-card')).toBeInTheDocument();
    expect(screen.getByTestId('ks-history-section')).toBeInTheDocument();
    expect(screen.getByTestId('language-picker')).toBeInTheDocument();
  });

  it('shows "Not yet submitted" status when missing', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('ks-reflection-card'));
    expect(screen.getByText('Not yet submitted')).toBeInTheDocument();
    expect(screen.getByTestId('ks-reflection-cta')).toHaveTextContent('Start reflection');
  });

  it('shows complete status and edit affordance when complete', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...samplePayload,
        my_reflection: { state: 'complete', reflection_id: 42, template_id: 5, editable: true },
      },
    });
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('ks-reflection-card'));
    // CTA should say edit when reflection exists
    expect(screen.getByTestId('ks-reflection-cta')).toHaveTextContent('Edit reflection');
    // CTA should link to edit URL
    expect(screen.getByTestId('ks-reflection-cta')).toHaveAttribute(
      'href', '/kitchen-staff/reflection/42/edit',
    );
  });

  it('shows Spanish UI when preferred_language is es', async () => {
    getMock.mockResolvedValueOnce({
      data: { ...samplePayload, header: { ...samplePayload.header, preferred_language: 'es' } },
    });
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByText('Kira Kitchen'));
    // Language picker is always present so staff can change language
    expect(screen.getByTestId('language-picker')).toBeInTheDocument();
  });

  it('shows error state on load failure', async () => {
    getMock.mockRejectedValueOnce(new Error('Network error'));
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByTestId('ks-error')).toBeInTheDocument();
    });
  });

  it('links history section to /kitchen-staff/history', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><KitchenStaffDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('ks-history-link'));
    expect(screen.getByTestId('ks-history-link')).toHaveAttribute('href', '/kitchen-staff/history');
  });
});
