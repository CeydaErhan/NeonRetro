const BASE_URL = 'https://senior-project-website-add-optimizer.onrender.com';

function getPageName() {
  const path = window.location.pathname;
  if (path.includes('product')) return 'product';
  if (path.includes('cart')) return 'cart';
  if (path.includes('clothes')) return 'clothes';
  if (path.includes('cosmetics')) return 'cosmetics';
  return 'home';
}

async function initSession() {
  if (localStorage.getItem('session_id')) return;
  const res = await fetch(BASE_URL + '/visitor-sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({user_agent: navigator.userAgent, referrer: document.referrer})
  });
  const data = await res.json();
  localStorage.setItem('session_id', data.id);
}

async function trackPageview() {
  await fetch(BASE_URL + '/events/track', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'omit',
    body: JSON.stringify({
      session_id: parseInt(localStorage.getItem('session_id')),
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
      session_id: parseInt(localStorage.getItem('session_id')),
      type: 'click',
      element: element,
      page: getPageName()
    })
  }).catch(() => {});
}

document.addEventListener('click', e => {
  const el = e.target.closest('[data-track]');
  if (el) trackClick(el.dataset.track);
});
