import type { Prediction } from "@/lib/types";
import ProbabilityBar from "./ProbabilityBar";

interface PredictionPanelProps {
  prediction: Prediction;
  homeTeam: string;
  awayTeam: string;
}

export default function PredictionPanel({
  prediction: p,
  homeTeam,
  awayTeam,
}: PredictionPanelProps) {
  const correctScores: { score: string; prob: number }[] = (() => {
    if (!p.correct_score_top5) return [];
    try {
      return JSON.parse(p.correct_score_top5);
    } catch {
      return [];
    }
  })();

  const hasValueBet =
    (p.value_edge_home ?? 0) > 0.02 ||
    (p.value_edge_draw ?? 0) > 0.02 ||
    (p.value_edge_away ?? 0) > 0.02;

  return (
    <div className="sidebar-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-surface-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
            AI Predictions
          </h3>
          {hasValueBet && (
            <span className="px-1.5 py-0.5 bg-yellow-500/15 text-yellow-400 text-[9px] font-bold uppercase rounded">
              Value Bet
            </span>
          )}
        </div>
        {p.confidence != null && (
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className="text-[10px] text-gray-600">Confidence</span>
            <div className="flex-1 h-1.5 bg-surface-4 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${p.confidence * 100}%`,
                  background:
                    p.confidence > 0.7
                      ? "#00A83C"
                      : p.confidence > 0.5
                        ? "#F59E0B"
                        : "#EF4444",
                }}
              />
            </div>
            <span className="text-[10px] font-mono text-accent font-bold">
              {(p.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>

      <div className="p-4 space-y-5">
        {/* 1X2 */}
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
            Match Result (1X2)
          </h4>
          <ProbabilityBar home={p.prob_home} draw={p.prob_draw} away={p.prob_away} />
        </div>

        {/* Double Chance */}
        {(p.prob_dc_1x != null || p.prob_dc_x2 != null || p.prob_dc_12 != null) && (
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
              Double Chance
            </h4>
            <div className="grid grid-cols-3 gap-1.5">
              <DCCell label="1X" subLabel={`${homeTeam} or Draw`} value={p.prob_dc_1x} />
              <DCCell label="X2" subLabel={`Draw or ${awayTeam}`} value={p.prob_dc_x2} />
              <DCCell label="12" subLabel="No Draw" value={p.prob_dc_12} />
            </div>
          </div>
        )}

        {/* BTTS */}
        {p.prob_btts_yes != null && p.prob_btts_no != null && (
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
              Both Teams to Score
            </h4>
            <div className="flex gap-1.5">
              <div
                className={`flex-1 text-center py-2 rounded ${
                  p.prob_btts_yes > p.prob_btts_no
                    ? "bg-accent/10 border border-accent/20"
                    : "bg-surface-3"
                }`}
              >
                <div className="text-[10px] text-gray-500">Yes</div>
                <div
                  className={`text-sm font-mono font-bold ${
                    p.prob_btts_yes > p.prob_btts_no ? "text-accent" : "text-gray-300"
                  }`}
                >
                  {(p.prob_btts_yes * 100).toFixed(0)}%
                </div>
              </div>
              <div
                className={`flex-1 text-center py-2 rounded ${
                  p.prob_btts_no > p.prob_btts_yes
                    ? "bg-accent/10 border border-accent/20"
                    : "bg-surface-3"
                }`}
              >
                <div className="text-[10px] text-gray-500">No</div>
                <div
                  className={`text-sm font-mono font-bold ${
                    p.prob_btts_no > p.prob_btts_yes ? "text-accent" : "text-gray-300"
                  }`}
                >
                  {(p.prob_btts_no * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Expected Goals */}
        {(p.home_lambda != null || p.away_lambda != null) && (
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
              Expected Goals
            </h4>
            <div className="grid grid-cols-3 gap-2">
              <GoalStat label={homeTeam} value={p.home_lambda} />
              <GoalStat label="Total" value={p.expected_total_goals} highlight />
              <GoalStat label={awayTeam} value={p.away_lambda} />
            </div>
          </div>
        )}

        {/* Correct Score */}
        {correctScores.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
              Most Likely Scores
            </h4>
            <div className="space-y-1">
              {correctScores.map((cs, i) => (
                <div
                  key={cs.score}
                  className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface-3 transition-colors"
                >
                  <span className="text-[10px] text-gray-600 w-3">{i + 1}.</span>
                  <span className="text-xs font-mono font-bold text-white flex-1">
                    {cs.score}
                  </span>
                  <div className="w-16 h-1.5 bg-surface-4 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent/60 rounded-full"
                      style={{ width: `${Math.min(cs.prob * 100 * 5, 100)}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-mono text-gray-400 w-10 text-right">
                    {(cs.prob * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Goals O/U */}
        <OUSection
          title="Total Goals Over/Under"
          rows={[
            { line: "0.5", over: p.prob_over_05, under: p.prob_under_05 },
            { line: "1.5", over: p.prob_over_15, under: p.prob_under_15 },
            { line: "2.5", over: p.prob_over_25, under: p.prob_under_25 },
            { line: "3.5", over: p.prob_over_35, under: p.prob_under_35 },
          ]}
        />

        {/* Home Team O/U */}
        <OUSection
          title={`${homeTeam} Goals O/U`}
          rows={[
            { line: "0.5", over: p.home_prob_over_05, under: p.home_prob_under_05 },
            { line: "1.5", over: p.home_prob_over_15, under: p.home_prob_under_15 },
            { line: "2.5", over: p.home_prob_over_25, under: p.home_prob_under_25 },
          ]}
        />

        {/* Away Team O/U */}
        <OUSection
          title={`${awayTeam} Goals O/U`}
          rows={[
            { line: "0.5", over: p.away_prob_over_05, under: p.away_prob_under_05 },
            { line: "1.5", over: p.away_prob_over_15, under: p.away_prob_under_15 },
            { line: "2.5", over: p.away_prob_over_25, under: p.away_prob_under_25 },
          ]}
        />

        {/* Value Bets / Odds */}
        {(p.odds_implied_home != null || p.value_edge_home != null) && (
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
              Odds & Value
            </h4>
            <div className="space-y-1.5">
              <OddsRow
                label={`1 ${homeTeam}`}
                implied={p.odds_implied_home}
                model={p.prob_home}
                edge={p.value_edge_home}
              />
              <OddsRow
                label="X Draw"
                implied={p.odds_implied_draw}
                model={p.prob_draw}
                edge={p.value_edge_draw}
              />
              <OddsRow
                label={`2 ${awayTeam}`}
                implied={p.odds_implied_away}
                model={p.prob_away}
                edge={p.value_edge_away}
              />
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-surface-4 flex justify-between text-[10px] text-gray-600">
          <span>Model: {p.model_version}</span>
          <span>AI Powered</span>
        </div>
      </div>
    </div>
  );
}

function GoalStat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number | null;
  highlight?: boolean;
}) {
  return (
    <div
      className={`text-center py-2 px-1 rounded ${
        highlight ? "bg-accent/10 border border-accent/20" : "bg-surface-3"
      }`}
    >
      <div className="text-[10px] text-gray-500 truncate mb-0.5">{label}</div>
      <div
        className={`text-sm font-mono font-bold ${
          highlight ? "text-accent" : "text-white"
        }`}
      >
        {value != null ? value.toFixed(2) : "-"}
      </div>
    </div>
  );
}

function DCCell({
  label,
  subLabel,
  value,
}: {
  label: string;
  subLabel: string;
  value: number | null;
}) {
  if (value == null) return null;
  const isHigh = value > 0.65;
  return (
    <div
      className={`text-center py-2 rounded ${
        isHigh ? "bg-accent/10 border border-accent/20" : "bg-surface-3"
      }`}
    >
      <div className="text-[10px] font-bold text-gray-500">{label}</div>
      <div
        className={`text-sm font-mono font-bold ${isHigh ? "text-accent" : "text-white"}`}
      >
        {(value * 100).toFixed(0)}%
      </div>
      <div className="text-[9px] text-gray-600 truncate px-1">{subLabel}</div>
    </div>
  );
}

function OddsRow({
  label,
  implied,
  model,
  edge,
}: {
  label: string;
  implied: number | null;
  model: number;
  edge: number | null;
}) {
  const isValue = (edge ?? 0) > 0.02;
  return (
    <div className="flex items-center gap-2 py-1.5 px-2 rounded bg-surface-3">
      <span className="text-[10px] text-gray-400 flex-1 truncate">{label}</span>
      {implied != null && (
        <span className="text-[10px] font-mono text-gray-500">
          {(implied * 100).toFixed(0)}%
        </span>
      )}
      <span className="text-[10px] text-gray-600">→</span>
      <span className="text-[10px] font-mono text-white font-semibold">
        {(model * 100).toFixed(0)}%
      </span>
      {edge != null && (
        <span
          className={`text-[10px] font-mono font-bold px-1 py-0.5 rounded ${
            isValue
              ? "bg-yellow-500/15 text-yellow-400"
              : edge < -0.02
                ? "bg-red-500/10 text-red-400"
                : "text-gray-500"
          }`}
        >
          {edge > 0 ? "+" : ""}
          {(edge * 100).toFixed(1)}%
        </span>
      )}
    </div>
  );
}

function OUSection({
  title,
  rows,
}: {
  title: string;
  rows: { line: string; over: number | null; under: number | null }[];
}) {
  const hasData = rows.some((r) => r.over != null || r.under != null);
  if (!hasData) return null;

  return (
    <div>
      <h4 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
        {title}
      </h4>
      <div className="space-y-1">
        <div className="grid grid-cols-3 gap-1 text-[9px] text-gray-600 font-medium uppercase px-1">
          <span>Line</span>
          <span className="text-center">Over</span>
          <span className="text-right">Under</span>
        </div>
        {rows.map((row) => {
          if (row.over == null && row.under == null) return null;
          const overHigher = (row.over ?? 0) > (row.under ?? 0);
          return (
            <div
              key={row.line}
              className="grid grid-cols-3 gap-1 items-center py-1 px-1 rounded hover:bg-surface-3 transition-colors"
            >
              <span className="text-xs font-medium text-gray-400">{row.line}</span>
              <span
                className={`text-center text-xs font-mono font-semibold ${
                  overHigher ? "text-accent" : "text-gray-400"
                }`}
              >
                {row.over != null ? `${(row.over * 100).toFixed(0)}%` : "-"}
              </span>
              <span
                className={`text-right text-xs font-mono font-semibold ${
                  !overHigher ? "text-accent" : "text-gray-400"
                }`}
              >
                {row.under != null ? `${(row.under * 100).toFixed(0)}%` : "-"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
