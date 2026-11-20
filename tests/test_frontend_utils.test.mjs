import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const {
  esc,
  formatSyncTimestamp,
  resolveHeroSyncStatusText,
  migrateBrowserState,
  isValidUploadSize,
} = require('../frontend/js/utils.js');

test('esc sanitizes HTML special characters and handles nullish values', () => {
  assert.equal(esc(null), '');
  assert.equal(esc(undefined), '');
  assert.equal(
    esc(`<script>alert("x" & 'y')</script>`),
    '&lt;script&gt;alert(&quot;x&quot; &amp; &#39;y&#39;)&lt;/script&gt;'
  );
});

test('formatSyncTimestamp and resolveHeroSyncStatusText format live status accurately', () => {
  assert.equal(formatSyncTimestamp('2026-11-20T17:49:53+00:00'), '2026-11-20 17:49:53 UTC');
  assert.equal(
    resolveHeroSyncStatusText('2026-11-20T17:49:53+00:00', 14),
    'Direct official portals · 14 live snapshots verified (2026-11-20 17:49:53 UTC)'
  );
  assert.equal(
    resolveHeroSyncStatusText('', 0),
    'Direct official sources · No additions or middlemen · Updated in real time'
  );
});

test('migrateBrowserState prefers primary storage, falls back to legacy, and rejects malformed JSON', () => {
  const primary = JSON.stringify({ profile: { name: 'A' } });
  const legacy = JSON.stringify({ profile: { name: 'Legacy' } });

  assert.deepEqual(migrateBrowserState(primary, legacy), { profile: { name: 'A' } });
  assert.deepEqual(migrateBrowserState(null, legacy), { profile: { name: 'Legacy' } });
  assert.equal(migrateBrowserState('{bad json', null), null);
  assert.equal(migrateBrowserState('[1,2,3]', null), null);
});

test('isValidUploadSize enforces positive non-empty size up to cap', () => {
  const cap = 4404019;
  assert.equal(isValidUploadSize(0, cap), false);
  assert.equal(isValidUploadSize(1024, cap), true);
  assert.equal(isValidUploadSize(cap, cap), true);
  assert.equal(isValidUploadSize(cap + 1, cap), false);
});
