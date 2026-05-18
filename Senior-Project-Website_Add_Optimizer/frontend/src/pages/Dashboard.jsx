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
  page_views: 0,
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

function buildPageViewsByDay(rows) {
  return rows.map((row) => {
    const date = row?.day ? new Date(row.day) : null;
    if (!date || Number.isNaN(date.getTime())) {
      return {
        day: "-",
        pageViews: Number(row?.visitors ?? 0)
      };
    }

    return {
      day: formatChartDay(date),
      pageViews: Number(row?.visitors ?? 0)
    };
  });
}

function buildCampaignChartData(rows) {
  return rows
    .slice(0, 6)
    .map((row) => ({
      campaign: row.campaign_name,
      impressions: Number(row.impressions ?? 0)
    }));
}

function formatPercent(value) {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

// Shows business-facing traffic and ad performance KPIs.
export default function Dashboard() {
  const [summary, setSummary] = useState(initialSummary);
  const [pageViewsByDay, setPageViewsByDay] = useState(() => buildPageViewsByDay([]));
  const [campaignPerformance, setCampaignPerformance] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      try {
        const headers = getAuthHeaders();
        const [summaryResponse, visitorsResponse, campaignPerformanceResponse] = await Promise.all([
          api.get("/analytics/summary", { headers }),
          api.get("/analytics/visitors-by-day", { headers }),
          api.get("/analytics/campaign-performance", { headers })
        ]);

        if (!isMounted) {
          return;
        }

        const visitors = Array.isArray(visitorsResponse.data) ? visitorsResponse.data : [];
        const campaigns = Array.isArray(campaignPerformanceResponse.data) ? campaignPerformanceResponse.data : [];

        setSummary({ ...initialSummary, ...summaryResponse.data });
        setPageViewsByDay(buildPageViewsByDay(visitors));
        setCampaignPerformance(campaigns);
        setError("");
      } catch (err) {
        if (!isMounted) {
          return;
        }
        const detail = err?.response?.data?.detail;
        setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load dashboard metrics.");
      }
    };

    loadDashboard();
    const intervalId = window.setInterval(loadDashboard, 5000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const kpis = [
    { label: "Total Sessions", value: summary.sessions.toLocaleString(), change: "Store traffic" },
    { label: "Page Views", value: summary.page_views.toLocaleString(), change: "Tracked storefront page loads" },
    { label: "Ad Impressions", value: summary.impressions.toLocaleString(), change: "Ads served to sessions" },
    { label: "CTR", value: formatPercent(summary.ctr), change: `${summary.clicks.toLocaleString()} ad clicks` }
  ];

  const campaignChartData = buildCampaignChartData(campaignPerformance);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Business Dashboard</h2>
        <p className="text-sm text-slate-500">Traffic, ad reach, and campaign performance from the live backend.</p>
      </div>

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

      <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 shadow-card">
        Dashboard data refreshes automatically every 5 seconds and reflects storefront traffic plus ad-serving activity.
      </article>

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">Page Views Over Last 7 Days</h2>
          <p className="mb-4 text-sm text-slate-500">Daily storefront page-load volume.</p>
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <LineChart data={pageViewsByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="day" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Line type="monotone" dataKey="pageViews" stroke="#0f172a" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">Ad Performance by Campaign</h2>
          <p className="mb-4 text-sm text-slate-500">Top campaigns ranked by total impressions.</p>
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <BarChart data={campaignChartData}>
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

      <article className="overflow-hidden rounded-2xl bg-white shadow-card">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-lg font-semibold text-slate-900">Top Campaigns</h3>
          <p className="mt-1 text-sm text-slate-500">Campaign-level impression, click, and CTR performance.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Campaign
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Impressions
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Clicks
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  CTR
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {campaignPerformance.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-4 py-6 text-sm text-slate-500">
                    No campaign performance data available yet.
                  </td>
                </tr>
              ) : (
                campaignPerformance.map((campaign) => (
                  <tr key={campaign.campaign_id}>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{campaign.campaign_name}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{campaign.impressions.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{campaign.clicks.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{formatPercent(campaign.ctr)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
