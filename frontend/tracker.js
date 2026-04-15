const BASE_URL = 'https://senior-project-website-add-optimizer.onrender.com';
let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

function getPageName() {
  const path = window.location.pathname;
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

async function trackPageview() {
  await fetch(BASE_URL + '/events/track', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      session_id: sessionId,
      type: 'pageview',
      page: getPageName()
    })
  });
}

function trackClick(element) {
  fetch(BASE_URL + '/events/track', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      session_id: sessionId,
      type: 'click',
      element: element,
      page: getPageName()
    })
  }).catch(() => {});
}

function track(type, element, extra = {}) {
  fetch(BASE_URL + '/events/track', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      session_id: sessionId,
      type,
      element,
      page: getPageName(),
      ...extra
    })
  }).catch(() => {});
}

window.tracker = { track };

document.addEventListener('click', e => {
  const el = e.target.closest('[data-track]');
  if (el) trackClick(el.dataset.track);
});
