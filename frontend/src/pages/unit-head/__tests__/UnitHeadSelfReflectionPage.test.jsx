import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import UnitHeadSelfReflectionPage from '../UnitHeadSelfReflectionPage';

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
  },
}));

function PathProbe() {
  const loc = useLocation();
  return <div data-testid="probe" data-pathname={loc.pathname} />;
}

const template = {
  id: 17,
  name: 'Unit Head Self-Reflection',
  slug: 'unit-head-self-reflection',
  version: 1,
  languages: ['en', 'es'],
  schema: {
    fields: [
      { key: 'day_off', type: 'yes_no', required: false, prompts: { en: 'Day off?' } },
      {
        key: 'overall_day',
        type: 'single_rating',
        required: false,
        scale: [1, 5],
        scale_labels: { en: ['Difficult', 'Tough', 'OK', 'Good', 'Great'] },
        prompts: { en: 'How was today?' },
      },
      {
        key: 'concern',
        type: 'textarea',
        required: false,
        prompts: { en: 'Anything to flag?' },
      },
      {
        key: 'bunk_concerns_bunks',
        type: 'multiple_choice',
        required: false,
        option_source: 'supervised_bunks',
        prompts: { en: 'Which bunks?' },
      },
    ],
  },
};

const dashboard = {
  today: '2026-07-04',
  bunks: [
    { id: 11, name: 'Alpha', unit_name: 'Unit One', completion: { submitted: 0, expected: 0, off_camp: 0 }, badges: [] },
    { id: 12, name: 'Bravo', unit_name: 'Unit One', completion: { submitted: 0, expected: 0, off_camp: 0 }, badges: [] },
  ],
  self_reflection: { state: 'missing', reflection_id: null, template_id: 17, editable: false },
};

function wireDashboardThenTemplate() {
  getMock.mockImplementation((url) => {
    if (url.startsWith('/api/v1/unit-head/dashboard/')) {
      return Promise.resolve({ data: dashboard });
    }
    if (url.startsWith('/api/v1/templates/17/')) {
      return Promise.resolve({ data: template });
    }
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
});

describe('UnitHeadSelfReflectionPage', () => {
  it('renders the form after loading the dashboard + template', async () => {
    wireDashboardThenTemplate();
    render(
      <MemoryRouter initialEntries={['/unit-head/self-reflection']}>
        <Routes>
          <Route path="/unit-head/self-reflection" element={<UnitHeadSelfReflectionPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('uh-self-reflection-form')).toBeInTheDocument();
    });
    expect(screen.getByText('How was today?')).toBeInTheDocument();
    expect(screen.getByText('Anything to flag?')).toBeInTheDocument();
    expect(screen.getByText('Which bunks?')).toBeInTheDocument();
  });

  it('injects supervised bunks as multiple-choice options', async () => {
    wireDashboardThenTemplate();
    render(
      <MemoryRouter initialEntries={['/unit-head/self-reflection']}>
        <Routes>
          <Route path="/unit-head/self-reflection" element={<UnitHeadSelfReflectionPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Alpha — Unit One')).toBeInTheDocument();
    });
    expect(screen.getByText('Bravo — Unit One')).toBeInTheDocument();
  });

  it('submits the day-off shortcut and redirects to the dashboard', async () => {
    wireDashboardThenTemplate();
    postMock.mockResolvedValueOnce({ data: { id: 99 }, status: 201 });
    render(
      <MemoryRouter initialEntries={['/unit-head/self-reflection']}>
        <Routes>
          <Route path="/unit-head" element={<PathProbe />} />
          <Route path="/unit-head/self-reflection" element={<UnitHeadSelfReflectionPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('uh-self-reflection-form')).toBeInTheDocument();
    });
    const user = userEvent.setup();
    await user.click(screen.getByTestId('uh-self-reflection-day-off-toggle'));
    await user.click(screen.getByTestId('uh-self-reflection-submit'));
    await waitFor(() => {
      expect(postMock).toHaveBeenCalled();
    });
    const [url, payload] = postMock.mock.calls[0];
    expect(url).toBe('/api/v1/unit-head/self-reflection/');
    expect(payload.day_off).toBe(true);
    expect(payload.client_submission_id).toBeTruthy();
  });

  it('redirects to edit when a submission already exists for today', async () => {
    getMock.mockImplementationOnce(() => Promise.resolve({
      data: {
        ...dashboard,
        self_reflection: { state: 'complete', reflection_id: 55, template_id: 17, editable: true },
      },
    })).mockImplementationOnce(() => Promise.resolve({ data: template }));
    render(
      <MemoryRouter initialEntries={['/unit-head/self-reflection']}>
        <Routes>
          <Route path="/unit-head/self-reflection" element={<UnitHeadSelfReflectionPage />} />
          <Route path="/unit-head/self-reflection/:reflectionId/edit" element={<PathProbe />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      const probe = screen.queryByTestId('probe');
      expect(probe?.getAttribute('data-pathname')).toBe('/unit-head/self-reflection/55/edit');
    });
  });
});
