import React from 'react';
import { getTodayDateStr } from '../utils/dateUtils';

// Standard month abbreviations
const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

/**
 * FunDateOpenedPicker Component
 * Renders an interactive segmented Month, Day, and Year selector box
 * with quick shortcuts ("Today", "Yesterday", "3d ago") and an "Unsure" toggle
 * that applies Ashton's conservative FoodKeeper guidelines.
 */
export default function FunDateOpenedPicker({
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

  // Compute number of days in the current selected month
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

  const setRelativeDaysAgo = (daysAgo) => {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dt = String(d.getDate()).padStart(2, '0');
    onChange(`${y}-${m}-${dt}`);
  };

  return (
    <div
      style={{
        border: isUnsure ? '2px solid var(--color-attention)' : '2px solid var(--color-primary-accent)',
        background: isUnsure ? '#fff9f8' : '#f8fafd',
        padding: '10px 12px',
        borderRadius: '8px',
        marginTop: '8px',
        boxShadow: '0 2px 5px rgba(0,0,0,0.06)'
      }}
    >
      {/* Header bar with title and Unsure button */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
          gap: '8px',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '14px' }}>📅</span>
          <span
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--color-text)',
              letterSpacing: '0.2px'
            }}
          >
            Date Opened
          </span>
        </div>

        {/* Unsure button */}
        <button
          type="button"
          onClick={onToggleUnsure}
          aria-pressed={isUnsure}
          style={{
            background: isUnsure ? 'var(--color-attention)' : '#ffffff',
            color: isUnsure ? '#ffffff' : 'var(--color-attention)',
            border: '1.5px solid var(--color-attention)',
            padding: '3px 10px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: 'pointer',
            borderRadius: '4px',
            minHeight: '28px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          {isUnsure ? '✓ Unsure (Conservative Active)' : '? Unsure when opened'}
        </button>
      </div>

      {isUnsure ? (
        <div
          style={{
            fontSize: '12px',
            color: 'var(--color-attention)',
            lineHeight: '1.4',
            padding: '6px 8px',
            background: '#ffffff',
            border: '1px solid #ffd0c7',
            borderRadius: '4px'
          }}
        >
          <strong>Safety mode:</strong> Using Ashton's conservative minimum shelf life estimate because opening date is unknown.
        </div>
      ) : (
        <>
          {/* Segmented Month, Day, Year Selector Boxes */}
          <div
            style={{
              display: 'flex',
              gap: '6px',
              alignItems: 'center',
              marginBottom: '8px'
            }}
          >
            {/* Month Box */}
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1.5 }}>
              <label
                htmlFor={`month-select-${label}`}
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--color-text-muted)',
                  marginBottom: '2px'
                }}
              >
                Month
              </label>
              <select
                id={`month-select-${label}`}
                value={monthIdx}
                onChange={(e) => handleMonthChange(parseInt(e.target.value, 10))}
                style={{
                  padding: '6px 4px',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  background: '#ffffff',
                  minHeight: '36px',
                  cursor: 'pointer'
                }}
              >
                {MONTHS.map((m, idx) => (
                  <option key={m} value={idx}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            {/* Day Box */}
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <label
                htmlFor={`day-select-${label}`}
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--color-text-muted)',
                  marginBottom: '2px'
                }}
              >
                Day
              </label>
              <select
                id={`day-select-${label}`}
                value={day}
                onChange={(e) => handleDayChange(parseInt(e.target.value, 10))}
                style={{
                  padding: '6px 4px',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  background: '#ffffff',
                  minHeight: '36px',
                  cursor: 'pointer',
                  textAlign: 'center'
                }}
              >
                {dayOptions.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* Year Box */}
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1.2 }}>
              <label
                htmlFor={`year-select-${label}`}
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--color-text-muted)',
                  marginBottom: '2px'
                }}
              >
                Year
              </label>
              <select
                id={`year-select-${label}`}
                value={year}
                onChange={(e) => handleYearChange(parseInt(e.target.value, 10))}
                style={{
                  padding: '6px 4px',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  background: '#ffffff',
                  minHeight: '36px',
                  cursor: 'pointer'
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

          {/* Quick preset chips */}
          <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginRight: '2px' }}>
              Quick:
            </span>
            <button
              type="button"
              onClick={() => setRelativeDaysAgo(0)}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '2px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '26px'
              }}
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => setRelativeDaysAgo(1)}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '2px 8px',
                fontSize: '11px',
                cursor: 'pointer',
                minHeight: '26px'
              }}
            >
              Yesterday
            </button>
            <button
              type="button"
              onClick={() => setRelativeDaysAgo(3)}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '2px 8px',
                fontSize: '11px',
                cursor: 'pointer',
                minHeight: '26px'
              }}
            >
              3 days ago
            </button>
          </div>
        </>
      )}
    </div>
  );
}
