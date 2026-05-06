import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import api from "../api/axios";

const TOKEN_KEY = "optimizer_jwt_token";
const initialSummary = {
  sessions: 0,
  events: 0,
  ads: 0,
  impressions: 0,
  clicks: 0,
  ctr: 0
};

function buildAuthorizationHeader(token) {
  if (!token) {
    return null;
  }

  return token.startsWith("Bearer ") ? token : `Bearer ${token}`;
}

function getAuthHeaders() {
  const token = window.localStorage.getItem(TOKEN_KEY);
  const authorization = buildAuthorizationHeader(token);
  return authorization ? { Authorization: authorization } : {};
}

function formatChartDay(date) {
  return new Intl.DateTimeFormat("en-US", { weekday: "short" }).format(date);
}

function formatDateKey(date) {
  return date.toISOString().slice(0, 10);
}

function buildVisitorsByDay(rows) {
  return rows.map((row) => {
    const date = row?.day ? new Date(row.day) : null;
    if (!date || Number.isNaN(date.getTime())) {
      return {
        day: "-",
        visitors: Number(row?.visitors ?? 0)
      };
    }

    return {
      day: formatChartDay(date),
      visitors: Number(row?.visitors ?? 0)
    };
  });
}

function buildCampaignChartData(campaigns, events) {
  const campaignData = campaigns
    .filter((campaign) => typeof campaign?.name === "string" && campaign.name.trim())
    .map((campaign) => ({
      label: campaign.name,
      value: Number(campaign.impressions ?? 0)
    }));

  if (campaignData.some((item) => item.value > 0)) {
    return {
      title: "Impressions Per Campaign",
      data: campaignData.map((item) => ({
        campaign: item.label,
        impressions: item.value
      }))
    };
  }

  const pageCounts = new Map();
  events.forEach((event) => {
    const page = typeof event?.page === "string" && event.page.trim() ? event.page : "Unknown";
    pageCounts.set(page, (pageCounts.get(page) ?? 0) + 1);
  });

  const fallbackData = [...pageCounts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 6)
    .map(([page, count]) => ({
      campaign: page,
      impressions: count
    }));

  return {
    title: "Event Counts Per Page",
    data: fallbackData
  };
}

function formatDemoValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not returned";
  }

  return String(value);
}

