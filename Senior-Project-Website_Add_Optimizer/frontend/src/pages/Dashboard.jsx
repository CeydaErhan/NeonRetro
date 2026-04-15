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

function buildVisitorsByDay(events) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const dates = Array.from({ length: 7 }, (_, index) => {
    const value = new Date(today);
    value.setDate(today.getDate() - (6 - index));
    return value;
  });

  const counts = new Map(dates.map((date) => [formatDateKey(date), 0]));

  events.forEach((event) => {
    if (event?.type !== "page_view" && event?.type !== "pageview") {
      return;
    }

    const timestamp = event?.timestamp ? new Date(event.timestamp) : null;
    if (!timestamp || Number.isNaN(timestamp.getTime())) {
      return;
    }

    const key = formatDateKey(timestamp);
    if (counts.has(key)) {
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  });

  return dates.map((date) => {
    const key = formatDateKey(date);
    return {
      day: formatChartDay(date),
      visitors: counts.get(key) ?? 0
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

// Shows top-level KPIs and quick trend charts for the dashboard home.
export default function Dashboard() {
  const [summary, setSummary] = useState(initialSummary);
  const [visitorsByDay, setVisitorsByDay] = useState(() => buildVisitorsByDay([]));
  const [campaignChart, setCampaignChart] = useState({
    title: "Impressions Per Campaign",
    data: []
  });
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const headers = getAuthHeaders();
        const [summaryResponse, eventsResponse, campaignsResponse] = await Promise.all([
          api.get("/analytics/summary", { headers }),
          api.get("/events/list", { headers }),
          api.get("/campaigns", { headers })
        ]);
        const events = Array.isArray(eventsResponse.data) ? eventsResponse.data : [];
        const campaigns = Array.isArray(campaignsResponse.data) ? campaignsResponse.data : [];

        setSummary({ ...initialSummary, ...summaryResponse.data });
        setVisitorsByDay(buildVisitorsByDay(events));
        setCampaignChart(buildCampaignChartData(campaigns, events));
        setError("");
      } catch (err) {
        const detail = err?.response?.data?.detail;
        setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load dashboard metrics.");
      }
    };

    loadDashboard();
  }, []);

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
    </section>
  );
}
