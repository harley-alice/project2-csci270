/**
 * Utility functions for date manipulation and display formatting.
 * Keeps date logic clear and consistent across all components.
 */

/**
 * Returns today's date formatted as 'YYYY-MM-DD'.
 */
export function getTodayDateStr() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Adds an integer number of days to a 'YYYY-MM-DD' date string.
 *
 * @param {string} dateStr - Starting date in 'YYYY-MM-DD' format
 * @param {number|string} days - Number of days to add
 * @returns {string|null} Resulting date in 'YYYY-MM-DD' format
 */
export function addDaysToDate(dateStr, days) {
  if (!dateStr) return null;
  const parts = String(dateStr).split('-');
  if (parts.length !== 3) return null;

  const yearNum = parseInt(parts[0], 10);
  const monthNum = parseInt(parts[1], 10) - 1;
  const dayNum = parseInt(parts[2], 10);

  const d = new Date(yearNum, monthNum, dayNum);
  d.setDate(d.getDate() + (parseInt(days, 10) || 0));

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Formats a 'YYYY-MM-DD' date string into a friendly human-readable format.
 * Example: '2026-11-25' -> 'Nov 25, 2026'
 *
 * @param {string} dateStr - Date string to format
 * @returns {string} Human-readable date string
 */
export function formatDateDisplay(dateStr) {
  if (!dateStr) return 'N/A';
  const parts = String(dateStr).split('-');
  if (parts.length !== 3) return dateStr;

  const yearNum = parseInt(parts[0], 10);
  const monthNum = parseInt(parts[1], 10) - 1;
  const dayNum = parseInt(parts[2], 10);

  const d = new Date(yearNum, monthNum, dayNum);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

/**
 * Calculate the number of calendar days between today and a target date.
 *
 * @param {string} targetDateStr - Target date in 'YYYY-MM-DD' format
 * @returns {number} Days remaining (negative if expired)
 */
export function calculateDaysRemaining(targetDateStr) {
  if (!targetDateStr) return 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const parts = String(targetDateStr).split('-');
  if (parts.length !== 3) return 0;

  const target = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  target.setHours(0, 0, 0, 0);

  const diffMs = target.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Converts underscored food labels to clean, capitalized display text.
 * Example: 'bell_pepper' -> 'bell pepper'
 *
 * @param {string} label - Raw class name
 * @returns {string} Formatted label
 */
export function formatLabel(label) {
  return label ? String(label).replace(/_/g, ' ') : '';
}
