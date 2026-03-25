import { Link, Route, Routes } from "react-router-dom";

import { DashboardPage } from "./pages/DashboardPage";
import { OpportunityDetailPage } from "./pages/OpportunityDetailPage";

export default function App() {
  return (
    <div className="min-h-screen bg-fog text-ink">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(194,65,12,0.10),_transparent_30%)]" />
      <div className="absolute inset-0 -z-10 bg-dashboard-grid bg-[size:36px_36px] opacity-60" />
      <header className="border-b border-black/5 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
          <Link to="/" className="space-y-1">
            <div className="text-xs uppercase tracking-[0.3em] text-slate">Polymarket</div>
            <div className="text-2xl font-semibold">Relative-Value Scanner</div>
          </Link>
          <div className="rounded-full border border-black/10 bg-white px-3 py-1 text-sm text-slate shadow-sm">
            MVP dashboard
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}

