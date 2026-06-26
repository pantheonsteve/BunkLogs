import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Boxes,
  Plus,
  Pencil,
  Trash2,
  Upload,
  Download,
  BarChart3,
  Layers,
  Tag,
  Package,
  Search,
  ChevronUp,
  ChevronDown,
  X,
} from 'lucide-react';

import {
  fetchCatalogTree,
  createCatalogStore,
  patchCatalogStore,
  deleteCatalogStore,
  createCatalogRequestType,
  patchCatalogRequestType,
  deleteCatalogRequestType,
  createCatalogItem,
  patchCatalogItem,
  deleteCatalogItem,
  importCatalogCsv,
  downloadCatalogTemplate,
} from '../../../api/admin';
import Button from '../../../components/ui/Button';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import Toast, { useToast } from '../../../components/ui/Toast';

/**
 * Catalog management UI (/admin/catalog). Lets admins configure the
 * Store -> RequestType -> CatalogItem tree that powers the Maintenance and
 * Camper Care request dropdowns, plus bulk CSV import. Wired behind
 * AdminRoute.
 */

const FULFILLING_ROLES = [
  { value: 'camper_care', label: 'Camper Care' },
  { value: 'maintenance', label: 'Maintenance' },
];

function inputClass() {
  return 'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function errMessage(e, fallback) {
  const body = e?.response?.data;
  if (typeof body === 'string') return body;
  return body?.detail || fallback;
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function Modal({ title, onClose, children }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const node = panelRef.current;
    if (!node) return undefined;
    // Autofocus the first input/select, falling back to a button.
    const firstField = node.querySelector('input, select, textarea');
    (firstField || node.querySelector('button'))?.focus();

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const focusable = Array.from(
        node.querySelectorAll('input, select, textarea, button, [href], [tabindex]:not([tabindex="-1"])'),
      ).filter((el) => !el.disabled && el.offsetParent !== null);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => document.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
            <X size={18} />
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

function ConfirmModal({ label, busy, onCancel, onConfirm }) {
  return (
    <Modal title="Confirm delete" onClose={onCancel}>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        Delete <span className="font-semibold text-gray-900 dark:text-white">“{label}”</span>?
        This cannot be undone.
      </p>
      <div className="flex justify-end gap-2 pt-4">
        <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
        <Button variant="danger" onClick={onConfirm} disabled={busy} data-testid="confirm-delete">
          {busy ? 'Deleting…' : 'Delete'}
        </Button>
      </div>
    </Modal>
  );
}

function StoreModal({ initial, busy, onClose, onSubmit }) {
  const [form, setForm] = useState(
    initial || { name: '', fulfilling_role: 'camper_care', labels: {}, is_active: true, sort_order: 0 },
  );
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <Modal title={initial?.id ? 'Edit store' : 'New store'} onClose={onClose}>
      <form
        onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}
        className="space-y-3"
      >
        <Field label="Name *">
          <input className={inputClass()} required value={form.name}
            onChange={(e) => update('name', e.target.value)} data-testid="store-name" />
        </Field>
        <Field label="Spanish label (optional)">
          <input className={inputClass()} value={form.labels?.es || ''}
            onChange={(e) => update('labels', { ...form.labels, es: e.target.value })} />
        </Field>
        <Field label="Fulfilling team *">
          <select className={inputClass()} value={form.fulfilling_role}
            onChange={(e) => update('fulfilling_role', e.target.value)}>
            {FULFILLING_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Sort order">
            <input type="number" className={inputClass()} value={form.sort_order ?? 0}
              onChange={(e) => update('sort_order', Number(e.target.value))} />
          </Field>
          <label className="flex items-center gap-2 mt-6 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" checked={!!form.is_active}
              onChange={(e) => update('is_active', e.target.checked)} />
            Active
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" disabled={busy} data-testid="store-submit">{busy ? 'Saving…' : 'Save'}</Button>
        </div>
      </form>
    </Modal>
  );
}

function TypeModal({ initial, busy, onClose, onSubmit }) {
  const [form, setForm] = useState(initial || { name: '', labels: {}, is_active: true, sort_order: 0 });
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <Modal title={initial?.id ? 'Edit request type' : 'New request type'} onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(form); }} className="space-y-3">
        <Field label="Name *">
          <input className={inputClass()} required value={form.name}
            onChange={(e) => update('name', e.target.value)} data-testid="type-name" />
        </Field>
        <Field label="Spanish label (optional)">
          <input className={inputClass()} value={form.labels?.es || ''}
            onChange={(e) => update('labels', { ...form.labels, es: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Sort order">
            <input type="number" className={inputClass()} value={form.sort_order ?? 0}
              onChange={(e) => update('sort_order', Number(e.target.value))} />
          </Field>
          <label className="flex items-center gap-2 mt-6 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" checked={!!form.is_active}
              onChange={(e) => update('is_active', e.target.checked)} />
            Active
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" disabled={busy} data-testid="type-submit">{busy ? 'Saving…' : 'Save'}</Button>
        </div>
      </form>
    </Modal>
  );
}

function ItemModal({ initial, busy, onClose, onSubmit }) {
  const [form, setForm] = useState(
    initial || { name: '', labels: {}, track_quantity: true, unit: '', is_active: true, sort_order: 0 },
  );
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <Modal title={initial?.id ? 'Edit item' : 'New item'} onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(form); }} className="space-y-3">
        <Field label="Name *">
          <input className={inputClass()} required value={form.name}
            onChange={(e) => update('name', e.target.value)} data-testid="item-name" />
        </Field>
        <Field label="Spanish label (optional)">
          <input className={inputClass()} value={form.labels?.es || ''}
            onChange={(e) => update('labels', { ...form.labels, es: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Unit (optional)">
            <input className={inputClass()} value={form.unit || ''} placeholder="roll, bottle…"
              onChange={(e) => update('unit', e.target.value)} />
          </Field>
          <Field label="Sort order">
            <input type="number" className={inputClass()} value={form.sort_order ?? 0}
              onChange={(e) => update('sort_order', Number(e.target.value))} />
          </Field>
        </div>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" checked={!!form.track_quantity}
              onChange={(e) => update('track_quantity', e.target.checked)} data-testid="item-track-qty" />
            Track quantity (consumable)
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" checked={!!form.is_active}
              onChange={(e) => update('is_active', e.target.checked)} />
            Active
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" disabled={busy} data-testid="item-submit">{busy ? 'Saving…' : 'Save'}</Button>
        </div>
      </form>
    </Modal>
  );
}

function ImportPanel({ onDone, showToast }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [deactivate, setDeactivate] = useState(false);
  const [busy, setBusy] = useState(false);

  const runPreview = async (f) => {
    setBusy(true);
    setPreview(null);
    try {
      const res = await importCatalogCsv(f, { mode: 'preview' });
      setPreview(res);
    } catch (e) {
      setPreview(e?.response?.data || { errors: ['Preview failed.'], valid: false });
    } finally {
      setBusy(false);
    }
  };

  const runCommit = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const res = await importCatalogCsv(file, { mode: 'commit', deactivateMissing: deactivate });
      const s = res?.summary || {};
      showToast(
        `Imported: +${s.items_created || 0} new, ${s.items_updated || 0} updated`
        + (s.items_deactivated ? `, ${s.items_deactivated} deactivated` : ''),
      );
      setFile(null);
      setPreview(null);
      onDone();
    } catch (e) {
      showToast(errMessage(e, 'Import failed.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      data-testid="catalog-import-panel"
      className="mb-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5"
    >
      <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Bulk CSV import</h2>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        One row per item. Stores and request types are created if missing.
        Columns: store, fulfilling_role, request_type, item_name, label_es,
        track_quantity, unit, sort_order, is_active.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv,text/csv"
          data-testid="catalog-csv-input"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            setFile(f);
            if (f) runPreview(f);
          }}
          className="text-sm text-gray-700 dark:text-gray-300"
        />
        <Button variant="secondary" onClick={() => downloadCatalogTemplate()}>
          <Download size={14} /> Template
        </Button>
      </div>

      {preview && (
        <div className="mt-4 text-sm">
          {preview.valid ? (
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-3">
              <p className="text-green-800 dark:text-green-300">
                {preview.row_count} valid row(s) ready to import.
              </p>
              <label className="flex items-center gap-2 mt-2 text-xs text-gray-700 dark:text-gray-300">
                <input type="checkbox" checked={deactivate}
                  onChange={(e) => setDeactivate(e.target.checked)} />
                Deactivate items not present in this file (under touched request types)
              </label>
              <div className="mt-3">
                <Button onClick={runCommit} disabled={busy} data-testid="catalog-import-commit">
                  {busy ? 'Importing…' : 'Commit import'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3">
              <p className="font-medium text-red-800 dark:text-red-300 mb-1">
                {(preview.errors || []).length} error(s) — fix and re-upload:
              </p>
              <ul className="list-disc list-inside text-xs text-red-700 dark:text-red-300 max-h-40 overflow-auto">
                {(preview.errors || []).map((err) => <li key={err}>{err}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Badge({ children, tone = 'gray' }) {
  const tones = {
    gray: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    green: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    indigo: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  };
  return <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

function ReorderControls({ canUp, canDown, onUp, onDown, disabled, label, compact = false }) {
  const size = compact ? 11 : 13;
  const btn = 'text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-25 disabled:hover:text-gray-400';
  return (
    <span className={`inline-flex flex-col -space-y-1 ${compact ? 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity' : ''}`}>
      <button type="button" className={btn} disabled={disabled || !canUp} aria-label={`Move ${label} up`} onClick={onUp}>
        <ChevronUp size={size} />
      </button>
      <button type="button" className={btn} disabled={disabled || !canDown} aria-label={`Move ${label} down`} onClick={onDown}>
        <ChevronDown size={size} />
      </button>
    </span>
  );
}

function StatCard({ icon: Icon, label, value, iconClass, onClick, active = false, testId }) {
  const base = 'flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors';
  const stateCls = active
    ? 'border-indigo-400 dark:border-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-900 bg-indigo-50/60 dark:bg-indigo-900/20'
    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900';
  const interactive = onClick ? 'hover:border-gray-300 dark:hover:border-gray-600 cursor-pointer' : '';
  const inner = (
    <>
      <span className={`inline-flex items-center justify-center w-9 h-9 rounded-lg ${iconClass}`}>
        <Icon size={18} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xl font-bold leading-tight text-gray-900 dark:text-white">{value}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{label}</p>
      </div>
    </>
  );
  if (!onClick) {
    return <div className={`${base} ${stateCls}`}>{inner}</div>;
  }
  return (
    <button type="button" onClick={onClick} aria-pressed={active} data-testid={testId} className={`${base} ${stateCls} ${interactive}`}>
      {inner}
    </button>
  );
}

export default function CatalogManagePage() {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [modal, setModal] = useState(null); // { kind, mode, data, parentId }
  const [confirm, setConfirm] = useState(null); // { kind, id, label }
  const [busy, setBusy] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all'); // all | camper_care | maintenance
  const [activeOnly, setActiveOnly] = useState(false);
  const { toast, showToast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchCatalogTree();
      setTree(data.stores || []);
    } catch (e) {
      setError(errMessage(e, 'Failed to load catalog.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const stats = useMemo(() => {
    let requestTypes = 0;
    let items = 0;
    let activeItems = 0;
    let camperCare = 0;
    let maintenance = 0;
    for (const store of tree) {
      if (store.fulfilling_role === 'maintenance') maintenance += 1;
      else camperCare += 1;
      for (const rt of store.request_types || []) {
        requestTypes += 1;
        for (const it of rt.items || []) {
          items += 1;
          if (it.is_active) activeItems += 1;
        }
      }
    }
    return { stores: tree.length, requestTypes, items, activeItems, camperCare, maintenance };
  }, [tree]);

  const filtersActive = search.trim() !== '' || roleFilter !== 'all' || activeOnly;

  const filteredTree = useMemo(() => {
    if (!filtersActive) return tree;
    const q = search.trim().toLowerCase();
    const matches = (name) => !q || (name || '').toLowerCase().includes(q);
    return tree
      .filter((s) => roleFilter === 'all' || s.fulfilling_role === roleFilter)
      .filter((s) => !activeOnly || s.is_active)
      .map((s) => {
        const request_types = (s.request_types || [])
          .filter((rt) => !activeOnly || rt.is_active)
          .map((rt) => {
            const items = (rt.items || [])
              .filter((it) => !activeOnly || it.is_active)
              .filter((it) => matches(s.name) || matches(rt.name) || matches(it.name));
            return { ...rt, items };
          })
          .filter((rt) => matches(s.name) || matches(rt.name) || rt.items.length > 0);
        return { ...s, request_types };
      })
      .filter((s) => matches(s.name) || s.request_types.length > 0);
  }, [tree, filtersActive, search, roleFilter, activeOnly]);

  const reorder = async (siblings, fromIdx, dir, patchFn) => {
    const toIdx = fromIdx + dir;
    if (toIdx < 0 || toIdx >= siblings.length) return;
    const arr = [...siblings];
    const [moved] = arr.splice(fromIdx, 1);
    arr.splice(toIdx, 0, moved);
    setReordering(true);
    try {
      await Promise.all(
        arr
          .map((el, i) => (el.sort_order !== i ? patchFn(el.id, { sort_order: i }) : null))
          .filter(Boolean),
      );
      await load();
    } catch (e) {
      showToast(errMessage(e, 'Reorder failed.'));
    } finally {
      setReordering(false);
    }
  };

  const clearFilters = () => {
    setSearch('');
    setRoleFilter('all');
    setActiveOnly(false);
  };

  const handleStoreSubmit = async (form) => {
    setBusy(true);
    const editing = !!modal.data?.id;
    try {
      if (editing) await patchCatalogStore(modal.data.id, form);
      else await createCatalogStore(form);
      setModal(null);
      await load();
      showToast(editing ? `Updated “${form.name}”.` : `Created store “${form.name}”.`);
    } catch (e) { showToast(errMessage(e, 'Save failed.')); }
    finally { setBusy(false); }
  };

  const handleTypeSubmit = async (form) => {
    setBusy(true);
    const editing = !!modal.data?.id;
    try {
      if (editing) await patchCatalogRequestType(modal.data.id, form);
      else await createCatalogRequestType({ ...form, store_id: modal.parentId });
      setModal(null);
      await load();
      showToast(editing ? `Updated “${form.name}”.` : `Added request type “${form.name}”.`);
    } catch (e) { showToast(errMessage(e, 'Save failed.')); }
    finally { setBusy(false); }
  };

  const handleItemSubmit = async (form) => {
    setBusy(true);
    const editing = !!modal.data?.id;
    try {
      if (editing) await patchCatalogItem(modal.data.id, form);
      else await createCatalogItem({ ...form, request_type_id: modal.parentId });
      setModal(null);
      await load();
      showToast(editing ? `Updated “${form.name}”.` : `Added item “${form.name}”.`);
    } catch (e) { showToast(errMessage(e, 'Save failed.')); }
    finally { setBusy(false); }
  };

  const runDelete = async () => {
    if (!confirm) return;
    const { kind, id, label } = confirm;
    setBusy(true);
    try {
      if (kind === 'store') await deleteCatalogStore(id);
      else if (kind === 'type') await deleteCatalogRequestType(id);
      else await deleteCatalogItem(id);
      setConfirm(null);
      await load();
      showToast(`Deleted “${label}”.`);
    } catch (e) { showToast(errMessage(e, 'Delete failed.')); }
    finally { setBusy(false); }
  };

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full">
      <Link to="/admin/home" className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4">
        <ArrowLeft size={14} /> Admin
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between mb-6 gap-4">
        <div className="flex items-start gap-3">
          <span className="inline-flex items-center justify-center w-11 h-11 shrink-0 rounded-xl bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
            <Boxes size={22} aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Request catalog
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
              Configure the stores, request types, and items that populate the
              Maintenance and Camper Care request forms.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Link to="/admin/catalog/planning">
            <Button variant="secondary"><BarChart3 size={16} /> Planning</Button>
          </Link>
          <Button variant="secondary" onClick={() => setShowImport((v) => !v)} data-testid="catalog-import-toggle">
            <Upload size={16} /> {showImport ? 'Close import' : 'Import CSV'}
          </Button>
          <Button onClick={() => setModal({ kind: 'store', data: null })} data-testid="catalog-add-store">
            <Plus size={16} /> Store
          </Button>
        </div>
      </div>

      {!loading && !error && tree.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <StatCard icon={Boxes} label="All stores" value={stats.stores}
            iconClass="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
            onClick={() => setRoleFilter('all')} active={roleFilter === 'all'} testId="filter-all" />
          <StatCard icon={Tag} label="Camper Care" value={stats.camperCare}
            iconClass="bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
            onClick={() => setRoleFilter((r) => (r === 'camper_care' ? 'all' : 'camper_care'))}
            active={roleFilter === 'camper_care'} testId="filter-camper-care" />
          <StatCard icon={Layers} label="Maintenance" value={stats.maintenance}
            iconClass="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
            onClick={() => setRoleFilter((r) => (r === 'maintenance' ? 'all' : 'maintenance'))}
            active={roleFilter === 'maintenance'} testId="filter-maintenance" />
          <StatCard icon={Package} label="Active items only" value={stats.activeItems}
            iconClass="bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
            onClick={() => setActiveOnly((v) => !v)} active={activeOnly} testId="filter-active" />
        </div>
      )}

      {!loading && !error && tree.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="relative flex-1 min-w-[14rem] max-w-md">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search stores, request types, or items…"
              data-testid="catalog-search"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 pl-9 pr-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {filtersActive && (
            <button type="button" onClick={clearFilters} data-testid="catalog-clear-filters"
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 underline">
              Clear filters
            </button>
          )}
          {filtersActive && !search && (
            <span className="text-xs text-gray-400">Reordering is available when no filters are applied.</span>
          )}
        </div>
      )}

      {showImport && <ImportPanel onDone={load} showToast={showToast} />}

      {error && <div className="mb-4"><ErrorPanel>{error}</ErrorPanel></div>}

      {loading ? (
        <LoadingState>Loading catalog…</LoadingState>
      ) : tree.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
          <EmptyState icon={Boxes} title="No stores yet" data-testid="catalog-empty">
            Add a store or import a CSV to get started.
          </EmptyState>
        </div>
      ) : filteredTree.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
          <EmptyState icon={Search} title="No matches" data-testid="catalog-no-matches">
            No stores, request types, or items match your filters.{' '}
            <button type="button" onClick={clearFilters} className="text-blue-600 dark:text-blue-400 underline">Clear filters</button>
          </EmptyState>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 items-start">
          {filteredTree.map((store) => (
            <section key={store.id} data-testid={`store-${store.id}`} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
              <header className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 min-w-0">
                  <h2 className="font-semibold text-gray-900 dark:text-white truncate">{store.name}</h2>
                  <Badge tone="indigo">{store.fulfilling_role === 'maintenance' ? 'Maintenance' : 'Camper Care'}</Badge>
                  {!store.is_active && <Badge tone="amber">Inactive</Badge>}
                </div>
                <div className="flex items-center gap-1">
                  <button type="button" className="text-xs text-blue-600 dark:text-blue-400 hover:underline px-2 py-1 inline-flex items-center gap-1"
                    onClick={() => setModal({ kind: 'store', data: store })}>
                    <Pencil size={12} /> Edit
                  </button>
                  <button type="button" className="text-xs text-red-600 dark:text-red-400 hover:underline px-2 py-1 inline-flex items-center gap-1"
                    onClick={() => setConfirm({ kind: 'store', id: store.id, label: store.name })}>
                    <Trash2 size={12} /> Delete
                  </button>
                  <Button variant="secondary" className="ml-2" onClick={() => setModal({ kind: 'type', data: null, parentId: store.id })}
                    data-testid={`add-type-${store.id}`}>
                    <Plus size={14} /> Type
                  </Button>
                </div>
              </header>

              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {(store.request_types || []).length === 0 ? (
                  <p className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">No request types yet.</p>
                ) : (
                  store.request_types.map((rt, rtIdx) => (
                    <div key={rt.id} data-testid={`type-${rt.id}`} className="px-4 py-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {!filtersActive && (
                            <ReorderControls
                              disabled={reordering}
                              canUp={rtIdx > 0}
                              canDown={rtIdx < store.request_types.length - 1}
                              onUp={() => reorder(store.request_types, rtIdx, -1, patchCatalogRequestType)}
                              onDown={() => reorder(store.request_types, rtIdx, 1, patchCatalogRequestType)}
                              label={rt.name}
                            />
                          )}
                          <h3 className="text-sm font-medium text-gray-900 dark:text-white">{rt.name}</h3>
                          {!rt.is_active && <Badge tone="amber">Inactive</Badge>}
                        </div>
                        <div className="flex items-center gap-1">
                          <button type="button" className="text-xs text-blue-600 dark:text-blue-400 hover:underline px-2 py-1 inline-flex items-center gap-1"
                            onClick={() => setModal({ kind: 'type', data: rt })}>
                            <Pencil size={12} /> Edit
                          </button>
                          <button type="button" className="text-xs text-red-600 dark:text-red-400 hover:underline px-2 py-1 inline-flex items-center gap-1"
                            onClick={() => setConfirm({ kind: 'type', id: rt.id, label: rt.name })}>
                            <Trash2 size={12} /> Delete
                          </button>
                          <button type="button" className="text-xs text-gray-700 dark:text-gray-300 hover:underline px-2 py-1 inline-flex items-center gap-1"
                            onClick={() => setModal({ kind: 'item', data: null, parentId: rt.id })}
                            data-testid={`add-item-${rt.id}`}>
                            <Plus size={12} /> Item
                          </button>
                        </div>
                      </div>
                      {(rt.items || []).length === 0 ? (
                        <p className="text-xs text-gray-400 dark:text-gray-500 pl-1">No items.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {rt.items.map((it, itIdx) => (
                            <div key={it.id} data-testid={`item-${it.id}`}
                              className={`group inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
                                it.is_active
                                  ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-600'
                                  : 'border-dashed border-gray-300 dark:border-gray-700 opacity-60'
                              }`}>
                              {!filtersActive && (
                                <ReorderControls
                                  compact
                                  disabled={reordering}
                                  canUp={itIdx > 0}
                                  canDown={itIdx < rt.items.length - 1}
                                  onUp={() => reorder(rt.items, itIdx, -1, patchCatalogItem)}
                                  onDown={() => reorder(rt.items, itIdx, 1, patchCatalogItem)}
                                  label={it.name}
                                />
                              )}
                              <span className="text-gray-900 dark:text-gray-100">{it.name}</span>
                              {it.unit && <span className="text-gray-400">/{it.unit}</span>}
                              {!it.track_quantity && <Badge tone="gray">service</Badge>}
                              <span className="inline-flex items-center gap-1.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
                                <button type="button" aria-label={`Edit ${it.name}`} className="text-blue-600 dark:text-blue-400"
                                  onClick={() => setModal({ kind: 'item', data: it })}>
                                  <Pencil size={11} />
                                </button>
                                <button type="button" aria-label={`Delete ${it.name}`} className="text-red-600 dark:text-red-400"
                                  onClick={() => setConfirm({ kind: 'item', id: it.id, label: it.name })}>
                                  <Trash2 size={11} />
                                </button>
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </section>
          ))}
        </div>
      )}

      {modal?.kind === 'store' && (
        <StoreModal initial={modal.data} busy={busy} onClose={() => setModal(null)} onSubmit={handleStoreSubmit} />
      )}
      {modal?.kind === 'type' && (
        <TypeModal initial={modal.data} busy={busy} onClose={() => setModal(null)} onSubmit={handleTypeSubmit} />
      )}
      {modal?.kind === 'item' && (
        <ItemModal initial={modal.data} busy={busy} onClose={() => setModal(null)} onSubmit={handleItemSubmit} />
      )}
      {confirm && (
        <ConfirmModal label={confirm.label} busy={busy} onCancel={() => setConfirm(null)} onConfirm={runDelete} />
      )}

      <Toast message={toast} data-testid="catalog-toast" />
    </main>
  );
}
