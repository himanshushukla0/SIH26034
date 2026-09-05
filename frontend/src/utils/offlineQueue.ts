/**
 * SIH26034 — Field Inspector Offline Queue
 *
 * IndexedDB storage and auto-synchronization manager for Legal Metrology officers
 * conducting inspections in wholesale markets, basements, or low-connectivity godowns.
 */

import { auditImage } from "../api";

const DB_NAME = "lmpc_inspector_db";
const DB_VERSION = 1;
const STORE_NAME = "pending_scans";

export interface PendingScan {
  id: string;
  timestamp: string;
  fileName: string;
  fileType: string;
  fileBlob: Blob;
  marketLocation?: string;
  officerNotes?: string;
}

/** Open or create the IndexedDB database. */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) {
      reject(new Error("IndexedDB is not supported in this environment."));
      return;
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Enqueue an image scan into the offline store when network is unavailable. */
export async function enqueueOfflineScan(
  file: File,
  marketLocation?: string,
  officerNotes?: string
): Promise<string> {
  const db = await openDB();
  const id = `scan_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  
  const record: PendingScan = {
    id,
    timestamp: new Date().toISOString(),
    fileName: file.name,
    fileType: file.type || "image/jpeg",
    fileBlob: file,
    marketLocation: marketLocation || "Field Retail Inspection",
    officerNotes,
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(record);

    req.onsuccess = () => resolve(id);
    req.onerror = () => reject(req.error);
  });
}

/** Get the count of pending scans waiting to be synced. */
export async function getPendingScansCount(): Promise<number> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.count();

      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return 0;
  }
}

/** Get all pending scans. */
export async function getAllPendingScans(): Promise<PendingScan[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();

    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

/** Delete a single scan once synced successfully. */
export async function deletePendingScan(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(id);

    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Synchronize all pending offline scans to the backend.
 */
export async function syncAllPendingScans(
  onProgress?: (current: number, total: number) => void
): Promise<{ success: number; failed: number }> {
  const scans = await getAllPendingScans();
  let success = 0;
  let failed = 0;

  for (let i = 0; i < scans.length; i++) {
    const scan = scans[i];
    try {
      const reconstructedFile = new File([scan.fileBlob], scan.fileName, {
        type: scan.fileType,
      });

      await auditImage(reconstructedFile);
      await deletePendingScan(scan.id);
      success++;
    } catch {
      failed++;
    }

    if (onProgress) {
      onProgress(i + 1, scans.length);
    }
  }

  return { success, failed };
}
