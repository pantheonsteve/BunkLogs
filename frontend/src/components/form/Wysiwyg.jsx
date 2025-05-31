import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import Quill from 'quill';
import 'quill/dist/quill.snow.css';

const Wysiwyg = forwardRef(({ onChange, value, readOnly = false, showToolbar = true }, ref) => {
    const editorRef = useRef(null);
    const quillRef = useRef(null);

    console.log('=== Wysiwyg: Component rendered ===');
    console.log('Props received:', { value, readOnly, showToolbar });
    console.log('Value type and length:', typeof value, value ? value.length : 0);

    // Expose quill instance to parent
    useImperativeHandle(ref, () => ({
        getQuill: () => quillRef.current,
        setContent: (content) => {
            console.log('=== Wysiwyg: setContent called ===', content);
            if (quillRef.current) {
                try {
                    if (!content || content.trim() === '') {
                        console.log('Setting empty content');
                        quillRef.current.setText('');
                    } else if (content.includes('<') && content.includes('>')) {
                        console.log('Setting HTML content via setContent');
                        // HTML content - use dangerouslyPasteHTML for better reliability
                        quillRef.current.root.innerHTML = content;
                    } else {
                        console.log('Setting plain text via setContent');
                        // Plain text
                        quillRef.current.setText(content);
                    }
                    console.log('Content after setContent:', quillRef.current.root.innerHTML);
                } catch (error) {
                    console.error('Error setting Wysiwyg content:', error);
                    quillRef.current.setText(content || '');
                }
            } else {
                console.warn('Quill instance not ready for setContent');
            }
        }
    }));

    useEffect(() => {
        if (editorRef.current && !quillRef.current) {
            const toolbarOptions = [
                [{ 'header': [1, 2, false] }],
                ['bold', 'italic', 'underline'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                [{ 'align': [] }],
                ['link'],
                ['clean']
            ];

            quillRef.current = new Quill(editorRef.current, {
                modules: {
                    toolbar: showToolbar ? toolbarOptions : false
                },
                theme: 'snow',
                readOnly: readOnly
            });

            quillRef.current.on('text-change', function(delta, oldDelta, source) {
                if (source === 'user') {
                    const content = quillRef.current.root.innerHTML;
                    console.log('WYSIWYG content changed:', content);
                    if (onChange) {
                        onChange(content);
                    }
                }
            });

            // Set initial content if provided
            if (value) {
                console.log('=== Wysiwyg: Setting initial content ===');
                console.log('Initial value:', value);
                setTimeout(() => {
                    if (quillRef.current) {
                        try {
                            console.log('=== Wysiwyg: Applying initial content ===');
                            if (value.includes('<') && value.includes('>')) {
                                console.log('Setting as HTML content');
                                // Use direct innerHTML assignment for better HTML preservation
                                quillRef.current.root.innerHTML = value;
                            } else {
                                console.log('Setting as plain text');
                                quillRef.current.setText(value);
                            }
                            console.log('Content after setting:', quillRef.current.root.innerHTML);
                        } catch (error) {
                            console.error('Error setting initial content:', error);
                            quillRef.current.setText(value);
                        }
                    }
                }, 100);
            }
        }

        // Update readonly state
        if (quillRef.current) {
            quillRef.current.enable(!readOnly);
        }
    }, [onChange, readOnly, showToolbar, value]); // Added value to dependencies

    // Update content when value prop changes
    useEffect(() => {
        console.log('WYSIWYG useEffect triggered, value:', value);
        if (quillRef.current && value !== undefined) {
            const currentContent = quillRef.current.root.innerHTML;
            console.log('Current content vs new value:', { currentContent, newValue: value });
            if (currentContent !== value) {
                try {
                    console.log('Setting new content in Wysiwyg...');
                    quillRef.current.disable(); // Prevent triggering onChange
                    if (!value || value.trim() === '') {
                        quillRef.current.setText('');
                        console.log('Set empty text');
                    } else if (value.includes('<') && value.includes('>')) {
                        // Use direct innerHTML assignment for better HTML preservation
                        quillRef.current.root.innerHTML = value;
                        console.log('Set HTML content:', value);
                    } else {
                        quillRef.current.setText(value);
                        console.log('Set plain text:', value);
                    }
                } catch (error) {
                    console.error('Error updating content:', error);
                    quillRef.current.setText(value || '');
                } finally {
                    if (!readOnly) {
                        quillRef.current.enable(); // Re-enable
                    }
                }
            }
        }
    }, [value, readOnly]); // Added readOnly to dependencies

    return (
        <div>
            <div ref={editorRef} style={{ height: '300px' }}></div>
        </div>
    );
});

export default Wysiwyg;