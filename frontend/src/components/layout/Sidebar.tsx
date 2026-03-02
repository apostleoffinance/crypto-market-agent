import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, Database, TrendingUp, Grid3X3, ShieldAlert, PieChart } from 'lucide-react';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/explorer', label: 'Historical Explorer', icon: Search },
  { to: '/correlation', label: 'Correlation Matrix', icon: Grid3X3 },
  { to: '/risk', label: 'Risk Metrics', icon: ShieldAlert },
  { to: '/sectors', label: 'Sector Rotation', icon: PieChart },
];

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-brand-950 text-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-brand-800">
        <span className="text-2xl">🪙</span>
        <div>
          <h1 className="text-lg font-bold leading-tight">Crypto Market</h1>
          <p className="text-xs text-brand-300">Investment Dashboard</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-800 text-white'
                  : 'text-brand-200 hover:bg-brand-900 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-brand-800">
        <div className="flex items-center gap-2 text-brand-400 text-xs">
          <Database size={14} />
          <span>Powered by CoinGecko</span>
        </div>
      </div>
    </aside>
  );
}
