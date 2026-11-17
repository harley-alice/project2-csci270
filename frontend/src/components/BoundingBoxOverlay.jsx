import React from 'react';

/**
 * BoundingBoxOverlay
 * Renders an image container with responsive YOLO bounding boxes and labels.
 * Supports interactive manual box drawing for human-in-the-loop active learning.
 */
export default function BoundingBoxOverlay({
  image,
  visibleItems,
  isDrawingMode,
  currentBox,
  imageContainerRef,
  imgElementRef,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  formatLabel = (l) => l
}) {
  return (
    <div style={{ textAlign: 'center', marginBottom: '24px' }}>
      <div
        ref={imageContainerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{
          display: 'inline-block',
          position: 'relative',
          lineHeight: 0,
          border: isDrawingMode ? '2px solid var(--color-primary-accent, #0052cc)' : '1px solid var(--color-border, #e0e0e0)',
          background: '#000000',
          cursor: isDrawingMode ? 'crosshair' : 'default',
          userSelect: 'none',
          maxWidth: '100%',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
        }}
      >
        <img
          ref={imgElementRef}
          src={image}
          alt="Scanned fridge interior preview"
          draggable={false}
          style={{
            display: 'block',
            maxWidth: '100%',
            maxHeight: '520px',
            width: 'auto',
            height: 'auto',
            pointerEvents: 'none'
          }}
        />

        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible'
          }}
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {visibleItems.map((it) => {
            if (!it.bbox || !Array.isArray(it.bbox) || it.bbox.length < 4) return null;
            const [ymin, xmin, ymax, xmax] = it.bbox;
            const conf = it.confidence ?? 1.0;
            const isUnsure = conf < 0.60;

            const strokeColor = it.userEdited
              ? 'var(--color-accent, #faad14)'
              : isUnsure
              ? 'var(--color-attention, #d4380d)'
              : 'var(--color-primary-accent, #1890ff)';

            const x = xmin * 1000;
            const y = ymin * 1000;
            const w = Math.max(4, (xmax - xmin) * 1000);
            const h = Math.max(4, (ymax - ymin) * 1000);
            const labelText = `${formatLabel(it.label)} (${Math.round(conf * 100)}%)`;
            const badgeWidth = Math.max(70, labelText.length * 8.5 + 16);

            return (
              <g key={it.id}>
                {/* Translucent fill inside the box */}
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={isUnsure ? 'rgba(212, 56, 13, 0.12)' : 'rgba(24, 144, 255, 0.12)'}
                  stroke={strokeColor}
                  strokeWidth="3"
                />
                {/* Label header background */}
                <rect
                  x={x}
                  y={Math.max(0, y - 22)}
                  width={badgeWidth}
                  height="22"
                  fill={strokeColor}
                />
                {/* Label text */}
                <text
                  x={x + 6}
                  y={Math.max(16, y - 6)}
                  fill={it.userEdited ? '#000000' : '#ffffff'}
                  fontSize="12"
                  fontWeight="bold"
                  fontFamily="system-ui, -apple-system, sans-serif"
                >
                  {labelText}
                </text>
              </g>
            );
          })}

          {/* In-progress drawing preview box */}
          {isDrawingMode && currentBox && (
            <rect
              x={currentBox.xmin * 1000}
              y={currentBox.ymin * 1000}
              width={(currentBox.xmax - currentBox.xmin) * 1000}
              height={(currentBox.ymax - currentBox.ymin) * 1000}
              fill="rgba(250, 173, 20, 0.25)"
              stroke="var(--color-accent, #faad14)"
              strokeWidth="3"
              strokeDasharray="6,4"
            />
          )}
        </svg>
      </div>
    </div>
  );
}
