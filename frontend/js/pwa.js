// PWA Installation & Service Worker Lifecycle for ai4japa.store

const INSTALL_DISMISS_KEY = 'ai4japa_store_install_dismissed';
const LEGACY_INSTALL_DISMISS_KEY = 'japaai_ng_install_dismissed';
let deferredInstallPrompt = null;

function isStandalonePwa() {
  return (
    (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
    window.navigator.standalone === true
  );
}

function isIosDevice() {
  const ua = (navigator.userAgent || '').toLowerCase();
  const isTouchMac = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
  return /iphone|ipad|ipod/.test(ua) || isTouchMac;
}

function showInstallBannerIfEligible() {
  const banner = document.getElementById('pwa-install-banner');
  if (!banner) return;
  const dismissed =
    localStorage.getItem(INSTALL_DISMISS_KEY) === '1' ||
    localStorage.getItem(LEGACY_INSTALL_DISMISS_KEY) === '1';
  if (isStandalonePwa() || dismissed) {
    banner.classList.add('hidden');
    return;
  }
  const isCompactViewport = window.innerWidth <= 900 || !!deferredInstallPrompt || isIosDevice();
  banner.classList.toggle('hidden', !isCompactViewport);
}

function dismissInstallBanner() {
  localStorage.setItem(INSTALL_DISMISS_KEY, '1');
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.classList.add('hidden');
}

function openPwaInstallModal() {
  const modal = document.getElementById('pwa-install-modal');
  const title = document.getElementById('pwa-modal-title');
  const steps = document.getElementById('pwa-modal-steps');
  if (!modal || !steps) return;

  if (isIosDevice()) {
    if (title) title.textContent = 'Install ai4japa.store on iPhone / iPad';
    steps.innerHTML = [
      '<li>Tap the <strong>Share</strong> icon in your Safari toolbar (square with an upward arrow).</li>',
      '<li>Scroll down and tap <strong>Add to Home Screen</strong>.</li>',
      '<li>Tap <strong>Add</strong> in the top corner to install ai4japa.store like a native app.</li>',
    ].join('');
  } else {
    if (title) title.textContent = 'Install ai4japa.store on Android or Desktop';
    steps.innerHTML = [
      '<li>Open your browser menu (<strong>⋮</strong> on Chrome Android or <strong>⋯</strong> in your toolbar).</li>',
      '<li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>',
      '<li>Confirm to add <strong>ai4japa.store</strong> directly to your phone or desktop.</li>',
    ].join('');
  }
  modal.classList.remove('hidden');
}

function closePwaInstallModal() {
  const modal = document.getElementById('pwa-install-modal');
  if (modal) modal.classList.add('hidden');
}

async function promptPwaInstall() {
  if (isStandalonePwa()) {
    if (typeof showToast === 'function') {
      showToast('ai4japa.store is already running as an installed app.');
    }
    return;
  }
  if (deferredInstallPrompt) {
    try {
      deferredInstallPrompt.prompt();
      const choice = await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
      if (choice && choice.outcome === 'accepted') {
        dismissInstallBanner();
      }
      return;
    } catch (err) {
      deferredInstallPrompt = null;
    }
  }
  openPwaInstallModal();
}

function initPwaSupport() {
  if (isStandalonePwa()) {
    document.documentElement.classList.add('is-pwa-installed');
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(err => {
        console.warn('ServiceWorker registration skipped:', err);
      });
    });
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    showInstallBannerIfEligible();
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    document.documentElement.classList.add('is-pwa-installed');
    closePwaInstallModal();
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.add('hidden');
    if (typeof showToast === 'function') {
      showToast('ai4japa.store installed on your device!');
    }
  });

  showInstallBannerIfEligible();
}
