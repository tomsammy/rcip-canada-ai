// Pure frontend utilities for JapaAI.ng (browser global + CommonJS testable in Node)

(function attachJapaUtils(root) {
  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatSyncTimestamp(isoTs) {
    if (!isoTs) return '';
    return String(isoTs).replace('T', ' ').replace('+00:00', ' UTC').trim();
  }

  function resolveHeroSyncStatusText(lastSyncedAt, liveCount) {
    if (lastSyncedAt) {
      const cleanTs = formatSyncTimestamp(lastSyncedAt);
      const countLabel = Number(liveCount) > 0 ? String(liveCount) : 'Live';
      return `Direct official portals · ${countLabel} live snapshots verified (${cleanTs})`;
    }
    return 'Direct official sources · No additions or middlemen · Updated in real time';
  }

  function migrateBrowserState(primaryRaw, legacyRaw) {
    const raw = primaryRaw || legacyRaw;
    if (!raw || typeof raw !== 'string') return null;
    try {
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
    } catch (err) {
      return null;
    }
  }

  function isValidUploadSize(byteLength, maxBytes) {
    return typeof byteLength === 'number' && Number.isFinite(byteLength) && byteLength > 0 && byteLength <= maxBytes;
  }

  const api = {
    esc,
    formatSyncTimestamp,
    resolveHeroSyncStatusText,
    migrateBrowserState,
    isValidUploadSize,
  };

  if (root) {
    root.JapaUtils = api;
    root.esc = esc;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : window);
