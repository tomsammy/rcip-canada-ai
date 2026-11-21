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

  const IMAGE_VERSION = 'v=7';

  const COUNTRY_MEDIA = {
    canada: {
      src: `/static/images/dest-canada.webp?${IMAGE_VERSION}`,
      alt: 'Scenic Canadian waterfront skyline backed by pine forests and mountain peaks',
      focal: 'center 42%',
    },
    uk: {
      src: `/static/images/dest-uk.webp?${IMAGE_VERSION}`,
      alt: 'London waterfront along the River Thames combining stone heritage facades and glass towers',
      focal: 'center 45%',
    },
    usa: {
      src: `/static/images/dest-usa.webp?${IMAGE_VERSION}`,
      alt: 'Sunlit American waterfront promenade and modern metropolitan skyline',
      focal: 'center 45%',
    },
    germany: {
      src: `/static/images/dest-central-europe.webp?${IMAGE_VERSION}`,
      alt: 'Central European architectural canal promenade lined with trees and heritage buildings',
      focal: 'center',
    },
    netherlands: {
      src: `/static/images/dest-central-europe.webp?${IMAGE_VERSION}`,
      alt: 'Dutch canal waterfront promenade lined with heritage architecture and green trees',
      focal: 'center',
    },
    spain: {
      src: `/static/images/dest-southern-europe.webp?${IMAGE_VERSION}`,
      alt: 'Sunlit Southern European coastal boulevard and limestone promenade terraces',
      focal: 'center',
    },
    france: {
      src: `/static/images/dest-southern-europe.webp?${IMAGE_VERSION}`,
      alt: 'Sunlit European architectural boulevard and coastal skyline under clear sky',
      focal: 'center',
    },
    sweden: {
      src: `/static/images/dest-nordic-baltic.webp?${IMAGE_VERSION}`,
      alt: 'Nordic waterfront combining historic gabled buildings and Scandinavian timber-glass architecture',
      focal: 'center',
    },
    estonia: {
      src: `/static/images/dest-nordic-baltic.webp?${IMAGE_VERSION}`,
      alt: 'Nordic-Baltic harbour blending historic rooftops with contemporary waterfront architecture',
      focal: 'center',
    },
    lithuania: {
      src: `/static/images/dest-nordic-baltic.webp?${IMAGE_VERSION}`,
      alt: 'Clean Northern-Baltic waterfront skyline surrounded by calm blue water and parkland',
      focal: 'center',
    },
    bulgaria: {
      src: `/static/images/dest-nordic-baltic.webp?${IMAGE_VERSION}`,
      alt: 'Historic European waterfront and sunlit civic rooftops framed by parkland',
      focal: 'center',
    },
    brazil: {
      src: `/static/images/dest-brazil.webp?${IMAGE_VERSION}`,
      alt: 'Brazilian oceanfront skyline along a golden bay framed by lush green tropical peaks',
      focal: 'center',
    },
  };

  const FEATURED_SHOWCASE_IDS = ['canada', 'uk', 'usa', 'germany', 'spain', 'sweden', 'brazil'];

  function getCountryMedia(countryId) {
    const key = String(countryId || '').trim().toLowerCase();
    return (
      COUNTRY_MEDIA[key] || {
        src: `/static/images/hero-global-mobility.webp?${IMAGE_VERSION}`,
        alt: 'Global immigration destination skyline',
        focal: 'center',
      }
    );
  }

  const api = {
    esc,
    formatSyncTimestamp,
    resolveHeroSyncStatusText,
    migrateBrowserState,
    isValidUploadSize,
    IMAGE_VERSION,
    COUNTRY_MEDIA,
    FEATURED_SHOWCASE_IDS,
    getCountryMedia,
  };

  if (root) {
    root.JapaUtils = api;
    root.esc = esc;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : window);