// Shows top-level KPIs and quick trend charts for the dashboard home.
export default function Dashboard() {
  const [summary, setSummary] = useState(initialSummary);
  const [visitorsByDay, setVisitorsByDay] = useState(() => buildVisitorsByDay([]));
  const [campaignChart, setCampaignChart] = useState({
    title: "Impressions Per Campaign",
    data: []
  });
  const [error, setError] = useState("");
  const [demoPage, setDemoPage] = useState("home");
  const [demoSessionId, setDemoSessionId] = useState("");
  const [demoPlacement, setDemoPlacement] = useState(undefined);
  const [demoError, setDemoError] = useState("");
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const headers = getAuthHeaders();
        const [summaryResponse, visitorsResponse, eventsResponse, campaignsResponse] = await Promise.all([
          api.get("/analytics/summary", { headers }),
          api.get("/analytics/visitors-by-day", { headers }),
          api.get("/events/list", { headers }),
          api.get("/campaigns", { headers })
        ]);
        const events = Array.isArray(eventsResponse.data) ? eventsResponse.data : [];
        const campaigns = Array.isArray(campaignsResponse.data) ? campaignsResponse.data : [];
        const visitors = Array.isArray(visitorsResponse.data) ? visitorsResponse.data : [];

        setSummary({ ...initialSummary, ...summaryResponse.data });
        setVisitorsByDay(buildVisitorsByDay(visitors));
        setCampaignChart(buildCampaignChartData(campaigns, events));
        setError("");
      } catch (err) {
        const detail = err?.response?.data?.detail;
        setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load dashboard metrics.");
      }
    };

    loadDashboard();
  }, []);

  const handlePlacementDemo = async (event) => {
    event.preventDefault();
    setIsDemoLoading(true);
    setDemoError("");
    setDemoPlacement(undefined);

    const page = demoPage.trim() || "home";
    const sessionId = demoSessionId.trim();
    const params = { page };

    if (sessionId) {
      params.session_id = sessionId;
    }

    try {
      const response = await api.get("/ads/placement", { params });
      setDemoPage(page);
      setDemoPlacement(response.data ?? null);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setDemoError(typeof detail === "string" && detail.trim() ? detail : "Failed to load ad placement.");
    } finally {
      setIsDemoLoading(false);
    }
  };

  const kpis = [
    { label: "Total Sessions", value: summary.sessions.toLocaleString(), change: "Live data" },
    { label: "Tracked Events", value: summary.events.toLocaleString(), change: "Live data" },
    { label: "Total Impressions", value: summary.impressions.toLocaleString(), change: "Live data" },
    { label: "Avg CTR", value: `${(summary.ctr * 100).toFixed(2)}%`, change: `${summary.clicks.toLocaleString()} clicks` }
  ];

  return (
    <section className="space-y-6">
      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((item) => (
          <article key={item.label} className="rounded-2xl bg-white p-5 shadow-card">
            <p className="text-sm text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">{item.value}</p>
            <p className="mt-1 text-sm text-emerald-600">{item.change}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Visitors Over Last 7 Days</h2>
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <LineChart data={visitorsByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="day" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Line type="monotone" dataKey="visitors" stroke="#0f172a" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">{campaignChart.title}</h2>
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <BarChart data={campaignChart.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="campaign" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Bar dataKey="impressions" fill="#334155" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </div>

      <article className="rounded-2xl bg-white p-5 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">ML Placement Demo</h2>
            <p className="mt-1 text-sm text-slate-500">Run the storefront placement endpoint for a page and session.</p>
          </div>
        </div>

        <form className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_auto]" onSubmit={handlePlacementDemo}>
          <div>
            <label htmlFor="placement-page" className="mb-1 block text-sm font-medium text-slate-700">
              Page
            </label>
            <input
              id="placement-page"
              type="text"
              value={demoPage}
              onChange={(event) => setDemoPage(event.target.value)}
              placeholder="home"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
            />
          </div>

          <div>
            <label htmlFor="placement-session" className="mb-1 block text-sm font-medium text-slate-700">
              Session ID
            </label>
            <input
              id="placement-session"
              type="text"
              value={demoSessionId}
              onChange={(event) => setDemoSessionId(event.target.value)}
              placeholder="123"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isDemoLoading}
              className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
            >
              {isDemoLoading ? "Loading..." : "Run Placement Demo"}
            </button>
          </div>
        </form>

        {demoError ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{demoError}</p>
        ) : null}

        {demoPlacement === null ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            No ad returned for this placement.
          </p>
        ) : null}

        {demoPlacement ? (
          <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(260px,360px)]">
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ad Preview</p>
              <h3 className="mt-2 text-lg font-semibold text-slate-900">{formatDemoValue(demoPlacement.title)}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{formatDemoValue(demoPlacement.content)}</p>
              {demoPlacement.image_url ? (
                <img
                  src={demoPlacement.image_url}
                  alt={demoPlacement.title || "Placement ad"}
                  className="mt-4 h-44 w-full rounded-lg object-cover"
                />
              ) : null}
            </div>

            <dl className="grid gap-3 rounded-xl border border-slate-200 p-4 text-sm">
              {[
                ["Segment", demoPlacement.segment],
                ["Segment Label", demoPlacement.segment_label],
                ["Ranking Strategy", demoPlacement.ranking_strategy],
                ["Model Version", demoPlacement.model_version],
                ["Backend Explanation", demoPlacement.explanation],
                ["Impression ID", demoPlacement.impression_id]
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
                  <dd className="mt-1 break-words font-medium text-slate-900">{formatDemoValue(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}
      </article>
    </section>
  );
}
