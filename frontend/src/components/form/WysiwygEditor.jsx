import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import Quill from 'quill';
import 'quill/dist/quill.snow.css';
import { uploadRichTextImage } from '../../api/richText';

const Delta = Quill.import('delta');

function normalizeHtml(html) {
  if (html == null || html === '') return '';
  return String(html);
}

function htmlMatches(a, b) {
  return normalizeHtml(a) === normalizeHtml(b);
}

const WysiwygEditor = forwardRef(({ onChange, value, readOnly = false, showToolbar = true }, ref) => {
  const editorRef = useRef(null);
  const quillRef = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useImperativeHandle(ref, () => ({
    getQuill: () => quillRef.current,
    setContent: (content) => {
      if (!quillRef.current) return;
      try {
        if (!content || String(content).trim() === '') {
          quillRef.current.setText('');
        } else if (content.includes('<') && content.includes('>')) {
          quillRef.current.root.innerHTML = content;
        } else {
          quillRef.current.setText(content);
        }
      } catch {
        quillRef.current.setText(content || '');
      }
    },
  }));

  useEffect(() => {
    if (!editorRef.current || quillRef.current) return;

    const toolbarOptions = [
      [{ header: [1, 2, false] }],
      ['bold', 'italic', 'underline'],
      [{ list: 'ordered' }, { list: 'bullet' }],
      [{ align: [] }],
      ['link', 'image'],
      ['clean'],
    ];

    quillRef.current = new Quill(editorRef.current, {
      modules: {
        toolbar: showToolbar ? toolbarOptions : false,
      },
      theme: 'snow',
      readOnly,
    });

    const quill = quillRef.current;

    // Upload a file to S3 and embed the returned URL. Never inline base64 --
    // that's what bloated the DB (multi-MB rows) before this change.
    const uploadAndInsert = async (file) => {
      if (!file || !file.type?.startsWith('image/')) return;
      const range = quill.getSelection(true);
      const index = range ? range.index : quill.getLength();
      try {
        const url = await uploadRichTextImage(file);
        quill.insertEmbed(index, 'image', url, 'user');
        quill.setSelection(index + 1, 0);
      } catch {
        // eslint-disable-next-line no-alert
        window.alert?.('Image upload failed. Please try again.');
      }
    };

    if (showToolbar) {
      const toolbar = quill.getModule('toolbar');
      toolbar?.addHandler('image', () => {
        const input = document.createElement('input');
        input.setAttribute('type', 'file');
        input.setAttribute('accept', 'image/*');
        input.onchange = () => uploadAndInsert(input.files?.[0]);
        input.click();
      });
    }

    // Pasted/dropped image files (e.g. screenshots) route through the uploader
    // instead of Quill's default base64 embedding.
    const handlePaste = (e) => {
      const files = Array.from(e.clipboardData?.files || []).filter((f) =>
        f.type?.startsWith('image/'),
      );
      if (files.length) {
        e.preventDefault();
        files.forEach(uploadAndInsert);
      }
    };
    const handleDrop = (e) => {
      const files = Array.from(e.dataTransfer?.files || []).filter((f) =>
        f.type?.startsWith('image/'),
      );
      if (files.length) {
        e.preventDefault();
        files.forEach(uploadAndInsert);
      }
    };
    quill.root.addEventListener('paste', handlePaste, true);
    quill.root.addEventListener('drop', handleDrop, true);

    // Pasting rich HTML that already contains base64 <img> (e.g. from a doc):
    // drop those inline images rather than storing the blob.
    quill.clipboard.addMatcher('IMG', (node, delta) => {
      const src = node.getAttribute?.('src') || '';
      return src.startsWith('data:') ? new Delta() : delta;
    });

    quillRef.current.on('text-change', (_delta, _oldDelta, source) => {
      if (source !== 'user' || !quillRef.current) return;
      const content = quillRef.current.root.innerHTML;
      onChangeRef.current?.(content);
    });

    // Flush the live editor content to the parent on blur (range === null).
    // Defense-in-depth so the submitted state always matches what the user
    // sees, even if an external effect briefly reverts the `value` prop while
    // the editor held focus (the value->editor sync below is skipped while
    // focused). Same-string updates are no-ops, so this can't loop.
    quillRef.current.on('selection-change', (range) => {
      if (range !== null || !quillRef.current) return;
      const content = quillRef.current.root.innerHTML;
      onChangeRef.current?.(content);
    });
  }, [readOnly, showToolbar]);

  useEffect(() => {
    if (!quillRef.current) return;
    quillRef.current.enable(!readOnly);
  }, [readOnly]);

  useEffect(() => {
    if (!quillRef.current || value === undefined) return;
    if (quillRef.current.hasFocus()) return;

    const currentContent = quillRef.current.root.innerHTML;
    if (htmlMatches(currentContent, value)) return;

    try {
      if (!value || String(value).trim() === '') {
        quillRef.current.setText('');
      } else if (value.includes('<') && value.includes('>')) {
        quillRef.current.root.innerHTML = value;
      } else {
        quillRef.current.setText(value);
      }
    } catch {
      quillRef.current.setText(value || '');
    }
  }, [value]);

  return (
    <div>
      <div ref={editorRef} style={{ height: '300px' }} />
    </div>
  );
});

WysiwygEditor.displayName = 'WysiwygEditor';

export default WysiwygEditor;
