import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import Quill from 'quill';
import 'quill/dist/quill.snow.css';

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
      ['link'],
      ['clean'],
    ];

    quillRef.current = new Quill(editorRef.current, {
      modules: {
        toolbar: showToolbar ? toolbarOptions : false,
      },
      theme: 'snow',
      readOnly,
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
