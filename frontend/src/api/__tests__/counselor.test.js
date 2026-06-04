import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  CAMPER_REFLECTION_AUDIENCE,
  COUNSELOR_SELF_REFLECTION_AUDIENCE,
  MAINTENANCE_CATEGORIES,
  MAINTENANCE_URGENCY_CHOICES,
  createCamperCareRequest,
  createCamperReflection,
  createMaintenanceTicket,
  createSelfReflection,
  fetchCamperCareItemSuggestions,
  fetchCamperReflections,
  fetchCounselorDashboard,
  fetchCounselorRequests,
  fetchReflection,
  fetchSelfReflectionHistory,
  fetchTemplateById,
  newClientSubmissionId,
  patchCamperReflection,
  patchSelfReflection,
  uploadMaintenanceTicketPhoto,
} from '../counselor';

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock('../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
  },
}));

describe('counselor API helpers', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it('exports the canonical camper-reflection audience set', () => {
    expect(CAMPER_REFLECTION_AUDIENCE).toEqual([
      'Admin',
      'Camper Care',
      'Counselor',
      'Leadership Team',
      'Unit Head',
    ]);
  });

  it('newClientSubmissionId returns a UUID-shaped string', () => {
    const id = newClientSubmissionId();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(newClientSubmissionId()).not.toBe(id);
  });

  it('fetchCounselorDashboard hits the v1 endpoint with optional nocache param', async () => {
    getMock.mockResolvedValue({ data: { ok: true } });
    await fetchCounselorDashboard();
    expect(getMock.mock.calls[0][0]).toBe('/api/v1/counselor/dashboard/');
    expect(getMock.mock.calls[0][1]).toEqual({ params: {} });

    await fetchCounselorDashboard({ noCache: true });
    expect(getMock.mock.calls[1][1]).toEqual({ params: { nocache: '1' } });

    await fetchCounselorDashboard({ date: '2026-07-01' });
    expect(getMock.mock.calls[2][1]).toEqual({ params: { date: '2026-07-01' } });
  });

  it('fetchCamperReflections forwards the date param', async () => {
    getMock.mockResolvedValue({ data: {} });
    await fetchCamperReflections({ date: '2026-07-04' });
    expect(getMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/camper-reflections/',
      { params: { date: '2026-07-04' } },
    ]);
  });

  it('createCamperReflection sends the camel→snake payload', async () => {
    postMock.mockResolvedValue({ data: { id: 1 }, status: 201 });
    const result = await createCamperReflection({
      subjectId: 7,
      assignmentGroupId: 100,
      answers: { note: 'hi' },
      language: 'es',
      teamVisibility: 'supervisors_only',
      clientSubmissionId: '11111111-1111-4111-8111-111111111111',
    });
    expect(postMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/camper-reflections/',
      {
        subject_id: 7,
        assignment_group_id: 100,
        answers: { note: 'hi' },
        language: 'es',
        team_visibility: 'supervisors_only',
        client_submission_id: '11111111-1111-4111-8111-111111111111',
      },
    ]);
    expect(result.status).toBe(201);
  });

  it('patchCamperReflection omits undefined fields', async () => {
    patchMock.mockResolvedValue({ data: { id: 1 } });
    await patchCamperReflection(99, { answers: { note: 'edited' } });
    expect(patchMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/camper-reflections/99/',
      { answers: { note: 'edited' } },
    ]);
  });

  it('fetchTemplateById uses the templates viewset', async () => {
    getMock.mockResolvedValue({ data: { id: 7 } });
    await fetchTemplateById(7);
    expect(getMock.mock.calls[0][0]).toBe('/api/v1/templates/7/');
  });

  it('fetchReflection uses the reflection viewset', async () => {
    getMock.mockResolvedValue({ data: { id: 1 } });
    await fetchReflection(42);
    expect(getMock.mock.calls[0][0]).toBe('/api/v1/reflections/42/');
  });

  it('exports the canonical self-reflection audience set', () => {
    expect(COUNSELOR_SELF_REFLECTION_AUDIENCE).toEqual([
      'Admin',
      'Counselor',
      'Leadership Team',
      'Unit Head',
    ]);
  });

  it('createSelfReflection day-off shortcut omits answers', async () => {
    postMock.mockResolvedValue({ data: { id: 1 }, status: 201 });
    await createSelfReflection({
      dayOff: true,
      language: 'en',
      clientSubmissionId: '11111111-1111-4111-8111-111111111111',
    });
    expect(postMock.mock.calls[0][0]).toBe('/api/v1/counselor/self-reflection/');
    const body = postMock.mock.calls[0][1];
    expect(body).toEqual({
      day_off: true,
      language: 'en',
      client_submission_id: '11111111-1111-4111-8111-111111111111',
    });
    expect(body).not.toHaveProperty('answers');
  });

  it('createSelfReflection sends the full answers payload otherwise', async () => {
    postMock.mockResolvedValue({ data: { id: 2 }, status: 201 });
    await createSelfReflection({
      dayOff: false,
      answers: { overall_day: 4 },
      language: 'es',
      clientSubmissionId: '22222222-2222-4222-8222-222222222222',
    });
    const body = postMock.mock.calls[0][1];
    expect(body).toEqual({
      day_off: false,
      language: 'es',
      client_submission_id: '22222222-2222-4222-8222-222222222222',
      answers: { overall_day: 4 },
    });
  });

  it('patchSelfReflection omits undefined fields', async () => {
    patchMock.mockResolvedValue({ data: { id: 9 } });
    await patchSelfReflection(9, { dayOff: true });
    expect(patchMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/self-reflection/9/',
      { day_off: true },
    ]);
  });

  it('fetchSelfReflectionHistory forwards pagination params', async () => {
    getMock.mockResolvedValue({ data: { results: [] } });
    await fetchSelfReflectionHistory({ page: 3, pageSize: 30 });
    expect(getMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/self-reflection/history/',
      { params: { page: 3, page_size: 30 } },
    ]);
  });

  it('fetchCounselorRequests defaults status=open', async () => {
    getMock.mockResolvedValue({ data: { requests: [] } });
    await fetchCounselorRequests();
    expect(getMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/requests/',
      { params: { status: 'open' } },
    ]);
  });

  it('fetchCounselorRequests forwards status filter', async () => {
    getMock.mockResolvedValue({ data: { requests: [] } });
    await fetchCounselorRequests({ status: 'all' });
    expect(getMock.mock.calls[0][1].params.status).toBe('all');
  });

  it('fetchCamperCareItemSuggestions calls the suggestions endpoint', async () => {
    getMock.mockResolvedValue({ data: { suggestions: [] } });
    await fetchCamperCareItemSuggestions();
    expect(getMock.mock.calls[0][0]).toBe(
      '/api/v1/counselor/camper-care-item-suggestions/',
    );
  });

  it('createCamperCareRequest sends the trimmed payload', async () => {
    postMock.mockResolvedValue({ data: { id: 'order-1' }, status: 201 });
    await createCamperCareRequest({
      subjectId: 42,
      item: 'Toothbrush',
      itemNote: 'purple',
      description: 'after lights out',
      clientSubmissionId: '33333333-3333-4333-8333-333333333333',
    });
    expect(postMock.mock.calls[0][0]).toBe('/api/v1/counselor/camper-care-requests/');
    expect(postMock.mock.calls[0][1]).toEqual({
      subject_id: 42,
      item: 'Toothbrush',
      item_note: 'purple',
      description: 'after lights out',
      client_submission_id: '33333333-3333-4333-8333-333333333333',
    });
  });

  it('createCamperCareRequest omits subject_id when null/undefined', async () => {
    postMock.mockResolvedValue({ data: { id: 'order-2' }, status: 201 });
    await createCamperCareRequest({
      subjectId: null,
      item: 'Bug spray',
      clientSubmissionId: '44444444-4444-4444-8444-444444444444',
    });
    const body = postMock.mock.calls[0][1];
    expect(body).not.toHaveProperty('subject_id');
    expect(body.item).toBe('Bug spray');
  });

  it('createMaintenanceTicket builds a multipart FormData with photos', async () => {
    postMock.mockResolvedValue({ data: { id: 'mt-1' }, status: 201 });
    const photo1 = new File(['fake-image-1'], 'photo1.jpg', { type: 'image/jpeg' });
    const photo2 = new File(['fake-image-2'], 'photo2.jpg', { type: 'image/jpeg' });
    await createMaintenanceTicket({
      location: 'Bunk Pine',
      category: 'leak',
      description: 'under sink',
      urgency: 'urgent',
      urgentReason: 'flooding',
      photos: [photo1, photo2],
      clientSubmissionId: '55555555-5555-4555-8555-555555555555',
    });
    expect(postMock.mock.calls[0][0]).toBe('/api/v1/counselor/maintenance-tickets/');
    const body = postMock.mock.calls[0][1];
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('location')).toBe('Bunk Pine');
    expect(body.get('category')).toBe('leak');
    expect(body.get('urgency')).toBe('urgent');
    expect(body.get('urgent_reason')).toBe('flooding');
    expect(body.get('client_submission_id')).toBe(
      '55555555-5555-4555-8555-555555555555',
    );
    expect(body.getAll('photos')).toHaveLength(2);

    // ``Content-Type: undefined`` so the browser sets the multipart boundary.
    expect(postMock.mock.calls[0][2]).toEqual({
      headers: { 'Content-Type': undefined },
    });
  });

  it('createMaintenanceTicket skips urgent_reason when urgency is normal', async () => {
    postMock.mockResolvedValue({ data: { id: 'mt-2' }, status: 201 });
    await createMaintenanceTicket({
      location: 'Dining hall',
      category: 'broken_light',
      photos: [],
      urgency: 'normal',
      urgentReason: 'should be ignored',
      clientSubmissionId: '66666666-6666-4666-8666-666666666666',
    });
    const body = postMock.mock.calls[0][1];
    expect(body.get('urgent_reason')).toBeNull();
    expect(body.getAll('photos')).toHaveLength(0);
  });

  it('uploadMaintenanceTicketPhoto posts to the follow-up endpoint', async () => {
    postMock.mockResolvedValue({ data: { id: 'photo-1' } });
    const photo = new File(['data'], 'extra.jpg', { type: 'image/jpeg' });
    await uploadMaintenanceTicketPhoto('abc-123', {
      image: photo,
      caption: 'cracked',
    });
    expect(postMock.mock.calls[0][0]).toBe(
      '/api/v1/counselor/maintenance-tickets/abc-123/photos/',
    );
    const body = postMock.mock.calls[0][1];
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('caption')).toBe('cracked');
    expect(body.get('image')).toBeInstanceOf(File);
  });

  it('exports stable maintenance categories + urgencies', () => {
    expect(MAINTENANCE_CATEGORIES.map((c) => c.value)).toEqual([
      'plumbing',
      'broken_light',
      'pest',
      'leak',
      'other',
    ]);
    expect(MAINTENANCE_URGENCY_CHOICES.map((u) => u.value)).toEqual([
      'normal',
      'urgent',
    ]);
  });
});
