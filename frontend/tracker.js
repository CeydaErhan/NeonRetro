function resolveBaseUrl() {
  if (window.NEON_API_BASE_URL) {
    return window.NEON_API_BASE_URL.replace(/\/$/, '');
  }

  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:10000';
  }

  return 'https://senior-project-website-add-optimizer.onrender.com';
}

const BASE_URL = resolveBaseUrl();
const SESSION_KEY = 'neonretro_tracking_session_id';
let sessionIdPromise = null;

function getStoredSessionId() {
  const stored = window.localStorage.getItem(SESSION_KEY);
  if (stored) {
    return Number(stored);
  }
  return null;
}

async function createVisitorSession() {
  const response = await fetch(BASE_URL + '/visitor-sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      user_agent: navigator.userAgent || 'unknown',
      referrer: document.referrer || window.location.origin || 'direct'
    })
  });

  if (!response.ok) {
    throw new Error('Failed to create visitor session');
  }

  const payload = await response.json();
  const sessionId = Number(payload?.id);
  if (!Number.isInteger(sessionId) || sessionId <= 0) {
    throw new Error('Backend returned an invalid visitor session id');
  }

  window.localStorage.setItem(SESSION_KEY, String(sessionId));
  return sessionId;
}

async function getSessionId() {
  const stored = getStoredSessionId();
  if (stored) {
    return stored;
  }

  if (!sessionIdPromise) {
    sessionIdPromise = createVisitorSession()
      .catch(() => null)
      .finally(() => {
        sessionIdPromise = null;
      });
  }

  return sessionIdPromise;
}

function getPageName() {
  const path = window.location.pathname;
  const categoryParam = new URLSearchParams(window.location.search).get('cat');
  if (categoryParam) return categoryParam;
  if (path.includes('product')) return 'product';
  if (path.includes('cart')) return 'cart';
  if (path.includes('checkout')) return 'checkout';
  if (path.includes('search')) return 'search';
  if (path.includes('clothing')) return 'clothing';
  if (path.includes('beauty')) return 'beauty';
  if (path.includes('home-appliances')) return 'home-appliances';
  if (path.includes('books')) return 'books';
  if (path.includes('sports')) return 'sports';
  if (path.includes('electronics')) return 'electronics';
  return 'home';
}

async function sendEvent(payload) {
  const sessionId = await getSessionId();
  if (!sessionId) {
    return null;
  }
  return fetch(BASE_URL + '/events/track', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      ...payload,
      session_id: sessionId
    })
  }).catch(() => {});
}

async function trackPageview(metadata = {}) {
  await sendEvent({
    type: 'page_view',
    page: getPageName(),
    metadata
  });
}

function trackClick(element, metadata = {}) {
  sendEvent({
    type: 'click',
    element,
    page: getPageName(),
    metadata
  });
}

function track(type, element, extra = {}) {
  const metadata = {
    ...(extra.metadata || {}),
    ...Object.fromEntries(
      Object.entries(extra).filter(([key]) => key !== 'metadata')
    )
  };

  sendEvent({
    type,
    element,
    page: getPageName(),
    metadata
  });
}

window.tracker = { track, trackClick, trackPageview, getSessionId };

document.addEventListener('click', e => {
  const el = e.target.closest('[data-track]');
  if (el) trackClick(el.dataset.track);
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    trackPageview({
      path: window.location.pathname,
      query: window.location.search || null
    });
  }, { once: true });
} else {
  trackPageview({
    path: window.location.pathname,
    query: window.location.search || null
  });
}
