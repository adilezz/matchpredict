import type { Match } from "./types";

const COUNTRY_FLAGS: Record<string, string> = {
  England: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  Spain: "🇪🇸",
  Germany: "🇩🇪",
  Italy: "🇮🇹",
  France: "🇫🇷",
  Netherlands: "🇳🇱",
  Portugal: "🇵🇹",
  Turkey: "🇹🇷",
  Belgium: "🇧🇪",
  Scotland: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  Morocco: "🇲🇦",
  International: "🌍",
  Europe: "🇪🇺",
};

export function getCountryFlag(country: string): string {
  return COUNTRY_FLAGS[country] || "⚽";
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function toPercent(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${(value * 100).toFixed(0)}%`;
}

export function getMatchResult(match: Match, teamId: number): "W" | "D" | "L" | null {
  if (match.status !== "finished" || match.home_goals == null || match.away_goals == null) {
    return null;
  }
  const isHome = match.home_team.id === teamId;
  const hg = match.home_goals;
  const ag = match.away_goals;
  if (hg === ag) return "D";
  if (isHome) return hg > ag ? "W" : "L";
  return ag > hg ? "W" : "L";
}

export function resultColor(r: "W" | "D" | "L" | null): string {
  if (r === "W") return "bg-accent text-white";
  if (r === "D") return "bg-yellow-500/80 text-white";
  if (r === "L") return "bg-red-500/80 text-white";
  return "bg-surface-4 text-gray-500";
}

export function getDaysArray(centerDate: Date, range: number): Date[] {
  const days: Date[] = [];
  for (let i = -range; i <= range; i++) {
    const d = new Date(centerDate);
    d.setDate(d.getDate() + i);
    days.push(d);
  }
  return days;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function groupMatchesByLeague(matches: Match[]): Record<string, Match[]> {
  const groups: Record<string, Match[]> = {};
  for (const m of matches) {
    const key = m.league.code;
    if (!groups[key]) groups[key] = [];
    groups[key].push(m);
  }
  return groups;
}

export function getTopPrediction(match: Match): { label: string; prob: number } | null {
  const p = match.prediction;
  if (!p) return null;
  const candidates = [
    { label: `${match.home_team.short_name || match.home_team.name} Win`, prob: p.prob_home },
    { label: "Draw", prob: p.prob_draw },
    { label: `${match.away_team.short_name || match.away_team.name} Win`, prob: p.prob_away },
  ];
  return candidates.reduce((best, c) => (c.prob > best.prob ? c : best));
}
