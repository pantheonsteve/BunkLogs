import { openDB } from 'idb';
import { QUEUE_DB_NAME, QUEUE_STORE } from './constants';

let dbPromise;

export function getQueueDb() {
  if (!dbPromise) {
    dbPromise = openDB(QUEUE_DB_NAME, 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          const store = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
          store.createIndex('status', 'status');
          store.createIndex('kind', 'kind');
          store.createIndex('clientSubmissionId', 'clientSubmissionId');
        }
      },
    });
  }
  return dbPromise;
}

export async function putEntry(entry) {
  const db = await getQueueDb();
  await db.put(QUEUE_STORE, entry);
  return entry;
}

export async function getEntry(id) {
  const db = await getQueueDb();
  return db.get(QUEUE_STORE, id);
}

export async function deleteEntry(id) {
  const db = await getQueueDb();
  await db.delete(QUEUE_STORE, id);
}

export async function listEntries() {
  const db = await getQueueDb();
  return db.getAll(QUEUE_STORE);
}

export async function listPendingEntries() {
  const db = await getQueueDb();
  return db.getAllFromIndex(QUEUE_STORE, 'status', 'pending');
}
