import { INITIAL_DETECTIONS } from '../mockData';

// When false, throws error instead of silently returning mock detections so failures are visible
let fallbackToMock = false;

export function setFallbackToMock(enable) {
  fallbackToMock = enable;
}

/**
 * Upload an image (File or Blob) to YOLO detection endpoint
 */
export async function detectFridgeItems(imageBlob) {
  try {
    const formData = new FormData();
    formData.append('file', imageBlob, 'fridge_scan.jpg');

    // CJ's FastAPI backend serves POST /api/detect (it also keeps /detect as an alias for Alice's local_test_server.py)
    const res = await fetch('/api/detect', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      let errMsg = `Detection failed with status: ${res.status}`;
      try {
        const errJson = await res.json();
        // local_test_server.py uses {error}, FastAPI uses {detail} (string, or a list of validation errors)
        if (errJson && errJson.error) errMsg = errJson.error;
        else if (errJson && typeof errJson.detail === 'string') errMsg = errJson.detail;
        else if (errJson && Array.isArray(errJson.detail)) errMsg = errJson.detail.map((d) => d.msg).join('; ');
      } catch (_) {}
      throw new Error(errMsg);
    }
    const data = await res.json();
    // The FastAPI backend wraps results as {success, count, detections: [...]}; the local test server returns a bare array
    return Array.isArray(data) ? data : data.detections || [];
  } catch (err) {
    if (fallbackToMock) {
      console.warn('[API Service] Backend /api/detect offline, using local mock detections.');
      await new Promise((r) => setTimeout(r, 600));
      return INITIAL_DETECTIONS;
    }
    throw err;
  }
}

/**
 * Send human-in-the-loop correction / false positive payload
 */
export async function sendFeedback(payload) {
  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Failed to record feedback');
    return await res.json();
  } catch (err) {
    // Silently fall back to local logging if server isn't up yet
    console.log('[API Service] Feedback saved locally:', payload);
    return { status: 'logged_locally', payload };
  }
}

/**
 * Fetch user inventory from SQLite backend (or localStorage if offline)
 */
export async function getInventory() {
  try {
    const res = await fetch('/api/inventory');
    if (!res.ok) throw new Error('Failed to fetch inventory');
    return await res.json();
  } catch (err) {
    const saved = localStorage.getItem('fridge_inventory');
    return saved ? JSON.parse(saved) : null;
  }
}

/**
 * Save confirmed items to backend SQLite (and backup to local storage)
 */
export async function saveInventory(items) {
  localStorage.setItem('fridge_inventory', JSON.stringify(items));
  try {
    const res = await fetch('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items })
    });
    if (!res.ok) throw new Error('Failed to save to backend');
    return await res.json();
  } catch (err) {
    console.log('[API Service] Saved to local browser storage.');
    return { status: 'saved_locally' };
  }
}

/**
 * Calculate dynamic shelf life from USDA FoodKeeper guidelines
 */
export function estimateShelfLife(itemClass, isOpened = false) {
  // Baseline storage lookup (days) based on USDA FoodKeeper guidelines
  const shelfLifeRules = {
    milk: { sealed: 7, opened: 4 },
    egg: { sealed: 21, opened: 14 },
    yogurt: { sealed: 14, opened: 7 },
    chicken: { sealed: 2, opened: 1 },
    beef: { sealed: 4, opened: 2 },
    bacon: { sealed: 14, opened: 7 },
    cheese: { sealed: 21, opened: 14 },
    goat_cheese: { sealed: 14, opened: 7 },
    butter: { sealed: 30, opened: 21 },
    cream: { sealed: 10, opened: 5 },
    apple: { sealed: 21, opened: 14 },
    banana: { sealed: 5, opened: 3 },
    strawberries: { sealed: 5, opened: 3 },
    blueberries: { sealed: 7, opened: 4 },
    orange: { sealed: 14, opened: 10 },
    lemon: { sealed: 21, opened: 14 },
    lime: { sealed: 21, opened: 14 },
    tomato: { sealed: 7, opened: 4 },
    bell_pepper: { sealed: 10, opened: 5 },
    carrot: { sealed: 21, opened: 14 },
    spinach: { sealed: 5, opened: 3 },
    mushrooms: { sealed: 5, opened: 3 },
    bread: { sealed: 7, opened: 5 },
    shrimp: { sealed: 2, opened: 1 },
    jar: { sealed: 30, opened: 14 }
  };

  const rule = shelfLifeRules[itemClass] || { sealed: 7, opened: 5 };
  return isOpened ? rule.opened : rule.sealed;
}


// ---- Backend inventory persistence (CJ's FastAPI backend, SQLite) ----

function toTrackingItem(it) {
  return {
    id: it.id,
    label: it.food_class,
    packageState: it.package_state || 'sealed',
    days: it.days_remaining !== undefined ? it.days_remaining : it.shelf_life_days
  };
}

/** Load saved inventory from the backend. Returns null when offline or empty so the UI keeps its defaults. */
export async function fetchSavedInventory() {
  try {
    const res = await fetch('/api/inventory');
    if (!res.ok) return null;
    const items = await res.json();
    return Array.isArray(items) && items.length > 0 ? items.map(toTrackingItem) : null;
  } catch (_) {
    return null;
  }
}

/** Persist confirmed items via POST /api/inventory/batch. Returns tracking items, or null if the backend is unreachable. */
export async function saveInventoryBatch(items) {
  try {
    const res = await fetch('/api/inventory/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map((it) => ({
          food_class: it.label,
          package_state: it.packageState || 'sealed',
          storage_location: 'refrigerator',
          shelf_life_days: it.days,
          confidence: it.confidence ?? 1.0,
          bbox: Array.isArray(it.bbox) && it.bbox.length === 4 ? it.bbox : null,
          verified: Boolean(it.userEdited)
        }))
      })
    });
    if (!res.ok) return null;
    const created = await res.json();
    return created.map(toTrackingItem);
  } catch (_) {
    return null;
  }
}

/** Fire-and-forget delete of a saved item (ids of local-only items simply 404). */
export function deleteSavedItem(id) {
  fetch(`/api/inventory/${id}`, { method: 'DELETE' }).catch(() => {});
}
