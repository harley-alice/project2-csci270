import React from 'react';
import { getTodayDateStr, formatDateDisplay } from '../utils/dateUtils';

// 12-month calendar names
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * DateOpenedField Component
 * 
 * Conforms to WCAG 2.1 / 2.2 AA & AAA Standards and Section 508 / ADA:
 * - Semantic Grouping: Uses <fieldset> and <legend> so screen readers announce context.
 * - Target Size: Minimum 44px by 44px tap target heights for all interactables (WCAG 2.5.5 / 2.5.8).
 * - Accessible Names & Associations: Every <select> and <input> has an explicit htmlFor/id and descriptive aria-label.
 * - Live Region Feedback: State changes (such as selecting Unsure) announce via aria-live="polite".
 * - High Contrast: Text and borders adhere to >4.5:1 contrast ratio against backgrounds.
 * - Clear Focus States: Retains visible high-contrast focus rings for keyboard navigators.
 */
export default function DateOpenedField({
  value,
  onChange,
  isUnsure,
  onToggleUnsure,
  previewExpiry,
  label
}) {
  const todayStr = getTodayDateStr();
  const currentDate = value || todayStr;
  const parts = currentDate.split('-');
  const year = parseInt(parts[0], 10) || new Date().getFullYear();
  const monthIdx = (parseInt(parts[1], 10) || 1) - 1;
  const day = parseInt(parts[2], 10) || 1;

  // Natural calendar constraints: exact days in selected month & year
  const daysInMonth = new Date(year, monthIdx + 1, 0).getDate();
  const dayOptions = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  // Available years: current year and prior year
  const currentYear = new Date().getFullYear();
  const yearOptions = [currentYear - 1, currentYear];

  const handleMonthChange = (newMonthIdx) => {
    const monthNum = String(newMonthIdx + 1).padStart(2, '0');
    const clampedDay = Math.min(day, new Date(year, newMonthIdx + 1, 0).getDate());
    const dayNum = String(clampedDay).padStart(2, '0');
    onChange(`${year}-${monthNum}-${dayNum}`);
  };

  const handleDayChange = (newDay) => {
    const monthNum = String(monthIdx + 1).padStart(2, '0');
    const dayNum = String(newDay).padStart(2, '0');
    onChange(`${year}-${monthNum}-${dayNum}`);
  };

  const handleYearChange = (newYear) => {
    const monthNum = String(monthIdx + 1).padStart(2, '0');
    const clampedDay = Math.min(day, new Date(newYear, monthIdx + 1, 0).getDate());
    const dayNum = String(clampedDay).padStart(2, '0');
    onChange(`${newYear}-${monthNum}-${dayNum}`);
  };

  const setToday = () => {
    onChange(todayStr);
  };

  const setYesterday = () => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dt = String(d.getDate()).padStart(2, '0');
    onChange(`${y}-${m}-${dt}`);
  };

  return (
    <fieldset
      style={{
        border: '1px solid var(--color-border)',
        padding: '14px',
        margin: '8px 0 0 0',
        background: isUnsure ? '#fff9f8' : '#fafafa',
        boxSizing: 'border-box',
        width: '100%',
        maxWidth: '420px'
      }}
    >
      <legend
        style={{
          fontSize: '13px',
          fontWeight: 700,
          color: isUnsure ? 'var(--color-attention)' : 'var(--color-text)',
          padding: '0 6px'
        }}
      >
        Date Package Opened
      </legend>

      {/* Header with Mode Toggle */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
          gap: '8px',
          flexWrap: 'wrap'
        }}
      >
        <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
          {isUnsure ? 'Opening date is unknown' : 'Specify opening date:'}
        </span>

        {/* Meets 44px min-height target */}
        <button
          type="button"
          onClick={onToggleUnsure}
          aria-pressed={isUnsure}
          aria-label={
            isUnsure
              ? 'Unsure mode active, minimum FoodKeeper shelf life applied. Click to enter specific date.'
              : 'Click if unsure when package was opened to apply conservative FoodKeeper estimate'
          }
          style={{
            background: isUnsure ? 'var(--color-attention)' : '#ffffff',
            color: isUnsure ? '#ffffff' : 'var(--color-attention)',
            border: isUnsure ? '2px solid var(--color-attention)' : '1px solid var(--color-border)',
            padding: '8px 14px',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            minHeight: '44px',
            borderRadius: 0
          }}
        >
          {isUnsure ? 'Unsure (Conservative Applied)' : 'Unsure when opened'}
        </button>
      </div>

      {isUnsure ? (
        <div
          role="status"
          aria-live="polite"
          style={{
            fontSize: '12px',
            color: 'var(--color-attention)',
            lineHeight: '1.5',
            padding: '10px 12px',
            background: '#ffffff',
            border: '1px solid var(--color-attention)'
          }}
        >
          <strong>Conservative Safety Guideline:</strong> Shelf-life shortened using USDA FoodKeeper minimum window for unknown opened date.
        </div>
      ) : (
        <div>
          {/* Segmented Month, Day, Year Selectors */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(120px, 1.8fr) minmax(70px, 1fr) minmax(80px, 1.2fr)',
              gap: '8px',
              marginBottom: '12px'
            }}
          >
            {/* Month */}
            <div>
              <label
                htmlFor={`month-field-${label}`}
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--color-text)',
                  marginBottom: '4px'
                }}
              >
                Month
              </label>
              <select
                id={`month-field-${label}`}
                aria-label={`Month package opened for item ${label}`}
                value={monthIdx}
                onChange={(e) => handleMonthChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '8px',
                  fontSize: '13px',
                  minHeight: '44px',
                  borderRadius: 0,
                  color: 'var(--color-text)'
                }}
              >
                {MONTHS.map((m, idx) => (
                  <option key={m} value={idx}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            {/* Day */}
            <div>
              <label
                htmlFor={`day-field-${label}`}
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--color-text)',
                  marginBottom: '4px'
                }}
              >
                Day
              </label>
              <select
                id={`day-field-${label}`}
                aria-label={`Day package opened for item ${label}`}
                value={day}
                onChange={(e) => handleDayChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '8px',
                  fontSize: '13px',
                  minHeight: '44px',
                  borderRadius: 0,
                  color: 'var(--color-text)'
                }}
              >
                {dayOptions.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* Year */}
            <div>
              <label
                htmlFor={`year-field-${label}`}
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--color-text)',
                  marginBottom: '4px'
                }}
              >
                Year
              </label>
              <select
                id={`year-field-${label}`}
                aria-label={`Year package opened for item ${label}`}
                value={year}
                onChange={(e) => handleYearChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '8px',
                  fontSize: '13px',
                  minHeight: '44px',
                  borderRadius: 0,
                  color: 'var(--color-text)'
                }}
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick preset affordances with full 44px accessible target heights */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              Quick select:
            </span>
            <button
              type="button"
              onClick={setToday}
              aria-label="Set date opened to today"
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '8px 14px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '44px',
                borderRadius: 0
              }}
            >
              Today
            </button>
            <button
              type="button"
              onClick={setYesterday}
              aria-label="Set date opened to yesterday"
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '8px 14px',
                fontSize: '12px',
                cursor: 'pointer',
                minHeight: '44px',
                borderRadius: 0
              }}
            >
              Yesterday
            </button>
          </div>
        </div>
      )}

      {/* Immediate feedback: Predicted Expiration */}
      {previewExpiry && (
        <div
          role="status"
          aria-live="polite"
          style={{
            fontSize: '13px',
            color: 'var(--color-text)',
            marginTop: '12px',
            padding: '8px 10px',
            background: '#f4f6fb',
            border: '1px solid var(--color-primary-accent)'
          }}
        >
          Predicted Expiration: <strong>{formatDateDisplay(previewExpiry)}</strong>
        </div>
      )}
    </fieldset>
  );
}
