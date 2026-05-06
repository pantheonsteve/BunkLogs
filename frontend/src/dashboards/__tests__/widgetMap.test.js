import { describe, it, expect } from 'vitest';
import {
  resolveWidgetName,
  partitionFields,
  ROLE_WIDGET_MAP,
  TYPE_WIDGET_MAP,
} from '../widgetMap';

describe('resolveWidgetName', () => {
  it('returns correct widget for primary_rating role', () => {
    expect(resolveWidgetName({ type: 'single_rating', dashboard_role: 'primary_rating' }))
      .toBe('RatingHeadlineWidget');
  });

  it('returns correct widget for category_ratings role', () => {
    expect(resolveWidgetName({ type: 'rating_group', dashboard_role: 'category_ratings' }))
      .toBe('CategoryRadarWidget');
  });

  it('returns correct widget for wins role', () => {
    expect(resolveWidgetName({ type: 'text_list', dashboard_role: 'wins' }))
      .toBe('HighlightFeedWidget');
  });

  it('returns correct widget for improvements role', () => {
    expect(resolveWidgetName({ type: 'text_list', dashboard_role: 'improvements' }))
      .toBe('ImprovementFeedWidget');
  });

  it('returns correct widget for open_concern role', () => {
    expect(resolveWidgetName({ type: 'textarea', dashboard_role: 'open_concern' }))
      .toBe('ConcernQueueWidget');
  });

  it('returns generic widget for untagged text field', () => {
    expect(resolveWidgetName({ type: 'text', dashboard_role: null }))
      .toBe('TextResponseListWidget');
  });

  it('returns generic widget for untagged textarea field', () => {
    expect(resolveWidgetName({ type: 'textarea', dashboard_role: null }))
      .toBe('TextResponseListWidget');
  });

  it('returns ItemCloudWidget for untagged text_list', () => {
    expect(resolveWidgetName({ type: 'text_list', dashboard_role: null }))
      .toBe('ItemCloudWidget');
  });

  it('returns RatingDistributionWidget for untagged single_rating', () => {
    expect(resolveWidgetName({ type: 'single_rating', dashboard_role: null }))
      .toBe('RatingDistributionWidget');
  });

  it('returns RatingTableWidget for untagged rating_group', () => {
    expect(resolveWidgetName({ type: 'rating_group', dashboard_role: null }))
      .toBe('RatingTableWidget');
  });

  it('returns ChoiceBarChartWidget for single_choice', () => {
    expect(resolveWidgetName({ type: 'single_choice' })).toBe('ChoiceBarChartWidget');
  });

  it('returns ChoiceBarChartWidget for multiple_choice', () => {
    expect(resolveWidgetName({ type: 'multiple_choice' })).toBe('ChoiceBarChartWidget');
  });

  it('returns YesNoBreakdownWidget for yes_no', () => {
    expect(resolveWidgetName({ type: 'yes_no' })).toBe('YesNoBreakdownWidget');
  });

  it('returns null for section_header', () => {
    expect(resolveWidgetName({ type: 'section_header' })).toBeNull();
  });

  it('returns null for instructions', () => {
    expect(resolveWidgetName({ type: 'instructions' })).toBeNull();
  });

  it('returns null for null field', () => {
    expect(resolveWidgetName(null)).toBeNull();
  });

  it('role-tagged field uses role widget over type widget', () => {
    const result = resolveWidgetName({ type: 'single_rating', dashboard_role: 'primary_rating' });
    expect(result).toBe(ROLE_WIDGET_MAP.primary_rating);
    expect(result).not.toBe(TYPE_WIDGET_MAP.single_rating);
  });
});

describe('partitionFields', () => {
  const fields = [
    { key: 'overall', type: 'single_rating', dashboard_role: 'primary_rating' },
    { key: 'pulse', type: 'rating_group', dashboard_role: 'category_ratings' },
    { key: 'wins', type: 'text_list', dashboard_role: 'wins' },
    { key: 'extra_text', type: 'text', dashboard_role: null },
    { key: 'a_header', type: 'section_header', dashboard_role: null },
    { key: 'yn', type: 'yes_no', dashboard_role: null },
  ];

  it('puts role-tagged fields in tagged array', () => {
    const { tagged } = partitionFields(fields);
    expect(tagged.map((f) => f.key)).toEqual(['overall', 'pulse', 'wins']);
  });

  it('puts untagged non-meta fields in generic array', () => {
    const { generic } = partitionFields(fields);
    const keys = generic.map((f) => f.key);
    expect(keys).toContain('extra_text');
    expect(keys).toContain('yn');
  });

  it('excludes meta field types', () => {
    const { tagged, generic } = partitionFields(fields);
    const all = [...tagged, ...generic].map((f) => f.key);
    expect(all).not.toContain('a_header');
  });

  it('handles empty/null input', () => {
    expect(partitionFields(null)).toEqual({ tagged: [], generic: [] });
    expect(partitionFields([])).toEqual({ tagged: [], generic: [] });
  });
});
