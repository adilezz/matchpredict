"use client";

import { useState } from "react";
import type { League } from "@/lib/types";
import { getCountryFlag } from "@/lib/helpers";

interface LeagueSidebarProps {
  leagues: League[];
  selected: string | null;
  onSelect: (code: string | null) => void;
}

export default function LeagueSidebar({ leagues, selected, onSelect }: LeagueSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = leagues.filter(
    (l) =>
      l.name.toLowerCase().includes(search.toLowerCase()) ||
      l.country.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="sidebar-card overflow-hidden">
      <div className="px-3 py-2.5 border-b border-surface-4">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
          Leagues
        </h3>
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-2.5 py-1.5 bg-surface-3 border border-surface-5 rounded text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>

      <div className="max-h-[calc(100vh-14rem)] overflow-y-auto">
        <button
          onClick={() => onSelect(null)}
          className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs font-medium transition-colors border-l-2 ${
            selected === null
              ? "bg-surface-3 text-white border-accent"
              : "text-gray-400 hover:bg-surface-2 hover:text-gray-200 border-transparent"
          }`}
        >
          <span className="text-sm">🌍</span>
          <span>All Leagues</span>
        </button>

        {filtered.map((league) => (
          <button
            key={league.code}
            onClick={() => onSelect(league.code)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs transition-colors border-l-2 ${
              selected === league.code
                ? "bg-surface-3 text-white border-accent"
                : "text-gray-400 hover:bg-surface-2 hover:text-gray-200 border-transparent"
            }`}
          >
            <span className="text-sm">{getCountryFlag(league.country)}</span>
            <div className="min-w-0">
              <div className="font-medium truncate">{league.name}</div>
              <div className="text-[10px] text-gray-600">{league.country}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
