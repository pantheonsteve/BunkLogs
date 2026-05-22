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

const sampleData = {
  recent: [
    { id: 10, display_name: 'Recent Cam', first_name: 'Recent', last_name: 'Cam', bunk_name: 'Oak', preferred_name: null },
  ],
  results: [
    { id: 11, display_name: 'Jake Smith', first_name: 'Jake', last_name: 'Smith', bunk_name: 'Elm', preferred_name: null },
    { id: 12, display_name: 'Alice Johnson', first_name: 'Alice', last_name: 'Johnson', bunk_name: 'Pine', preferred_name: null },
  ],
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
      preferred_name: null,
    }));
    getMock.mockResolvedValue({ data: { recent: [], results: many, zero_results_message: null } });
    render(<MemoryRouter><CamperPicker onSelect={vi.fn()} /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByTestId('sp-camper-row-1')).toBeInTheDocument();
    }, { timeout: 10000 });
    expect(screen.getByTestId('sp-camper-row-20')).toBeInTheDocument();
  });
});
