import type { Metadata } from "next";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "MatchPredict - AI Football Predictions",
  description:
    "AI-powered football match predictions: 1X2, over/under goals, BTTS, correct score across 10+ European leagues",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="flex flex-col min-h-screen">
          <header className="sticky top-0 z-50 border-b border-surface-4 bg-surface-1/95 backdrop-blur-md">
            <div className="max-w-[1440px] mx-auto px-4">
              <div className="flex items-center justify-between h-12">
                <a href="/" className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center">
                    <span className="text-white font-bold text-[11px]">MP</span>
                  </div>
                  <span className="text-sm font-bold text-white tracking-tight">
                    Match<span className="text-accent">Predict</span>
                  </span>
                </a>

                <nav className="flex items-center gap-1">
                  <NavLink href="/" label="Fixtures" />
                  <NavLink href="/leagues" label="Leagues" />
                  <NavLink href="/performance" label="Performance" />
                </nav>
              </div>
            </div>
          </header>

          <main className="flex-1">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>

          <footer className="border-t border-surface-4 bg-surface-1/80 py-4 mt-8">
            <div className="max-w-[1440px] mx-auto px-4 flex items-center justify-between text-[10px] text-gray-600">
              <span>MatchPredict AI &copy; {new Date().getFullYear()}</span>
              <span>Predictions powered by XGBoost + LightGBM + CatBoost ensemble</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white rounded hover:bg-surface-3 transition-colors"
    >
      {label}
    </a>
  );
}
