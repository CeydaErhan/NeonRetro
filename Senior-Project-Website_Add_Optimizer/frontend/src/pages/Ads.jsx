import { useEffect, useState } from "react";
import api from "../api/axios";

const initialForm = {
  campaign_id: "",
  title: "",
  content: "",
  image_url: "",
  target_page: ""
};

function summarizeContent(content) {
  if (!content) {
    return "-";
  }

  return content.length > 90 ? `${content.slice(0, 90)}...` : content;
}

// Renders ad inventory management with simple create and delete actions.
export default function Ads() {
  const [ads, setAds] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [form, setForm] = useState(initialForm);

  const loadAds = async () => {
    setIsLoading(true);
    setError("");

    try {
      const response = await api.get("/ads");
      setAds(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load ads.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAds();
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

  const handleCreateAd = async (event) => {
    event.preventDefault();
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.post("/ads", {
        campaign_id: Number(form.campaign_id),
        title: form.title.trim(),
        content: form.content.trim(),
        image_url: form.image_url.trim() || null,
        target_page: form.target_page.trim()
      });

      await loadAds();
      closeModal();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setFormError(typeof detail === "string" && detail.trim() ? detail : "Failed to create ad.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAd = async (adId) => {
    setError("");

    try {
      await api.delete(`/ads/${adId}`);
      await loadAds();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to delete ad.");
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Ads</h2>
          <p className="text-sm text-slate-500">
            Manage marketing ad units used by placement workflows. These are not storefront product inventory.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          New Ad
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
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Campaign ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Target Page
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Preview</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Content</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan="7" className="px-4 py-6 text-sm text-slate-500">
                    Loading ads...
                  </td>
                </tr>
              ) : ads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-6 text-sm text-slate-500">
                    No ads found.
                  </td>
                </tr>
              ) : (
                ads.map((ad) => (
                  <tr key={ad.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{ad.id}</td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{ad.title}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{ad.campaign_id}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{ad.target_page}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">
                      {ad.image_url ? (
                        <img src={ad.image_url} alt={ad.title} className="h-12 w-20 rounded-md object-cover" />
                      ) : (
                        <span className="text-slate-400">No image</span>
                      )}
                    </td>
                    <td className="max-w-xs px-4 py-3 text-sm leading-6 text-slate-700">
                      {summarizeContent(ad.content)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700">
                      <button
                        type="button"
                        onClick={() => handleDeleteAd(ad.id)}
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
            <h3 className="text-lg font-semibold text-slate-900">New Ad</h3>

            <form className="mt-4 space-y-4" onSubmit={handleCreateAd}>
              <div>
                <label htmlFor="campaign_id" className="mb-1 block text-sm font-medium text-slate-700">
                  Campaign ID
                </label>
                <input
                  id="campaign_id"
                  name="campaign_id"
                  type="number"
                  min="1"
                  value={form.campaign_id}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
              </div>

              <div>
                <label htmlFor="title" className="mb-1 block text-sm font-medium text-slate-700">
                  Title
                </label>
                <input
                  id="title"
                  name="title"
                  type="text"
                  value={form.title}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
              </div>

              <div>
                <label htmlFor="content" className="mb-1 block text-sm font-medium text-slate-700">
                  Content
                </label>
                <textarea
                  id="content"
                  name="content"
                  value={form.content}
                  onChange={handleChange}
                  required
                  rows="4"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
              </div>

              <div>
                <label htmlFor="image_url" className="mb-1 block text-sm font-medium text-slate-700">
                  Image URL
                </label>
                <input
                  id="image_url"
                  name="image_url"
                  type="url"
                  value={form.image_url}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-slate-300 transition focus:ring"
                />
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
                  placeholder="home"
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
                  {isSubmitting ? "Creating..." : "Create Ad"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
