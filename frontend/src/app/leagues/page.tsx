"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { League } from "@/lib/types";
import { getLeagues } from "@/lib/api";
import { getCountryFlag } from "@/lib/helpers";

export default function LeaguesPage() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLeagues()
      .then(setLeagues)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-6 fade-in">
      <h1 className="text-xl font-bold text-white mb-1">Leagues</h1>
      <p className="text-xs text-gray-500 mb-6">
        Select a league to view standings, fixtures and predictions
      </p>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {leagues
            .filter((l) => l.is_active)
            .map((league) => (
              <Link
                key={league.code}
                href={`/league/${league.code}`}
                className="card-hover flex items-center gap-4 px-5 py-4 group"
              >
                <span className="text-2xl">{getCountryFlag(league.country)}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold text-white group-hover:text-accent transition-colors">
                    {league.name}
                  </div>
                  <div className="text-[11px] text-gray-500">{league.country}</div>
                </div>
                <svg
                  className="w-4 h-4 text-gray-600 group-hover:text-accent transition-colors"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            ))}
        </div>
      )}
    </div>
  );
}
