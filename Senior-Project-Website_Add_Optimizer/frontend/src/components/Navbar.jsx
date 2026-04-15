import { useAuth } from "../context/AuthContext";

// Displays page header and quick user action area.
export default function Navbar() {
  const { logout } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white/90 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Website & Advertisement Optimizer</p>
          <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">Performance Console</h1>
        </div>

        <button
          type="button"
          onClick={logout}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
