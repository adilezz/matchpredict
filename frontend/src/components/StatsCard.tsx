interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

export default function StatsCard({ title, value, subtitle }: StatsCardProps) {
  return (
    <div className="card p-3.5">
      <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">
        {title}
      </div>
      <div className="text-xl font-bold text-white font-mono">{value}</div>
      {subtitle && <div className="text-[10px] text-gray-600 mt-0.5">{subtitle}</div>}
    </div>
  );
}
