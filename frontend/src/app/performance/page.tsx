"use client";

import { useState, useEffect } from "react";

interface PerformanceData {
  evaluations: {
    id: number;
    model_version: string;
    accuracy: number | null;
    log_loss: number | null;
    brier_score: number | null;
    sample_size: number;
    evaluated_at: string | null;
  }[];
  total_evaluated: number;
  correct_predictions: number;
  accuracy: number;
}

export default function PerformancePage() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/predictions/performance")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="skeleton h-8 w-64 mb-4 rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24 rounded-lg" />
          ))}
        </div>
        <div className="skeleton h-64 rounded-lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">Failed to load performance data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-6 fade-in">
      <h1 className="text-xl font-bold text-white mb-1">Model Performance</h1>
      <p className="text-xs text-gray-500 mb-6">
        Track record and accuracy metrics for our AI prediction models
      </p>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Overall Accuracy"
          value={`${(data.accuracy * 100).toFixed(1)}%`}
          subtitle={`${data.correct_predictions} / ${data.total_evaluated} correct`}
          accent
        />
        <MetricCard
          label="Total Evaluated"
          value={String(data.total_evaluated)}
          subtitle="Finished matches with predictions"
        />
        <MetricCard
          label="Correct Predictions"
          value={String(data.correct_predictions)}
          subtitle="1X2 outcome correct"
        />
        <MetricCard
          label="Model Evaluations"
          value={String(data.evaluations.length)}
          subtitle="Historical checkpoints"
        />
      </div>

      {/* Accuracy gauge */}
      <div className="card p-6 mb-6">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">
          Accuracy Breakdown
        </h2>
        <div className="flex items-center gap-6">
          <div className="relative w-32 h-32">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#1E2230"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#00A83C"
                strokeWidth="3"
                strokeDasharray={`${data.accuracy * 100}, 100`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold font-mono text-white">
                {(data.accuracy * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="flex-1 space-y-3">
            <AccuracyBar label="Random baseline" value={33.3} color="bg-red-500/60" />
            <AccuracyBar label="Bookmaker implied" value={52} color="bg-yellow-500/60" />
            <AccuracyBar
              label="Our model"
              value={data.accuracy * 100}
              color="bg-accent"
            />
          </div>
        </div>
      </div>

      {/* Evaluation history */}
      {data.evaluations.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-4">
            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500">
              Evaluation History
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-4 text-gray-500 uppercase text-[10px] tracking-wider">
                  <th className="py-2.5 px-3 text-left">Date</th>
                  <th className="py-2.5 px-3 text-left">Model</th>
                  <th className="py-2.5 px-3 text-center">Accuracy</th>
                  <th className="py-2.5 px-3 text-center">Log Loss</th>
                  <th className="py-2.5 px-3 text-center">Brier</th>
                  <th className="py-2.5 px-3 text-center">Sample</th>
                </tr>
              </thead>
              <tbody>
                {data.evaluations.map((ev) => (
                  <tr
                    key={ev.id}
                    className="border-b border-surface-3 hover:bg-surface-2 transition-colors"
                  >
                    <td className="py-2 px-3 text-gray-400">
                      {ev.evaluated_at
                        ? new Date(ev.evaluated_at).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })
                        : "-"}
                    </td>
                    <td className="py-2 px-3 text-gray-300 font-mono">{ev.model_version}</td>
                    <td className="py-2 px-3 text-center font-mono text-white">
                      {ev.accuracy != null ? `${(ev.accuracy * 100).toFixed(1)}%` : "-"}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-gray-400">
                      {ev.log_loss?.toFixed(4) ?? "-"}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-gray-400">
                      {ev.brier_score?.toFixed(4) ?? "-"}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-gray-400">
                      {ev.sample_size}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Methodology */}
      <div className="card p-6 mt-6">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
          Methodology
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-400">
          <div className="bg-surface-3 rounded-lg p-4">
            <div className="text-accent font-bold mb-1">1X2 Ensemble</div>
            <p>
              XGBoost (35%) + LightGBM (30%) + CatBoost (35%) with isotonic calibration.
              40+ features including Elo, xG, form, odds, and squad quality.
            </p>
          </div>
          <div className="bg-surface-3 rounded-lg p-4">
            <div className="text-accent font-bold mb-1">Goals Model</div>
            <p>
              Dixon-Coles bivariate Poisson for score probabilities, plus Random Forest
              for total goals. Generates O/U, BTTS, and correct score predictions.
            </p>
          </div>
          <div className="bg-surface-3 rounded-lg p-4">
            <div className="text-accent font-bold mb-1">Continuous Learning</div>
            <p>
              Models retrain weekly with fresh data. Elo ratings update after every matchday.
              Predictions refresh twice daily with latest odds.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  subtitle,
  accent,
}: {
  label: string;
  value: string;
  subtitle: string;
  accent?: boolean;
}) {
  return (
    <div className={`card p-4 ${accent ? "border-accent/30" : ""}`}>
      <div className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">
        {label}
      </div>
      <div
        className={`text-xl font-bold font-mono mt-1 ${
          accent ? "text-accent" : "text-white"
        }`}
      >
        {value}
      </div>
      <div className="text-[10px] text-gray-600 mt-0.5">{subtitle}</div>
    </div>
  );
}

function AccuracyBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-[10px] text-gray-500 mb-0.5">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-surface-4 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
