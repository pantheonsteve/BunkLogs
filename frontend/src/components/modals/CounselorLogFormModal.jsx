import { useRef, useEffect } from 'react';
import Transition from '../../utils/Transition';

function CounselorLogFormModal({
  children,
  id,
  title,
  modalOpen,
  setModalOpen,
  formSubmitted = false  // New prop to track form submission status
}) {

  const modalContent = useRef(null);

  // close on click outside
  useEffect(() => {
    const clickHandler = ({ target }) => {
      console.log('[CounselorLogFormModal] Click detected, modalOpen:', modalOpen, 'target:', target);
      if (!modalOpen || modalContent.current?.contains(target)) {
        console.log('[CounselorLogFormModal] Click ignored - modal closed or click inside modal');
        return;
      }
      console.log('[CounselorLogFormModal] Click outside modal - closing modal');
      setModalOpen(false);
    };
    document.addEventListener('click', clickHandler);
    return () => document.removeEventListener('click', clickHandler);
  }, [modalOpen, setModalOpen]);

  // close if the esc key is pressed
  useEffect(() => {
    const keyHandler = ({ keyCode }) => {
      if (!modalOpen || keyCode !== 27) return;
      setModalOpen(false);
    };
    document.addEventListener('keydown', keyHandler);
    return () => document.removeEventListener('keydown', keyHandler);
  }, [modalOpen, setModalOpen]);

  return (
    <>
      {/* Modal backdrop */}
      {modalOpen && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-30 z-50 transition-opacity" aria-hidden="true" />
      )}
      {/* Modal dialog */}
      {modalOpen && (
        <div
          id={id}
          className="fixed inset-0 z-50 overflow-hidden flex items-start top-20 mb-4 justify-center px-4 sm:px-6"
          role="dialog"
          aria-modal="true"
        >
          <div ref={modalContent} className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-auto max-w-lg w-full max-h-full">
            {/* Modal header */}
            <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-700/60">
            <div className="flex justify-between items-center">
              <div className="font-semibold text-gray-800 dark:text-gray-100">{title}</div>
              <button className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400" onClick={() => setModalOpen(false)}>
                <div className="sr-only">Close</div>
                <svg className="w-4 h-4 fill-current">
                  <path d="M7.95 6.536l4.242-4.243a1 1 0 111.415 1.414L9.364 7.95l4.243 4.242a1 1 0 11-1.415 1.415L7.95 9.364l-4.243 4.243a1 1 0 01-1.414-1.415L6.536 7.95 2.293 3.707a1 1 0 011.414-1.414L7.95 6.536z" />
                </svg>
              </button>
            </div>            </div>
          {children}     
        </div>        
      </div>
      )}
    </>
  );
}

export default CounselorLogFormModal;
