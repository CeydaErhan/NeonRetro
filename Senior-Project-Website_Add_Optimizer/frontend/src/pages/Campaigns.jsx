import { useEffect, useState } from "react";
import api from "../api/axios";

const initialForm = {
  name: "",
  status: "draft",
  start_date: "",
  end_date: "",
  target_page: ""
};

function formatStatus(status) {
  if (!status) {
    return "Unknown";
  }

  return status.charAt(0).toUpperCase() + status.slice(1);
}

// Renders campaigns table with live backend data and creation actions.
export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [form, setForm] = useState(initialForm);

  const loadCampaigns = async () => {
    setIsLoading(true);
    setError("");

    try {
      const response = await api.get("/campaigns");
      setCampaigns(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load campaigns.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  const closeModal = () => {
    setIsModalOpen(false);
    setForm(initialForm);
    setFormError("");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value
    }));
  };

  const handleCreateCampaign = async (event) => {
    event.preventDefault();
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.post("/campaigns", {
        name: form.name.trim(),
        status: form.status,
        start_date: form.start_date,
        end_date: form.end_date,
        target_page: form.target_page.trim()
      });

      await loadCampaigns();
      closeModal();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setFormError(typeof detail === "string" && detail.trim() ? detail : "Failed to create campaign.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCampaign = async (campaignId) => {
    setError("");

    try {
      await api.delete(`/campaigns/${campaignId}`);
      await loadCampaigns();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to delete campaign.");
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Campaigns</h2>
          <p className="text-sm text-slate-500">Manage website and advertisement campaign lifecycle.</p>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          New Campaign
        </button>
      </div>

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <div className="overflow-hidden rounded-2xl bg-white shadow-card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Start Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">End Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Target Page</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-sm text-slate-500">
                    Loading campaigns...
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-sm text-slate-500">
                    No campaigns found.
                  </td>
                </tr>
              ) : (
                campaigns.map((campaign) => (
                  <tr key={campaign.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{campaign.name}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{formatStatus(campaign.status)}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{campaign.start_date}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{campaign.end_date}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{campaign.target_page}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">
                      <button
                        type="button"
                        onClick={() => handleDeleteCampaign(campaign.id)}
                        className="rounded-md border border-red-200 px-3 py-1.5 text-red-700 transition hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen ? (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-card">
            <h3 className="text-lg font-semibold text-slate-900">New Campaign</h3>

            <form className="mt-4 space-y-4" onSubmit={handleCreateCampaign}>
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-medium text-slate-700">
                  Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={form.name}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
              </div>

              <div>
                <label htmlFor="status" className="mb-1 block text-sm font-medium text-slate-700">
                  Status
                </label>
                <select
                  id="status"
                  name="status"
                  value={form.status}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                >
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="start_date" className="mb-1 block text-sm font-medium text-slate-700">
                    Start Date
                  </label>
                  <input
                    id="start_date"
                    name="start_date"
                    type="date"
                    value={form.start_date}
                    onChange={handleChange}
                    required
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                  />
                </div>

                <div>
                  <label htmlFor="end_date" className="mb-1 block text-sm font-medium text-slate-700">
                    End Date
                  </label>
                  <input
                    id="end_date"
                    name="end_date"
                    type="date"
                    value={form.end_date}
                    onChange={handleChange}
                    required
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="target_page" className="mb-1 block text-sm font-medium text-slate-700">
                  Target Page
                </label>
                <input
                  id="target_page"
                  name="target_page"
                  type="text"
                  value={form.target_page}
                  onChange={handleChange}
                  required
                  placeholder="/landing-page"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
              </div>

              {formError ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>
              ) : null}

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Creating..." : "Create Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
