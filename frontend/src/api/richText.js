/**
 * Rich-text editor image uploads.
 *
 * The Quill editor uploads images to `/api/v1/rich-text-images/` (multipart)
 * and embeds the returned URL as an `<img src>` instead of base64. Keeping the
 * bytes out of the stored HTML avoids the multi-MB rows that used to bloat the
 * DB and break `pg_dump`.
 */

import api from '../api';

export async function uploadRichTextImage(file) {
  const form = new FormData();
  form.append('image', file);
  const { data } = await api.post('/api/v1/rich-text-images/', form, {
    headers: { 'Content-Type': undefined },
  });
  return data.url;
}
