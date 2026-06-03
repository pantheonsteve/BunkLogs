import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CamperPicker from '../CamperPicker';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
});

const sampleBunks = [
  { id: 1, name: 'Elm' },
  { id: 2, name: 'Oak' },
  { id: 3, name: 'Pine' },
];

const sampleData = {
  recent: [
    { id: 10, display_name: 'Recent Cam', first_name: 'Recent', last_name: 'Cam', bunk_name: 'Oak', bunk_id: 2, preferred_name: null },
  ],
  results: [
    { id: 11, display_name: 'Jake Smith', first_name: 'Jake', last_name: 'Smith', bunk_name: 'Elm', bunk_id: 1, preferred_name: null },
    { id: 12, display_name: 'Alice Johnson', first_name: 'Alice', last_name: 'Johnson', bunk_name: 'Pine', bunk_id: 3, preferred_name: null },
  ],
  bunks: sampleBunks,
  zero_results_message: null,
};

describe('CamperPicker', () => {
  it('renders all campers in initial load', async () => {
    getMock.mockResolvedValue({ data: sampleData });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.queryByTestId('sp-picker-loading')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('sp-camper-row-11')).toBeInTheDocument();
    expect(screen.getByTestId('sp-camper-row-12')).toBeInTheDocument();
  });

  it('renders Recent section when not searching', async () => {
    getMock.mockResolvedValue({ data: sampleData });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-picker-recent')).toBeInTheDocument());
    expect(screen.getByTestId('sp-camper-row-10')).toBeInTheDocument();
  });

  it('calls onSelect with camper when row is clicked', async () => {
    const onSelect = vi.fn();
    getMock.mockResolvedValue({ data: sampleData });
    render(<MemoryRouter><CamperPicker onSelect={onSelect} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-camper-row-11')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('sp-camper-row-11'));
    expect(onSelect).toHaveBeenCalledWith(sampleData.results[0]);
  });

  it('shows zero results message when no matches', async () => {
    getMock.mockResolvedValue({
      data: { recent: [], results: [], zero_results_message: 'No campers match XYZ.' },
    });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-picker-zero')).toBeInTheDocument());
    expect(screen.getByText(/No campers match XYZ/)).toBeInTheDocument();
  });

  it('does not fire second API call before debounce interval', async () => {
    getMock.mockResolvedValue({ data: sampleData });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));

    const input = screen.getByTestId('sp-camper-search');
    fireEvent.change(input, { target: { value: 'J' } });
    fireEvent.change(input, { target: { value: 'Ja' } });
    // Rapid typing should not fire immediately beyond the initial call
    expect(getMock).toHaveBeenCalledTimes(1);
  });

  it('renders 20 campers without error (performance proxy)', async () => {
    const many = Array.from({ length: 20 }, (_, i) => ({
      id: i + 1,
      display_name: `Camper ${i}`,
      first_name: 'Camper',
      last_name: `${i}`,
      bunk_name: 'Elm',
      bunk_id: 1,
      preferred_name: null,
    }));
    getMock.mockResolvedValue({ data: { recent: [], results: many, bunks: [], zero_results_message: null } });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByTestId('sp-camper-row-1')).toBeInTheDocument();
    }, { timeout: 10000 });
    expect(screen.getByTestId('sp-camper-row-20')).toBeInTheDocument();
  });

  it('populates bunk dropdown from response and re-fetches when bunk selected', async () => {
    const elmOnly = {
      recent: [],
      results: [
        { id: 11, display_name: 'Jake Smith', first_name: 'Jake', last_name: 'Smith', bunk_name: 'Elm', bunk_id: 1, preferred_name: null },
      ],
      bunks: sampleBunks,
      zero_results_message: null,
    };
    getMock
      .mockResolvedValueOnce({ data: sampleData })   // initial load
      .mockResolvedValueOnce({ data: elmOnly });      // after bunk select

    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.queryByTestId('sp-picker-loading')).not.toBeInTheDocument();
      expect(screen.getByTestId('sp-bunk-select').querySelector('option[value="1"]')).toBeInTheDocument();
    });

    const bunkSelect = screen.getByTestId('sp-bunk-select');

    fireEvent.change(bunkSelect, { target: { value: '1' } });

    // Triggered a second API call with bunk_id param
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    expect(getMock).toHaveBeenLastCalledWith(
      '/api/v1/specialist/campers/',
      expect.objectContaining({ params: expect.objectContaining({ bunk_id: '1' }) }),
    );

    // Only Elm camper visible; Alice (Pine) gone
    await waitFor(() => expect(screen.getByTestId('sp-camper-row-11')).toBeInTheDocument());
    expect(screen.queryByTestId('sp-camper-row-12')).not.toBeInTheDocument();
  });

  it('shows clear button when bunk selected and hides Recent section', async () => {
    getMock.mockResolvedValue({ data: sampleData });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-bunk-select')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('sp-bunk-select'), { target: { value: '2' } });

    await waitFor(() => expect(screen.getByTestId('sp-bunk-clear')).toBeInTheDocument());
    // Recent section hidden when a bunk is selected
    expect(screen.queryByTestId('sp-picker-recent')).not.toBeInTheDocument();
  });
});
