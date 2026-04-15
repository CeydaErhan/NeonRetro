import api from "../api/axios";

const SESSION_KEY = "optimizer_tracking_session_id";
const FLUSH_INTERVAL_MS = 30000;
const MAX_SCROLL_DEPTH = 100;
const BASE_URL = api.defaults.baseURL ?? "/api";

let eventQueue = [];
let flushTimer = null;
let scrollDepth = 0;
let pageEntryTime = Date.now();
let currentPage = "/";
let lastTrackedPage = null;
let trackingStarted = false;
let listenersAttached = false;

function getStoredSessionUuid() {
  const existing = window.localStorage.getItem(SESSION_KEY);
  if (existing) {
    return existing;
  }

  const nextId = crypto.randomUUID();
  window.localStorage.setItem(SESSION_KEY, nextId);
  return nextId;
}

function hashUuidToInt(value) {
  let hash = 0;

  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) | 0;
  }

  return Math.abs(hash) || 1;
}

function getApiSessionId() {
  return hashUuidToInt(getStoredSessionUuid());
}

function getCurrentPage() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function enqueueEvent(type, options = {}) {
  const sessionUuid = getStoredSessionUuid();
  const apiSessionId = getApiSessionId();
  const page = options.page ?? currentPage;
  const metadata = {
    client_session_uuid: sessionUuid,
    ...options.metadata
  };

  eventQueue.push({
    session_id: apiSessionId,
    type,
    page,
    element: options.element ?? null,
    metadata
  });
}

async function flushEvents() {
  if (eventQueue.length === 0) {
    return;
  }

  const pending = [...eventQueue];
  eventQueue = [];

  try {
    await Promise.all(
      pending.map((event) =>
        api.post("/events/track", {
          session_id: event.session_id,
          type: event.type,
          page: event.page,
          element: event.element,
          metadata: event.metadata
        })
      )
    );
  } catch (error) {
    eventQueue = [...pending, ...eventQueue];
    throw error;
  }
}

function scheduleFlush() {
  if (flushTimer) {
    return;
  }

  flushTimer = window.setInterval(() => {
    flushEvents().catch(() => {});
  }, FLUSH_INTERVAL_MS);
}

function trackPageView(nextPage = getCurrentPage()) {
  currentPage = nextPage;
  pageEntryTime = Date.now();

  if (lastTrackedPage === nextPage) {
    return;
  }

  lastTrackedPage = nextPage;
  scrollDepth = 0;
  enqueueEvent("page_view", {
    page: nextPage,
    metadata: {
      referrer: document.referrer || null
    }
  });
}

function trackDwellTime(nextPage = getCurrentPage()) {
  const dwellTimeMs = Date.now() - pageEntryTime;

  enqueueEvent("dwell_time", {
    page: currentPage,
    metadata: {
      dwell_time_ms: dwellTimeMs,
      next_page: nextPage
    }
  });
}

function handlePageChange() {
  const nextPage = getCurrentPage();

  if (nextPage === currentPage) {
    return;
  }

  trackDwellTime(nextPage);
  flushEvents().catch(() => {});
  trackPageView(nextPage);
}

function handleClick(event) {
  const target = event.target instanceof Element ? event.target.closest("button, a, input, [data-track-click]") : null;

  if (!target) {
    return;
  }

  enqueueEvent("click", {
    element: target.tagName.toLowerCase(),
    metadata: {
      text: target.textContent?.trim().slice(0, 120) || null,
      id: target.id || null,
      class_name: target.className || null
    }
  });
}

function handleScroll() {
  const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (documentHeight <= 0) {
    return;
  }

  const nextDepth = Math.min(
    MAX_SCROLL_DEPTH,
    Math.round((window.scrollY / documentHeight) * 100)
  );

  if (nextDepth < scrollDepth + 25 && nextDepth !== MAX_SCROLL_DEPTH) {
    return;
  }

  if (nextDepth <= scrollDepth) {
    return;
  }

  scrollDepth = nextDepth;
  enqueueEvent("scroll_depth", {
    metadata: {
      percent: nextDepth
    }
  });
}

function handleVisibilityChange() {
  if (document.visibilityState === "hidden") {
    trackDwellTime(currentPage);
    flushEvents().catch(() => {});
    pageEntryTime = Date.now();
  }
}

function patchHistoryMethod(methodName) {
  const original = window.history[methodName];

  window.history[methodName] = function patchedHistoryMethod(...args) {
    const result = original.apply(this, args);
    window.dispatchEvent(new Event("tracker:navigation"));
    return result;
  };
}

function attachListeners() {
  if (listenersAttached) {
    return;
  }

  listenersAttached = true;
  document.addEventListener("click", handleClick, true);
  window.addEventListener("scroll", handleScroll, { passive: true });
  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("beforeunload", () => {
    trackDwellTime(currentPage);
  });
  window.addEventListener("pagehide", () => {
    flushEvents().catch(() => {});
  });
  window.addEventListener("popstate", handlePageChange);
  window.addEventListener("tracker:navigation", handlePageChange);

  patchHistoryMethod("pushState");
  patchHistoryMethod("replaceState");
}

export function getTrackingSessionId() {
  return getStoredSessionUuid();
}

export function trackEvent(type, payload = {}) {
  enqueueEvent(type, payload);
}

export function trackClick(element) {
  fetch(`${BASE_URL}/events/track`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: getApiSessionId(),
      type: "click",
      element,
      page: window.location.pathname
    })
  });
}

export function startTracking() {
  if (trackingStarted) {
    return;
  }

  trackingStarted = true;
  currentPage = getCurrentPage();
  attachListeners();
  trackPageView(currentPage);
  scheduleFlush();
}

export async function flushTracking() {
  await flushEvents();
}
