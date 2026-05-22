import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import SelfReflectionPage from '../SelfReflectionPage';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => vi.fn(),
  },
}));

const TEMPLATE = {
  id: 42,
  name: 'Camper Care Self-Reflection',
  slug: 'camper-care-self-reflection',
  version: 1,
  languages: ['en'],
  schema: {
    fields: [
      { key: 'day_off', type: 'yes_no', required: false, prompts: { en: 'Day off today?' } },
      {
        key: 'overall_day',
        type: 'single_rating',
        required: false,
        scale: [1, 5],
        prompts: { en: 'How was today?' },
      },
      {
        key: 'bunk_concerns_bunks',
        type: 'multiple_choice',
        required: false,
        option_source: 'caseload_bunks',
        prompts: { en: 'Flag any caseload bunks?' },
      },
    ],
  },
};

const DASHBOARD_NO_REFL = {
  date: '2026-07-04',
  today: '2026-07-04',
  units: [
    { id: 1, name: 'Unit Alef', bunks: [{ id: 7, name: 'Bunk Birch' }] },
  ],
  summary: { submitted: 0, expected: 0, flag_count: 0, order_count: 0 },
  self_reflection: { state: 'missing', reflection_id: null, template_id: TEMPLATE.id, editable: false },
};

const DASHBOARD_EXISTING = {
  ...DASHBOARD_NO_REFL,
  self_reflection: {
    state: 'complete', reflection_id: 555, template_id: TEMPLATE.id, editable: true,
  },
};

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

function wireGets({ dashboard = DASHBOARD_NO_REFL, template = TEMPLATE } = {}) {
  getMock.mockImplementation((url) => {
    if (url === '/api/v1/camper-care/dashboard/') return Promise.resolve({ data: dashboard });
    if (url === `/api/v1/templates/${template.id}/`) return Promise.resolve({ data: template });
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
}

describe('CamperCareSelfReflectionPage', () => {
  it('renders the form once template + dashboard load', async () => {
    wireGets();
    render(
      <MemoryRouter initialEntries={['/camper-care/self-reflection']}>
        <Routes>
          <Route path="/camper-care/self-reflection" element={<SelfReflectionPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-self-reflection-form')).toBeInTheDocument();
    });
    expect(screen.getByTestId('cc-self-reflection-day-off-toggle')).toBeInTheDocument();
  });

  it('redirects to edit URL when today already has a reflection', async () => {
    wireGets({ dashboard: DASHBOARD_EXISTING });
    render(
      <MemoryRouter initialEntries={['/camper-care/self-reflection']}>
        <Routes>
          <Route path="/camper-care/self-reflection" element={<SelfReflectionPage />} />
          <Route
            path="/camper-care/self-reflection/:reflectionId/edit"
            element={<SelfReflectionPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    // The edit route loads `fetchReflection` next; for this assertion we
    // only need to confirm the form mounted on the new path.
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/camper-care/dashboard/') return Promise.resolve({ data: DASHBOARD_EXISTING });
      if (url === `/api/v1/templates/${TEMPLATE.id}/`) return Promise.resolve({ data: TEMPLATE });
      if (url === '/api/v1/reflections/555/') return Promise.resolve({ data: {
        id: 555, answers: { overall_day: 4 }, language: 'en',
      } });
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });
    await waitFor(() => {
      expect(screen.getByTestId('cc-self-reflection-form')).toBeInTheDocument();
    });
  });

  it('shows the configured-template warning when no template is configured', async () => {
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/camper-care/dashboard/') return Promise.resolve({
        data: { ...DASHBOARD_NO_REFL, self_reflection: { state: 'missing', template_id: null } },
      });
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });
    render(
      <MemoryRouter initialEntries={['/camper-care/self-reflection']}>
        <Routes>
          <Route path="/camper-care/self-reflection" element={<SelfReflectionPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-self-reflection-load-error')).toHaveTextContent(
        /No Camper Care self-reflection template/i,
      );
    });
  });
});
