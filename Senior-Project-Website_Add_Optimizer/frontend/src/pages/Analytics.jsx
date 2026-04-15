import { useEffect, useState } from "react";
import api from "../api/axios";

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString();
}

// Displays recent tracked events from the backend analytics API.
export default function Analytics() {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadEvents = async () => {
      setIsLoading(true);
      setError("");

      try {
        const response = await api.get("/events/list", {
          params: {
            limit: 20
          }
        });
        setEvents(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        const detail = err?.response?.data?.detail;
        setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load recent events.");
      } finally {
        setIsLoading(false);
      }
    };

    loadEvents();
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Analytics</h2>
        <p className="text-sm text-slate-500">Recent tracked visitor and interaction events from the backend.</p>
      </div>

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <article className="overflow-hidden rounded-2xl bg-white shadow-card">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-lg font-semibold text-slate-900">Recent Events</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Page</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Element</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Session</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-sm text-slate-500">
                    Loading recent events...
                  </td>
                </tr>
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-sm text-slate-500">
                    No events found.
                  </td>
                </tr>
              ) : (
                events.map((event) => (
                  <tr key={event.id}>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{event.type}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{event.page}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{event.element || "-"}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{event.session_id}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{formatTimestamp(event.timestamp)}</td>
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
