import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import GroupTypeIcon from '../GroupTypeIcon';
import { GROUP_TYPE_LABELS } from '../../pages/admin/groups/groupTypes';

describe('GroupTypeIcon', () => {
  it.each(Object.entries(GROUP_TYPE_LABELS))(
    'marks %s as %s',
    (type, label) => {
      render(<GroupTypeIcon type={type} />);
      expect(screen.getByRole('img', { name: label })).toBeInTheDocument();
    },
  );

  it('renders nothing for a type with no mark', () => {
    const { container } = render(<GroupTypeIcon type="unknown" />);
    expect(container).toBeEmptyDOMElement();
  });
});
