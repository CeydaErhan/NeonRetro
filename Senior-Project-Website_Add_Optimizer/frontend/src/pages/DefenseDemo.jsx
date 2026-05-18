import { useEffect, useMemo, useState } from "react";
import api from "../api/axios";

const TOKEN_KEY = "optimizer_jwt_token";
const MODEL_WARNING = "ML model is missing. Demo is in fallback mode.";

const scenarioButtons = [
  {
    key: "casual",
    label: "Run Casual Visitor Scenario",
    description: "Short browse, low product depth"
  },
  {
    key: "interested",
    label: "Run Interested Visitor Scenario",
    description: "Category interest with product interaction"
  },
  {
    key: "high-intent",
    label: "Run High Intent Visitor Scenario",
    description: "Deep comparison and add-to-cart behavior"
  }
];

const pipelineSteps = ["Visitor Behavior", "Feature Extraction", "KMeans Model", "Segment", "Ad Decision"];

const scenarioExplanations = {
  casual: ["low activity", "few clicks/pages", "weak purchase intent"],
  interested: ["moderate browsing", "some product/category interest", "medium engagement"],
  "high-intent": ["stronger click/product signals", "add-to-cart or attribute-selection behavior", "higher commercial intent"]
};

const segmentExplanationRows = [
  ["Low", "Light browsing with limited interaction depth", "least_exposed_ads", "Introduce under-exposed campaigns without over-optimizing for intent"],
  ["Medium", "Category and product interest with moderate engagement", "impression_popularity", "Show proven ads to visitors who are actively comparing options"],
  ["High", "Repeated product signals, attribute choices, or cart behavior", "ctr_performance", "Prioritize ads with stronger click-through performance for commercial intent"]
];

const featureRows = [
  ["page_count", "Page Count"],
  ["click_count", "Click Count"],
  ["dwell_time_seconds", "Dwell Time Seconds"],
  ["unique_products", "Unique Products"],
  ["add_to_cart_count", "Add To Cart Count"],
  ["attribute_selection_count", "Attribute Selection Count"],
  ["avg_price", "Average Price"],
  ["price_stddev", "Price Stddev"],
  ["category_diversity", "Category Diversity"],
  ["electronics_ratio", "Electronics Ratio"],
  ["clothing_ratio", "Clothing Ratio"],
  ["beauty_ratio", "Beauty Ratio"],
  ["home_appliances_ratio", "Home Appliances Ratio"],
  ["books_ratio", "Books Ratio"],
  ["sports_ratio", "Sports Ratio"]
];

function getAuthHeaders() {
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) {
    return {};
  }
  return { Authorization: token.startsWith("Bearer ") ? token : `Bearer ${token}` };
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not returned";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
  }
  return String(value);
}

function formatMetadataValue(value, fallback = "not available for this model artifact") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return formatValue(value);
}

