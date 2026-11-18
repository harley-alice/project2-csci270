import React from 'react';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import { formatLabel, formatDateDisplay, getTodayDateStr } from '../utils/dateUtils';

/**
 * ReviewSection component.
 * Allows the user to inspect detected items from the YOLO model,
 * correct misclassifications, switch package states (sealed vs opened),
 * enter date opened or choose the "Unsure" conservative food safety mode,
 * and draw custom bounding boxes for items the detector missed.
 */
export default function ReviewSection({
  image,
  visibleItems,
  rawDetections,
  confidenceThreshold,
  setConfidenceThreshold,
  foodClasses,
  isDetecting,
  detectionError,
  setDetectionError,
  isDrawingMode,
  setIsDrawingMode,
  currentBox,
  setCurrentBox,
  setDrawingStart,
  imageContainerRef,
  imgElementRef,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  updateLabel,
  togglePackageState,
  updateOpenedDate,
  toggleUnsureOpened,
  updateDays,
  removeItem,
  confirmAndTrack,
  onBack
}) {
  const today = getTodayDateStr();

  return (
    <section aria-labelledby="review-heading">
      {detectionError && (
        <div
          role="alert"
          style={{
            background: '#fff2f0',
            border: '1px solid var(--color-error)',
            color: 'var(--color-error)',
            padding: '12px 16px',
            marginBottom: '16px',
            fontSize: '14px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <span>
            <strong>Detection Error:</strong> {detectionError}
          </span>
          <button
            type="button"
            onClick={() => setDetectionError(null)}
            aria-label="Dismiss error"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-error)',
              fontWeight: 'bold',
              fontSize: '18px',
              padding: '4px 8px',
              minHeight: '36px'
            }}
          >
            ✕
          </button>
        </div>
      )}

      {isDetecting && (
        <div
          role="status"
          aria-live="polite"
          style={{
            background: '#f4f6fb',
            border: '1px solid var(--color-primary-accent)',
            color: 'var(--color-primary-accent)',
            padding: '12px 16px',
            marginBottom: '16px',
            fontSize: '14px',
            fontWeight: 600
          }}
        >
          Analyzing image and applying USDA FoodKeeper rules...
        </div>
      )}

      {/* Sensitivity / Detection Slider */}
      <div
        style={{
          border: '1px solid var(--color-border)',
          padding: '16px 18px',
          marginBottom: '20px',
          background: '#fafafa'
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px'
          }}
        >
          <label htmlFor="detection-slider" style={{ fontSize: '14px', fontWeight: 600 }}>
            Detection Sensitivity:
          </label>
          <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }} aria-live="polite">
            Showing {visibleItems.length} of {rawDetections.length} items
          </span>
        </div>
        <input
          id="detection-slider"
          type="range"
          min="0.05"
          max="0.95"
          step="0.05"
          value={confidenceThreshold}
          onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
          aria-valuemin="0.05"
          aria-valuemax="0.95"
          aria-valuenow={confidenceThreshold}
          aria-valuetext={`${Math.round(confidenceThreshold * 100)} percent confidence`}
          style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-primary-accent)' }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '12px',
            color: 'var(--color-text-muted)',
            marginTop: '4px'
          }}
        >
          <span>Show more items</span>
          <span>Only high certainty</span>
        </div>
      </div>

      {/* Photo with Bounding Boxes */}
      <BoundingBoxOverlay
        image={image}
        visibleItems={visibleItems}
        isDrawingMode={isDrawingMode}
        currentBox={currentBox}
        imageContainerRef={imageContainerRef}
        imgElementRef={imgElementRef}
        handleMouseDown={handleMouseDown}
        handleMouseMove={handleMouseMove}
        handleMouseUp={handleMouseUp}
        formatLabel={formatLabel}
      />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '14px'
        }}
      >
        <div>
          <h2 id="review-heading" style={{ fontSize: '18px', fontWeight: 700 }}>
            Review Detected Items
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
            {isDrawingMode
              ? 'Click and drag on the photo above to outline the missed food item.'
              : 'Verify items and package states. Shelf lives are calculated directly from USDA FoodKeeper rules.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={() => {
              setIsDrawingMode(!isDrawingMode);
              setCurrentBox(null);
              setDrawingStart(null);
            }}
            style={{
              background: isDrawingMode ? 'var(--color-primary-accent)' : '#ffffff',
              color: isDrawingMode ? '#ffffff' : 'var(--color-text)',
              border: '1px solid var(--color-border)',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            {isDrawingMode ? 'Drawing... (Click & Drag Photo)' : '+ Add Missed Item'}
          </button>
          {isDrawingMode && (
            <button
              type="button"
              onClick={() => {
                setIsDrawingMode(false);
                setCurrentBox(null);
                setDrawingStart(null);
              }}
              style={{
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                padding: '8px 12px',
                fontSize: '13px',
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          marginBottom: '24px',
          fontSize: '13px'
        }}
      >
        <caption
          className="sr-only"
          style={{
            position: 'absolute',
            width: '1px',
            height: '1px',
            padding: 0,
            margin: '-1px',
            overflow: 'hidden',
            clip: 'rect(0, 0, 0, 0)',
            border: 0
          }}
        >
          List of food items detected by model for verification
        </caption>
        <thead>
          <tr
            style={{
              borderBottom: '1px solid var(--color-border)',
              textAlign: 'left',
              fontSize: '13px',
              color: 'var(--color-text)'
            }}
          >
            <th scope="col" style={{ padding: '10px 0', width: '28%' }}>
              Item
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '34%' }}>
              Package & Date Opened
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '18%' }}>
              Est. Shelf Life
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '12%' }}>
              Certainty
            </th>
            <th scope="col" style={{ padding: '10px 0', textAlign: 'right', width: '8%' }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {visibleItems.map((it) => {
            const conf = it.confidence ?? 1.0;
            const isUnsureCertainty = conf < 0.60;
            const isOpened = it.packageState === 'opened';

            return (
              <tr key={it.id} style={{ borderBottom: '1px solid #e5e5e5' }}>
                <td style={{ padding: '12px 0', verticalAlign: 'top' }}>
                  <select
                    aria-label={`Food classification for item ${it.id}`}
                    value={it.label}
                    onChange={(e) => updateLabel(it.id, e.target.value)}
                    style={{
                      border: it.userEdited
                        ? '2px solid var(--color-primary-accent)'
                        : '1px solid var(--color-border)',
                      padding: '6px 8px',
                      fontSize: '13px',
                      background: it.userEdited ? '#f4f6fb' : '#ffffff',
                      fontWeight: it.userEdited ? 600 : 400,
                      width: '95%',
                      minHeight: '40px',
                      textTransform: 'capitalize'
                    }}
                  >
                    {foodClasses.map((c) => (
                      <option key={c} value={c}>
                        {formatLabel(c)}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: '12px 0', verticalAlign: 'top' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <select
                      aria-label={`Package condition for ${it.label}`}
                      value={it.packageState || 'sealed'}
                      onChange={(e) => togglePackageState(it.id, e.target.value)}
                      style={{
                        border: '1px solid var(--color-border)',
                        padding: '6px 8px',
                        fontSize: '13px',
                        background: '#ffffff',
                        minHeight: '36px',
                        width: '120px'
                      }}
                    >
                      <option value="sealed">Sealed</option>
                      <option value="opened">Opened</option>
                    </select>

                    {/* Date opened picker and conservative mode */}
                    {isOpened && (
                      <div
                        style={{
                          background: '#f8f9fa',
                          border: '1px dashed var(--color-border)',
                          padding: '8px 10px',
                          borderRadius: '4px',
                          marginTop: '2px'
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '6px'
                          }}
                        >
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              color: 'var(--color-text-muted)',
                              textTransform: 'uppercase'
                            }}
                          >
                            📅 Date Opened:
                          </span>
                          <button
                            type="button"
                            onClick={() => toggleUnsureOpened(it.id)}
                            aria-pressed={it.isUnsureOpened}
                            style={{
                              background: it.isUnsureOpened ? 'var(--color-attention)' : '#ffffff',
                              color: it.isUnsureOpened ? '#ffffff' : 'var(--color-attention)',
                              border: '1px solid var(--color-attention)',
                              padding: '2px 8px',
                              fontSize: '11px',
                              fontWeight: 700,
                              cursor: 'pointer',
                              minHeight: '26px',
                              borderRadius: '3px'
                            }}
                          >
                            {it.isUnsureOpened
                              ? '✓ Unsure (Conservative FoodKeeper applied)'
                              : '? Unsure when opened'}
                          </button>
                        </div>

                        {it.isUnsureOpened ? (
                          <div
                            style={{
                              fontSize: '12px',
                              color: 'var(--color-attention)',
                              lineHeight: '1.4'
                            }}
                          >
                            <strong>Conservative safety applied:</strong> FoodKeeper minimum window of{' '}
                            {it.days} {it.days === 1 ? 'day' : 'days'} selected.
                          </div>
                        ) : (
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              flexWrap: 'wrap'
                            }}
                          >
                            <input
                              type="date"
                              value={it.openedDate || today}
                              max={today}
                              onChange={(e) => updateOpenedDate(it.id, e.target.value)}
                              aria-label={`Date opened for ${it.label}`}
                              style={{
                                border: '1px solid var(--color-border)',
                                padding: '4px 6px',
                                fontSize: '12px',
                                background: '#ffffff',
                                minHeight: '32px'
                              }}
                            />
                            <button
                              type="button"
                              onClick={() => updateOpenedDate(it.id, today)}
                              style={{
                                background: '#ffffff',
                                border: '1px solid #ccc',
                                padding: '3px 7px',
                                fontSize: '11px',
                                cursor: 'pointer',
                                minHeight: '28px'
                              }}
                            >
                              Today
                            </button>
                          </div>
                        )}

                        {it.previewExpiry && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: 'var(--color-text-muted)',
                              marginTop: '4px'
                            }}
                          >
                            Predicted Expiry: <strong>{formatDateDisplay(it.previewExpiry)}</strong>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </td>

                <td
                  style={{
                    padding: '12px 0',
                    fontSize: '13px',
                    color: '#111',
                    verticalAlign: 'top'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      aria-label={`Shelf life days remaining for ${it.label}`}
                      value={it.days}
                      onChange={(e) => updateDays(it.id, e.target.value)}
                      style={{
                        width: '56px',
                        padding: '6px 6px',
                        fontSize: '13px',
                        border: it.userEditedDays
                          ? '2px solid var(--color-primary-accent)'
                          : '1px solid var(--color-border)',
                        background: '#ffffff',
                        borderRadius: 0,
                        minHeight: '40px'
                      }}
                    />
                    <span>days</span>
                  </div>
                  {it.label === 'jar' && (
                    <div
                      style={{
                        color: 'var(--color-attention)',
                        fontSize: '12px',
                        marginTop: '4px',
                        fontWeight: 600
                      }}
                    >
                      Select food type
                    </div>
                  )}
                  {it.usdaGuidance && (
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-text-muted)',
                        marginTop: '4px',
                        lineHeight: '1.3',
                        maxWidth: '180px'
                      }}
                    >
                      {it.usdaGuidance}
                    </div>
                  )}
                </td>

                <td style={{ padding: '12px 0', fontSize: '13px', verticalAlign: 'top' }}>
                  {it.manuallyAdded ? (
                    <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>
                      Added
                    </span>
                  ) : it.userEdited ? (
                    <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>
                      Edited
                    </span>
                  ) : isUnsureCertainty ? (
                    <span style={{ color: 'var(--color-attention)', fontWeight: 600 }}>
                      Unsure ({Math.round(conf * 100)}%)
                    </span>
                  ) : (
                    <span style={{ color: 'var(--color-text-muted)' }}>
                      {Math.round(conf * 100)}%
                    </span>
                  )}
                </td>

                <td
                  style={{
                    padding: '12px 0',
                    textAlign: 'right',
                    verticalAlign: 'top'
                  }}
                >
                  <button
                    type="button"
                    onClick={() => removeItem(it.id)}
                    aria-label={`Remove ${it.label} from detected list`}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-error)',
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      fontSize: '13px',
                      fontWeight: 600,
                      minHeight: '40px',
                      padding: '6px'
                    }}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            );
          })}

          {visibleItems.length === 0 && (
            <tr>
              <td
                colSpan="5"
                style={{
                  textAlign: 'center',
                  padding: '32px 0',
                  color: 'var(--color-text-muted)',
                  fontSize: '14px'
                }}
              >
                {isDetecting
                  ? 'Analyzing image with YOLO...'
                  : 'No items match this sensitivity level. Drag the slider to the left to show more items, or click "+ Add Missed Item".'}
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={confirmAndTrack}
          disabled={visibleItems.length === 0}
          style={{
            background: visibleItems.length === 0 ? '#888888' : 'var(--color-primary-accent)',
            color: '#ffffff',
            border: 'none',
            padding: '12px 24px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: visibleItems.length === 0 ? 'not-allowed' : 'pointer',
            minHeight: '44px'
          }}
        >
          Add to Fridge Inventory ({visibleItems.length})
        </button>
        <button
          type="button"
          onClick={onBack}
          style={{
            background: '#ffffff',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
            padding: '12px 20px',
            fontSize: '14px',
            cursor: 'pointer',
            minHeight: '44px'
          }}
        >
          Back
        </button>
      </div>
    </section>
  );
}
