/**
 * API service for communicating with the backend FastAPI server.
 * All functions connect directly to backend endpoints powered by
 * the YOLO detection model and Ashton's USDA FoodKeeper database.
 */

// Helper to check for JSON error responses
async function parseError(response, defaultMsg) {
  let message = `${defaultMsg} (status: ${response.status})`;
  try {
    const errJson = await response.json();
    if (errJson && errJson.detail) {
      message = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
    } else if (errJson && errJson.error) {
      message = errJson.error;
    }
  } catch (_) {
    // Response was not JSON
  }
  return new Error(message);
}

/**
 * Send an image blob or file to the YOLO object detection endpoint.
 *
 * @param {Blob|File} imageBlob - The image file to analyze
 * @param {number} confidenceThreshold - Minimum certainty cut-off (0.05 to 0.95)
 * @returns {Promise<Array>} List of detected items with bounding boxes and safety rules
 */
export async function detectFridgeItems(imageBlob, confidenceThreshold = 0.20) {
  const formData = new FormData();
  formData.append('file', imageBlob, 'fridge_scan.jpg');

  const queryParams = new URLSearchParams({
    confidence_threshold: confidenceThreshold.toString()
  });

  const res = await fetch(`/api/detect?${queryParams}`, {
    method: 'POST',
    body: formData
  });

  if (!res.ok) {
    throw await parseError(res, 'Item detection failed');
  }

  const data = await res.json();
  // Return the detections array returned by the FastAPI inference endpoint
  return data.detections || data || [];
}

/**
 * Fetch all food safety categories and tiers from the FoodKeeper database.
 *
 * @returns {Promise<Array>} List of category objects
 */
export async function getCategories() {
  const res = await fetch('/api/categories');
  if (!res.ok) {
    throw await parseError(res, 'Failed to fetch categories');
  }
  return await res.json();
}

/**
 * Fetch all storage rules from Ashton's USDA FoodKeeper database.
 * Used by the frontend to dynamically populate food classes and default shelf lives.
 *
 * @returns {Promise<Array>} List of storage rule objects
 */
export async function getStorageRules() {
  const res = await fetch('/api/rules');
  if (!res.ok) {
    throw await parseError(res, 'Failed to fetch storage rules');
  }
  return await res.json();
}

/**
 * Calculate the expiration date and shelf life using Ashton's USDA FoodKeeper rule engine.
 *
 * @param {string} foodClass - The class identifier (e.g. 'milk', 'chicken')
 * @param {string} packageState - 'sealed' or 'opened'
 * @param {string} storageLocation - 'refrigerator', 'freezer', or 'pantry'
 * @param {boolean} isCooked - Whether the food is cooked
 * @param {string|null} startDate - The start date string in 'YYYY-MM-DD' format
 * @returns {Promise<Object>} Calculated shelf life, dates, and advisory guidance
 */
export async function calculateRule({
  foodClass,
  packageState = 'sealed',
  storageLocation = 'refrigerator',
  isCooked = false,
  startDate = null
}) {
  const payload = {
    food_class: foodClass,
    package_state: packageState,
    storage_location: storageLocation,
    is_cooked: isCooked,
    start_date: startDate || undefined
  };

  const res = await fetch('/api/rules/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    throw await parseError(res, 'Failed to calculate food rule');
  }

  return await res.json();
}

/**
 * Send user adjustments and corrections to the active learning feedback endpoint.
 *
 * @param {Object} payload - Feedback data including label corrections or false positives
 * @returns {Promise<Object>} Status response
 */
export async function sendFeedback(payload) {
  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw await parseError(res, 'Failed to record feedback');
    }
    return await res.json();
  } catch (err) {
    console.warn('[API Service] Feedback recording encountered an issue:', err);
    return { status: 'failed', error: err.message };
  }
}

/**
 * Retrieve saved fridge inventory items from the database.
 *
 * @returns {Promise<Array>} List of inventory items
 */
export async function getInventory() {
  const res = await fetch('/api/inventory');
  if (!res.ok) {
    throw await parseError(res, 'Failed to fetch inventory');
  }
  return await res.json();
}

/**
 * Save new or verified items to the fridge inventory database in a single batch.
 *
 * @param {Array} items - List of item objects to store
 * @returns {Promise<Object>} Response from the inventory batch endpoint
 */
export async function saveInventory(items) {
  const formattedItems = items.map((it) => ({
    food_class: it.label || it.food_class,
    custom_name: it.custom_name || (it.label ? it.label.replace(/_/g, ' ') : null),
    package_state: it.packageState || it.package_state || 'sealed',
    storage_location: it.storage_location || 'refrigerator',
    shelf_life_days: parseInt(it.days ?? it.shelf_life_days ?? 7, 10),
    expiration_date: it.expirationDate || it.expiration_date || null,
    added_date: it.addedDate || it.added_date || null,
    verified: Boolean(it.verified || it.userEdited),
    confidence: it.confidence !== undefined ? it.confidence : 1.0,
    bbox: it.bbox || null,
    user_notes: it.user_notes || (it.isUnsureOpened ? 'Marked unsure opening date' : null)
  }));

  const res = await fetch('/api/inventory/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: formattedItems })
  });

  if (!res.ok) {
    throw await parseError(res, 'Failed to save items to inventory database');
  }

  return await res.json();
}

/**
 * Remove an item from the fridge inventory database by its unique ID.
 *
 * @param {string} id - The ID of the item to delete
 * @returns {Promise<Object>} Deletion result
 */
export async function deleteInventoryItem(id) {
  const res = await fetch(`/api/inventory/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  });

  if (!res.ok) {
    throw await parseError(res, 'Failed to delete inventory item');
  }

  return await res.json();
}