function titleCase(value) {
  if (!value) {
    return "Not returned";
  }
  return String(value)
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function isRealMlPlacement(placement) {
  return placement?.explanation === "ml:kmeans_segment_placement";
}

function Pipeline({ active }) {
  return (
    <div className="grid gap-3 lg:grid-cols-5">
      {pipelineSteps.map((step, index) => (
        <div
          key={step}
          className={`rounded-lg border px-4 py-4 ${
            active
              ? "border-emerald-200 bg-emerald-50 text-emerald-950"
              : index === 2
                ? "border-slate-300 bg-white text-slate-900"
                : "border-slate-200 bg-white text-slate-800"
          }`}
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Step {index + 1}</p>
          <p className="mt-2 text-sm font-bold">{step}</p>
          {index < pipelineSteps.length - 1 ? <p className="mt-2 text-xs text-slate-500">feeds next stage</p> : null}
        </div>
      ))}
    </div>
  );
}

function LiveTrackingPanel({ liveTracking, onRefresh }) {
  return (
    <article className="rounded-xl bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Live Storefront Tracking</h2>
          <p className="mt-1 text-sm text-slate-500">Click the storefront once, then refresh this panel to prove real events arrive.</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Current Session ID", liveTracking?.session_id],
          ["Event Count", liveTracking?.event_count],
          ["Latest Event Type", liveTracking?.latest_event_type],
          ["Latest Page", liveTracking?.latest_page]
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
            <dd className="mt-1 text-sm font-bold text-slate-900">{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

export default function DefenseDemo() {
  const [status, setStatus] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [placement, setPlacement] = useState(null);
  const [rawPayload, setRawPayload] = useState(null);
  const [error, setError] = useState("");
  const [loadingKey, setLoadingKey] = useState("");

  const modelLoaded = status ? Boolean(status.model_exists) : isRealMlPlacement(placement);
  const modelStatusLabel = status ? (modelLoaded ? "Real ML model loaded" : "Fallback mode") : "Checking model...";
  const shouldShowFallbackWarning = (status && !status.model_exists) || (placement && !isRealMlPlacement(placement));
  const modelMetadata = status?.model_metadata || selectedScenario?.model_metadata || {};
  const activeScenarioKey = selectedScenario?.key || "casual";
  const hasDecision = Boolean(placement);

  const selectedFeatureRows = useMemo(() => {
    const features = placement?.features_used || selectedScenario?.features_used || {};
    return featureRows.map(([key, label]) => [label, formatValue(features[key])]);
  }, [placement, selectedScenario]);

  const loadStatus = async () => {
    try {
      const response = await api.get("/recommendations/defense-demo/status", { headers: getAuthHeaders() });
      setStatus(response.data);
      setError("");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to load defense demo status.");
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const runScenario = async (scenarioKey) => {
    setLoadingKey(scenarioKey);
    setError("");
    setPlacement(null);
    setRawPayload(null);

    try {
      const headers = getAuthHeaders();
      const scenarioResponse = await api.post(`/recommendations/defense-demo/scenarios/${scenarioKey}`, {}, { headers });
      const scenario = scenarioResponse.data;
      const placementResponse = await api.get("/ads/placement", {
        params: {
          page: "home",
          session_id: scenario.session_id
        }
      });

      setSelectedScenario(scenario);
      setPlacement(placementResponse.data);
      setRawPayload({
        scenario,
        placement: placementResponse.data
      });
      await loadStatus();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" && detail.trim() ? detail : "Failed to run scenario.");
    } finally {
      setLoadingKey("");
    }
  };

  return (
    <section className="space-y-6">
      <div className="rounded-xl bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-950">ML Decision Demo</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Deterministic visitor scenarios pass through the same KMeans session segmentation and storefront ad placement endpoint used by NeonRetro.
              Explicit purchase signals can calibrate a medium behavioral cluster into high commercial intent when cart and attribute-selection actions are strong.
              Ad performance feedback updates ranking metrics, not the KMeans model.
            </p>
          </div>
          <div className={`rounded-lg px-4 py-3 text-sm font-bold ${modelLoaded ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
            {modelStatusLabel}
          </div>
        </div>

        {shouldShowFallbackWarning ? (
          <p className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            {MODEL_WARNING}
          </p>
        ) : null}

        {error ? (
          <p className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>
        ) : null}

        <div className="mt-6">
          <Pipeline active={Boolean(placement)} />
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["ML Algorithm: KMeans Clustering", modelMetadata.algorithm ? `${modelMetadata.algorithm} Clustering` : "KMeans Clustering"],
            ["Input: 15 visitor behavior features", `${modelMetadata.feature_count || 15} features`],
            ["Preprocessing: StandardScaler", modelMetadata.scaler || modelMetadata.scaler_type || "StandardScaler"],
            ["Output: low / medium / high engagement segment", "low / medium / high"],
            ["Business action: segment-aware ad ranking strategy", "Segment-aware ad ranking strategy"],
            ["Model status: Real ML model loaded", modelStatusLabel],
            ["Training sessions", formatMetadataValue(modelMetadata.training_session_count)],
            [
              "Silhouette score",
              formatMetadataValue(modelMetadata.silhouette_score, modelMetadata.silhouette_score_note || "not available for this model artifact")
            ]
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-2 text-sm font-bold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {scenarioButtons.map((scenario) => (
          <button
            key={scenario.key}
            type="button"
            onClick={() => runScenario(scenario.key)}
            disabled={Boolean(loadingKey)}
            className={`rounded-xl border bg-white p-5 text-left shadow-card transition hover:-translate-y-0.5 hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-60 ${
              selectedScenario?.key === scenario.key ? "border-slate-900 ring-2 ring-slate-900/10" : "border-transparent"
            }`}
          >
            <span className="text-sm font-bold text-slate-950">
              {loadingKey === scenario.key ? "Running..." : scenario.label}
            </span>
            <span className="mt-2 block text-sm leading-6 text-slate-500">{scenario.description}</span>
          </button>
        ))}
      </div>

      {!hasDecision ? (
        <article className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center shadow-card">
          <h2 className="text-lg font-semibold text-slate-900">Run a scenario to generate an ML decision.</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The feature table, raw KMeans segment, calibrated final segment, ad strategy, and selected ad preview will appear here.
          </p>
        </article>
      ) : (
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <article className="rounded-xl bg-white p-5 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Decision Explanation</h2>
              <p className="mt-1 text-sm text-slate-500">Algorithm: KMeans Clustering</p>
            </div>
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-bold text-slate-800">
              Segment: {titleCase(placement?.segment_label || selectedScenario?.expected_segment_label)}
            </div>
          </div>

          <dl className="mt-5 grid gap-3 sm:grid-cols-2">
            {[
              ["Predicted Segment", titleCase(placement?.segment_label)],
              ["KMeans Cluster Segment", titleCase(placement?.kmeans_segment_label)],
              ["Calibration Applied", placement?.calibration_applied === undefined ? null : placement.calibration_applied ? "Yes" : "No"],
              ["Calibration Reason", placement?.calibration_reason],
              ["Ranking Strategy", placement?.ranking_strategy || selectedScenario?.expected_strategy],
              ["Decision Reason", placement?.decision_reason],
              ["Candidate Count", placement?.candidate_count]
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
                <dd className="mt-2 text-sm font-bold text-slate-900">{formatValue(value)}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-bold text-slate-900">Why this segment?</h3>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-700 sm:grid-cols-3">
              {(scenarioExplanations[activeScenarioKey] || scenarioExplanations.casual).map((reason) => (
                <li key={reason} className="rounded-md bg-white px-3 py-2 font-medium">
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Input features table</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {selectedFeatureRows.map(([label, value]) => (
                  <tr key={label}>
                    <td className="px-4 py-2 font-medium text-slate-900">{label}</td>
                    <td className="px-4 py-2 text-slate-700">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="rounded-xl bg-white p-5 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selected Ad Preview</p>
          <h2 className="mt-3 text-xl font-bold text-slate-950">{formatValue(placement?.title)}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{formatValue(placement?.content)}</p>
          {placement?.image_url ? (
            <img src={placement.image_url} alt={placement.title || "Selected ad"} className="mt-5 h-56 w-full rounded-lg object-cover" />
          ) : (
            <div className="mt-5 flex h-56 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
              No ad image returned
            </div>
          )}

          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
            {!placement
              ? "Run a visitor scenario to send seeded behavior through the KMeans placement path."
              : isRealMlPlacement(placement)
              ? `The model classified this session as ${titleCase(placement.segment_label)} and selected an eligible home ad using ${placement.ranking_strategy}.`
              : "This response is not using the real KMeans placement path yet. Run the bootstrap script and re-run the scenario before the main defense demo."}
          </div>

          <details className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
            <summary className="cursor-pointer text-sm font-semibold text-slate-900">Technical Details</summary>
            <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
              {JSON.stringify(rawPayload || { status }, null, 2)}
            </pre>
          </details>
        </article>
      </div>
      )}

      <article className="rounded-xl bg-white p-5 shadow-card">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Cluster to Segment Explanation</h2>
          <p className="mt-1 text-sm text-slate-500">
            KMeans assigns a cluster from the 15 scaled behavior features, then the backend maps that cluster to a stable business segment.
          </p>
        </div>
        <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["Segment", "Behavior Pattern", "Ad Strategy", "Marketing Meaning"].map((heading) => (
                  <th key={heading} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {segmentExplanationRows.map(([segment, behaviorPattern, adStrategy, marketingMeaning]) => (
                <tr key={segment}>
                  <td className="px-4 py-3 font-bold text-slate-900">{segment}</td>
                  <td className="px-4 py-3 text-slate-700">{behaviorPattern}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800">{adStrategy}</td>
                  <td className="px-4 py-3 text-slate-700">{marketingMeaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <LiveTrackingPanel liveTracking={status?.live_tracking} onRefresh={loadStatus} />
    </section>
  );
}
