import React from 'react';
import { getTodayDateStr } from '../utils/dateUtils';

// 12-month calendar names
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * DateOpenedField Component
 * 
 * Follows Don Norman's UI & Design of Everyday Things principles:
 * 1. Affordance & Signifiers: Uses standard interactive dropdowns and clear labels.
 * 2. Feedback: Immediate visual feedback when switching between explicit date and "Unsure".
 * 3. Constraints: Days in month automatically adjust to month/year (no February 31st).
 * 4. Conceptual Consistency: Zero emojis or gradient boxes; strict 1px solid var(--color-border),
 *    clean 44px min-height targets, var(--color-primary-accent) and var(--color-attention).
 */
export default function DateOpenedField({
  value,
  onChange,
  isUnsure,
  onToggleUnsure,
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

  // Reasonable year range (current year and prior year)
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
        padding: '12px 14px',
        margin: '8px 0 0 0',
        background: isUnsure ? '#fff9f8' : '#fafafa',
        boxSizing: 'border-box'
      }}
    >
      <legend
        style={{
          fontSize: '12px',
          fontWeight: 700,
          padding: '0 6px',
          color: isUnsure ? 'var(--color-attention)' : 'var(--color-text)'
        }}
      >
        Date Package Opened
      </legend>

      {/* Primary Action / Mode Toggle */}
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
        <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
          {isUnsure ? 'Opening date is unknown' : 'Specify when package was opened:'}
        </span>

        <button
          type="button"
          onClick={onToggleUnsure}
          aria-pressed={isUnsure}
          style={{
            background: isUnsure ? 'var(--color-attention)' : '#ffffff',
            color: isUnsure ? '#ffffff' : 'var(--color-attention)',
            border: isUnsure ? '1px solid var(--color-attention)' : '1px solid var(--color-border)',
            padding: '6px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '36px',
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
          <strong>Conservative Safety Guideline:</strong> Because the opening date is uncertain, shelf-life is calculated using the minimum USDA FoodKeeper window.
        </div>
      ) : (
        <div>
          {/* Segmented Month, Day, Year Selectors */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1.2fr',
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
                  marginBottom: '4px'
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
                  minHeight: '40px',
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
                  marginBottom: '4px'
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
                  minHeight: '40px',
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
                  marginBottom: '4px'
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
                  minHeight: '40px',
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
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              Set to:
            </span>
            <button
              type="button"
              onClick={setToday}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '4px 10px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '32px',
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
                padding: '4px 10px',
                fontSize: '12px',
                cursor: 'pointer',
                minHeight: '32px',
                borderRadius: 0
              }}
            >
              Yesterday
            </button>
          </div>
        </div>
      )}
    </fieldset>
  );
}
