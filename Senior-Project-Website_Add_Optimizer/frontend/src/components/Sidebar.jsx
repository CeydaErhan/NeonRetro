import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Campaigns", to: "/campaigns" },
  { label: "Analytics", to: "/analytics" },
  { label: "Settings", to: "/settings" }
];

// Renders dark navigation sidebar with active route highlighting.
export default function Sidebar() {
  return (
    <>
      <aside className="hidden w-64 flex-shrink-0 bg-slatepanel px-4 py-6 text-slate-100 md:flex md:flex-col">
        <div className="mb-8 px-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Optimizer</p>
          <h2 className="mt-2 text-xl font-bold">Control Hub</h2>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-slatepanelLight text-white"
                    : "text-slate-300 hover:bg-slatepanelLight/70 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <nav className="fixed bottom-0 left-0 right-0 z-20 border-t border-slate-700 bg-slatepanel px-2 py-2 md:hidden">
        <div className="grid grid-cols-4 gap-1">
          {navItems.map((item) => (
            <NavLink
              key={`mobile-${item.to}`}
              to={item.to}
              className={({ isActive }) =>
                `rounded-lg px-2 py-2 text-center text-xs font-medium transition ${
                  isActive ? "bg-slatepanelLight text-white" : "text-slate-300"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </>
  );
}
