import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import TasksPage from './TasksPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function selfTask(overrides = {}) {
  return {
    id: 'aaa',
    template: { id: 1, name: 'Daily Check-In', cadence: 'daily', slug: 'daily-checkin' },
    assignment_group: null,
    subject_mode: 'self',
    period: { start: '2026-06-15', end: '2026-06-15' },
    program_slug: 'summer-2026',
    subjects: [],
    completion: { covered: 0, total: 1, my_count: 0 },
    self_status: { submitted: false, reflection_id: null, submitted_at: null },
    ...overrides,
  };
}

function rosterTask(subjects = [], overrides = {}) {
  return {
    id: 'bbb',
    template: { id: 2, name: 'Bunk Log', cadence: 'daily', slug: 'bunk-log' },
    assignment_group: { id: 10, name: 'Bunk Maple', group_type: 'bunk' },
    subject_mode: 'single_subject',
    period: { start: '2026-06-15', end: '2026-06-15' },
    program_slug: 'summer-2026',
    subjects,
    completion: {
      covered: subjects.filter((s) => s.covered).length,
      total: subjects.length,
      my_count: subjects.filter((s) => s.covered_by_me).length,
    },
    self_status: null,
    ...overrides,
  };
}

function groupTask(overrides = {}) {
  return {
    id: 'ccc',
    template: { id: 3, name: 'Unit Reflection', cadence: 'weekly', slug: 'unit-reflect' },
    assignment_group: { id: 11, name: 'Junior Boys', group_type: 'unit' },
    subject_mode: 'group',
    period: { start: '2026-06-15', end: '2026-06-21' },
    program_slug: 'summer-2026',
    subjects: [],
    completion: { covered: 0, total: 1, my_count: 0 },
    self_status: null,
    ...overrides,
  };
}

const sarahSubject = {
  person_id: 101,
  name: 'Sarah Levin',
  preferred_name: 'Sarah',
  covered: false,
  covered_by_me: false,
  reflection_id: null,
  covered_by_name: null,
};

const edenSubject = {
  person_id: 102,
  name: 'Eden Cohen',
  preferred_name: 'Eden',
  covered: true,
  covered_by_me: true,
  reflection_id: 55,
  covered_by_name: 'Counselor Mike',
};

function renderPage(initialEntries = ['/tasks']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/tasks" element={<TasksPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TasksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  it('shows loading state initially', () => {
    getMock.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText(/loading tasks/i)).toBeInTheDocument();
  });

  it('shows error when API fails', async () => {
    getMock.mockRejectedValue({ response: { data: { detail: 'Not found' } } });
    renderPage();
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/not found/i)).toBeInTheDocument();
  });

  it('shows empty state when no tasks', async () => {
    getMock.mockResolvedValue({ data: { tasks: [] } });
    renderPage();
    await waitFor(() => expect(screen.getByText(/no tasks for today/i)).toBeInTheDocument());
  });

  // Self section
  it('renders self-reflection task as card', async () => {
    getMock.mockResolvedValue({ data: { tasks: [selfTask()] } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Daily Check-In')).toBeInTheDocument());
    expect(screen.getByText(/your reflection/i)).toBeInTheDocument();
  });

  it('self card navigates to form on click', async () => {
    getMock.mockResolvedValue({ data: { tasks: [selfTask()] } });
    renderPage();
    const card = await waitFor(() => screen.getByRole('button', { name: /daily check-in.*not yet submitted/i }));
    await userEvent.click(card);
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('/reflect?'));
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('template=1'));
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('program=summer-2026'));
  });

  it('completed self card shows submitted indicator', async () => {
    const task = selfTask({
      completion: { covered: 1, total: 1, my_count: 1 },
      self_status: { submitted: true, reflection_id: 99, submitted_at: '2026-06-15T14:00:00Z' },
    });
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    await waitFor(() => expect(screen.getByText(/submitted/i)).toBeInTheDocument());
  });

  // Roster section (single_subject)
  it('renders subject pills for single_subject tasks', async () => {
    const task = rosterTask([sarahSubject, edenSubject]);
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Bunk Maple')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /sarah levin.*not yet logged/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /eden cohen.*logged/i })).toBeInTheDocument();
  });

  it('tapping an uncovered pill navigates to form with subject params', async () => {
    const task = rosterTask([sarahSubject]);
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    const pill = await waitFor(() => screen.getByRole('button', { name: /sarah/i }));
    await userEvent.click(pill);
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('subject=101'));
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('assignment_group=10'));
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('subject_name=Sarah+Levin'));
  });

  it('covered pill shows popover instead of navigating', async () => {
    const task = rosterTask([edenSubject]);
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    const pill = await waitFor(() => screen.getByRole('button', { name: /eden cohen/i }));
    await userEvent.click(pill);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // Group section
  it('renders group task as card', async () => {
    getMock.mockResolvedValue({ data: { tasks: [groupTask()] } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Unit Reflection')).toBeInTheDocument());
    expect(screen.getByText('Junior Boys')).toBeInTheDocument();
  });

  it('group card navigates to form on click', async () => {
    getMock.mockResolvedValue({ data: { tasks: [groupTask()] } });
    renderPage();
    const card = await waitFor(() =>
      screen.getByRole('button', { name: /unit reflection.*junior boys.*pending/i }),
    );
    await userEvent.click(card);
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('subject_group=11'));
  });

  // Summary bar
  it('summary bar shows correct counts', async () => {
    const completedTask = selfTask({
      completion: { covered: 1, total: 1, my_count: 1 },
      self_status: { submitted: true, reflection_id: 1, submitted_at: '2026-06-15T14:00:00Z' },
    });
    const pendingTask = rosterTask([sarahSubject]);
    getMock.mockResolvedValue({ data: { tasks: [completedTask, pendingTask] } });
    renderPage();
    await waitFor(() => expect(screen.getByText(/1 task waiting/i)).toBeInTheDocument());
    expect(screen.getByText(/1\/2 completed/i)).toBeInTheDocument();
  });

  it('summary bar shows all done when everything complete', async () => {
    const task = selfTask({
      completion: { covered: 1, total: 1, my_count: 1 },
      self_status: { submitted: true, reflection_id: 1, submitted_at: null },
    });
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    await waitFor(() => expect(screen.getByText(/all done/i)).toBeInTheDocument());
  });

  // multi_subject: renders same as single_subject in v1
  it('renders multi_subject same as single_subject', async () => {
    const task = rosterTask([sarahSubject], { subject_mode: 'multi_subject' });
    getMock.mockResolvedValue({ data: { tasks: [task] } });
    renderPage();
    await waitFor(() => expect(screen.getByRole('button', { name: /sarah/i })).toBeInTheDocument());
  });
});
