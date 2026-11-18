import React from 'react';

/**
 * CaptureSection component.
 * Allows the user to take a live photo of fridge contents using their webcam/camera,
 * or select an image file from their device.
 */
export default function CaptureSection({
  isCameraActive,
  videoRef,
  startCamera,
  stopCamera,
  capturePhoto,
  handleFile
}) {
  return (
    <section aria-labelledby="capture-heading">
      <h2
        id="capture-heading"
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
        Capture or Upload Food Photo
      </h2>

      {isCameraActive ? (
        <div
          style={{
            border: '2px solid var(--color-border)',
            marginBottom: '24px',
            background: '#000',
            textAlign: 'center'
          }}
        >
          <video
            ref={videoRef}
            autoPlay
            playsInline
            aria-label="Live camera preview of fridge shelf"
            style={{
              width: '100%',
              maxHeight: '440px',
              display: 'block',
              objectFit: 'cover'
            }}
          />
          <div
            style={{
              padding: '16px',
              background: '#ffffff',
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              gap: '12px',
              justifyContent: 'center'
            }}
          >
            <button
              type="button"
              onClick={capturePhoto}
              style={{
                background: 'var(--color-primary-accent)',
                color: '#ffffff',
                border: 'none',
                padding: '12px 24px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              Snap Photo
            </button>
            <button
              type="button"
              onClick={stopCamera}
              style={{
                background: '#ffffff',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '12px 18px',
                fontSize: '14px',
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div
          style={{
            border: '2px dashed var(--color-border)',
            padding: '64px 24px',
            textAlign: 'center',
            marginBottom: '24px',
            background: '#fafafa'
          }}
        >
          <p style={{ marginBottom: '24px', fontSize: '16px' }}>
            Scan your fridge shelves using your camera or upload a photo.
          </p>

          <div
            style={{
              display: 'flex',
              gap: '14px',
              justifyContent: 'center',
              flexWrap: 'wrap'
            }}
          >
            <button
              type="button"
              onClick={startCamera}
              style={{
                background: 'var(--color-primary-accent)',
                color: '#ffffff',
                padding: '12px 24px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                border: 'none',
                minHeight: '44px'
              }}
            >
              Open Live Camera
            </button>

            <label
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                background: '#ffffff',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '12px 24px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              Upload Image
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/jpg,image/heic,image/heif,.heic,.heif"
                onChange={handleFile}
                aria-label="Upload fridge image"
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
              />
            </label>
          </div>
        </div>
      )}
    </section>
  );
}
