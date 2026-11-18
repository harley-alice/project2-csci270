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
 * Don Norman Design Principles:
 * 1. Visual Hierarchy & Proportions: Fits properly within the table cell without squeezing adjacent columns.
 * 2. Natural Constraints: Dynamically adjusts day count based on month and year.
 * 3. Feedback: Highlights state and predicted expiration clearly with high contrast.
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
    <div
      style={{
        border: '1px solid var(--color-border)',
        padding: '12px 14px',
        margin: '6px 0 0 0',
        background: isUnsure ? '#fff9f8' : '#fafafa',
        boxSizing: 'border-box',
        width: '100%',
        maxWidth: '380px'
      }}
    >
      {/* Header bar with toggle */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
          gap: '8px',
          flexWrap: 'wrap'
        }}
      >
        <span
          style={{
            fontSize: '12px',
            fontWeight: 700,
            color: isUnsure ? 'var(--color-attention)' : 'var(--color-text)'
          }}
        >
          Date Package Opened
        </span>

        <button
          type="button"
          onClick={onToggleUnsure}
          aria-pressed={isUnsure}
          style={{
            background: isUnsure ? 'var(--color-attention)' : '#ffffff',
            color: isUnsure ? '#ffffff' : 'var(--color-attention)',
            border: isUnsure ? '1px solid var(--color-attention)' : '1px solid var(--color-border)',
            padding: '4px 10px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '32px',
            borderRadius: 0
          }}
        >
          {isUnsure ? 'Unsure (Conservative Applied)' : 'Unsure when opened'}
        </button>
      </div>

      {isUnsure ? (
        <div
          role="status"
          style={{
            fontSize: '12px',
            color: 'var(--color-attention)',
            lineHeight: '1.4',
            padding: '8px 10px',
            background: '#ffffff',
            border: '1px solid var(--color-attention)'
          }}
        >
          <strong>Conservative Safety Guideline:</strong> Shelf-life shortened using USDA FoodKeeper minimum window.
        </div>
      ) : (
        <div>
          {/* Segmented Month, Day, Year Selectors */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(120px, 1.8fr) minmax(65px, 1fr) minmax(75px, 1.2fr)',
              gap: '8px',
              marginBottom: '10px'
            }}
          >
            {/* Month */}
            <div>
              <label
                htmlFor={`month-field-${label}`}
                style={{
                  display: 'block',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--color-text-muted)',
                  marginBottom: '3px'
                }}
              >
                Month
              </label>
              <select
                id={`month-field-${label}`}
                value={monthIdx}
                onChange={(e) => handleMonthChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '6px 8px',
                  fontSize: '13px',
                  minHeight: '38px',
                  borderRadius: 0
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
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--color-text-muted)',
                  marginBottom: '3px'
                }}
              >
                Day
              </label>
              <select
                id={`day-field-${label}`}
                value={day}
                onChange={(e) => handleDayChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '6px 8px',
                  fontSize: '13px',
                  minHeight: '38px',
                  borderRadius: 0
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
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--color-text-muted)',
                  marginBottom: '3px'
                }}
              >
                Year
              </label>
              <select
                id={`year-field-${label}`}
                value={year}
                onChange={(e) => handleYearChange(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  border: '1px solid var(--color-border)',
                  background: '#ffffff',
                  padding: '6px 8px',
                  fontSize: '13px',
                  minHeight: '38px',
                  borderRadius: 0
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

          {/* Quick preset affordances */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Set to:
            </span>
            <button
              type="button"
              onClick={setToday}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '28px',
                borderRadius: 0
              }}
            >
              Today
            </button>
            <button
              type="button"
              onClick={setYesterday}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '3px 8px',
                fontSize: '11px',
                cursor: 'pointer',
                minHeight: '28px',
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
          style={{
            fontSize: '12px',
            color: 'var(--color-text)',
            marginTop: '10px',
            padding: '6px 8px',
            background: '#f4f6fb',
            border: '1px solid var(--color-primary-accent)'
          }}
        >
          Predicted Expiration: <strong>{formatDateDisplay(previewExpiry)}</strong>
        </div>
      )}
    </div>
  );
}
