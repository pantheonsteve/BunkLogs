import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SubjectTrendGrid from '../trends/SubjectTrendGrid';
import TrendCell from '../trends/TrendCell';
import { ratingColor } from '../colors';

function withRouter(ui) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

const PAYLOAD = {
  group: { id: 1, name: 'Bunk Maple', group_type: 'bunk' },
  template: {
    id: 5,
    name: 'Bunk Pulse',
    slug: 'bunk-pulse',
    primary_rating_key: 'overall',
    category_ratings_key: null,
    category_keys: [],
  },
  period: { start: '2026-06-01', end: '2026-06-03' },
  scale_min: 1,
  scale_max: 4,
  category_filter: null,
  subjects: [
    {
      person_id: 10,
      name: 'Sarah Levin',
      cells: [
        { date: '2026-06-01', rating: 4, reflection_id: 100, author_id: 7, author_name: 'Mike' },
        { date: '2026-06-02', rating: 1, reflection_id: 101, author_id: 7, author_name: 'Mike' },
        { date: '2026-06-03', rating: null, reflection_id: null, author_id: null, author_name: null },
      ],
    },
    {
      person_id: 11,
      name: 'Bobby Cohen',
      cells: [
        { date: '2026-06-01', rating: 3, reflection_id: 102, author_id: 7, author_name: 'Mike' },
        { date: '2026-06-02', rating: 3, reflection_id: 103, author_id: 7, author_name: 'Mike' },
        { date: '2026-06-03', rating: 4, reflection_id: 104, author_id: 7, author_name: 'Mike' },
      ],
    },
  ],
};

const PAYLOAD_WITH_CATEGORIES = {
  ...PAYLOAD,
  template: {
    id: 6,
    name: 'Pulse',
    slug: 'pulse',
    primary_rating_key: null,
    category_ratings_key: 'pulse',
    category_keys: ['morale', 'energy'],
  },
  scale_max: 5,
};


describe('TrendCell', () => {
  it('renders the rating value when present', () => {
    render(
      withRouter(
        <table>
          <tbody>
            <tr>
              <TrendCell
                cell={{ date: '2026-06-01', rating: 3, reflection_id: 1, author_name: 'Mike' }}
                scaleMax={4}
                subjectName="Sarah Levin"
              />
            </tr>
          </tbody>
        </table>,
      ),
    );
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('uses the correct color for each rating tier', () => {
    expect(ratingColor(1, 4)).toBe('#c0473a'); // red
    expect(ratingColor(4, 4)).toBe('#1b6e3f'); // dark green
    expect(ratingColor(5, 5)).toBe('#1b6e3f'); // dark green at scale-5
  });

  it('renders an aria-label with subject, date, rating, scale, and author', () => {
    render(
      withRouter(
        <table>
          <tbody>
            <tr>
              <TrendCell
                cell={{ date: '2026-06-14', rating: 3, reflection_id: 1, author_name: 'Counselor Mike' }}
                scaleMax={4}
                subjectName="Sarah Levin"
              />
            </tr>
          </tbody>
        </table>,
      ),
    );
    const labeled = screen.getByLabelText(
      /Sarah Levin.*Jun 14.*rating 3 of 4.*logged by Counselor Mike/i,
    );
    expect(labeled).toBeInTheDocument();
  });

  it('marks no-data cells as such', () => {
    render(
      withRouter(
        <table>
          <tbody>
            <tr>
              <TrendCell
                cell={{ date: '2026-06-14', rating: null }}
                scaleMax={4}
                subjectName="Sarah Levin"
              />
            </tr>
          </tbody>
        </table>,
      ),
    );
    expect(screen.getByLabelText(/Sarah Levin.*no reflection/i)).toBeInTheDocument();
  });

  it('renders the PrivacyChip lock overlay when the cell is filed privately', () => {
    render(
      withRouter(
        <table>
          <tbody>
            <tr>
              <TrendCell
                cell={{
                  date: '2026-06-14',
                  rating: 2,
                  reflection_id: 99,
                  author_name: 'Mike',
                  team_visibility: 'supervisors_only',
                }}
                scaleMax={4}
                subjectName="Sarah Levin"
              />
            </tr>
          </tbody>
        </table>,
      ),
    );
    expect(screen.getByTestId('privacy-chip')).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Sarah Levin.*filed privately/i),
    ).toBeInTheDocument();
  });

  it('does not render the PrivacyChip when team_visibility is "team"', () => {
    render(
      withRouter(
        <table>
          <tbody>
            <tr>
              <TrendCell
                cell={{
                  date: '2026-06-14',
                  rating: 4,
                  reflection_id: 99,
                  author_name: 'Mike',
                  team_visibility: 'team',
                }}
                scaleMax={4}
                subjectName="Sarah Levin"
              />
            </tr>
          </tbody>
        </table>,
      ),
    );
    expect(screen.queryByTestId('privacy-chip')).toBeNull();
  });
});


describe('SubjectTrendGrid', () => {
  it('renders one row per subject', () => {
    render(withRouter(<SubjectTrendGrid payload={PAYLOAD} />));
    expect(screen.getByText('Sarah Levin')).toBeInTheDocument();
    expect(screen.getByText('Bobby Cohen')).toBeInTheDocument();
  });

  it('renders the legend with the rating-scale label', () => {
    render(withRouter(<SubjectTrendGrid payload={PAYLOAD} />));
    expect(screen.getByText(/rating scale/i)).toBeInTheDocument();
    // "no reflection" legend entry
    expect(screen.getByText(/no reflection/i)).toBeInTheDocument();
  });

  it('does not render a category dropdown when template has no categories', () => {
    render(withRouter(<SubjectTrendGrid payload={PAYLOAD} />));
    expect(screen.queryByLabelText(/category/i)).not.toBeInTheDocument();
  });

  it('renders a category dropdown when category_keys present and fires onCategoryChange', () => {
    const onCategoryChange = vi.fn();
    render(
      withRouter(
        <SubjectTrendGrid
          payload={PAYLOAD_WITH_CATEGORIES}
          category=""
          onCategoryChange={onCategoryChange}
        />,
      ),
    );
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'morale' } });
    expect(onCategoryChange).toHaveBeenCalledWith('morale');
  });

  it('renders aria-labels for every cell in the grid', () => {
    render(withRouter(<SubjectTrendGrid payload={PAYLOAD} />));
    const rows = screen.getAllByLabelText(/Sarah Levin/i);
    // 3 cells for Sarah (date columns) plus the row link header.
    expect(rows.length).toBeGreaterThanOrEqual(3);
  });
});
