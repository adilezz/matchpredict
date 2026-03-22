interface ProbabilityBarProps {
  home: number;
  draw: number;
  away: number;
  size?: "sm" | "md";
}

export default function ProbabilityBar({
  home,
  draw,
  away,
  size = "md",
}: ProbabilityBarProps) {
  const total = home + draw + away;
  const pH = total > 0 ? (home / total) * 100 : 33.3;
  const pD = total > 0 ? (draw / total) * 100 : 33.3;
  const pA = total > 0 ? (away / total) * 100 : 33.3;
  const h = size === "sm" ? "h-1.5" : "h-2.5";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-mono">
        <span className="text-blue-400 font-semibold">{pH.toFixed(0)}%</span>
        <span className="text-gray-500">{pD.toFixed(0)}%</span>
        <span className="text-red-400 font-semibold">{pA.toFixed(0)}%</span>
      </div>
      <div className={`flex ${h} rounded-full overflow-hidden bg-surface-4`}>
        <div
          className="bg-blue-500 transition-all duration-500"
          style={{ width: `${pH}%` }}
        />
        <div
          className="bg-gray-500 transition-all duration-500"
          style={{ width: `${pD}%` }}
        />
        <div
          className="bg-red-500 transition-all duration-500"
          style={{ width: `${pA}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-600 font-medium uppercase tracking-wider">
        <span>Home</span>
        <span>Draw</span>
        <span>Away</span>
      </div>
    </div>
  );
}
