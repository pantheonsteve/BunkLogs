import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AudienceDisclosure from '../AudienceDisclosure';

describe('AudienceDisclosure', () => {
  it('renders all role labels', () => {
    render(
      <AudienceDisclosure audience={['Counselor', 'Unit Head', 'Admin']} />,
    );
    const labels = screen.getByTestId('audience-disclosure-labels');
    expect(labels).toHaveTextContent('Counselor, Unit Head, Admin');
    expect(screen.getByText(/Visible to:/i)).toBeInTheDocument();
  });

  it('updates when audience prop changes', () => {
    const { rerender } = render(
      <AudienceDisclosure audience={['Counselor']} />,
    );
    expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent('Counselor');

    rerender(<AudienceDisclosure audience={['Camper Care', 'Admin']} />);
    expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent(
      'Camper Care, Admin',
    );
  });

  it('renders context hint when provided', () => {
    render(
      <AudienceDisclosure
        audience={['Counselor']}
        contextHint="Spanish originals are kept on file."
      />,
    );
    expect(screen.getByText('Spanish originals are kept on file.')).toBeInTheDocument();
  });

  it('returns null for empty audience', () => {
    const { container } = render(<AudienceDisclosure audience={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
