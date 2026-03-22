export default function MatchListSkeleton() {
  return (
    <div className="card overflow-hidden">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex items-center px-3 py-3 border-b border-surface-3">
          <div className="w-12 flex-shrink-0">
            <div className="skeleton h-3 w-8 mx-auto" />
          </div>
          <div className="flex-1 px-2 space-y-2">
            <div className="skeleton h-3 w-32" />
            <div className="skeleton h-3 w-28" />
          </div>
          <div className="hidden sm:flex gap-1">
            <div className="skeleton h-8 w-12 rounded" />
            <div className="skeleton h-8 w-12 rounded" />
            <div className="skeleton h-8 w-12 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
