import { Activity, ClipboardList, Cpu, GitBranch, LogOut, ShieldCheck } from 'lucide-react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useHealth } from '@/hooks/useHealth';
import { clearApiKey } from '@/api';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/releases', label: 'Releases', icon: GitBranch },
  { to: '/devices', label: 'Devices', icon: Cpu },
  { to: '/audit', label: 'Audit Log', icon: ClipboardList },
  { to: '/overrides', label: 'Overrides', icon: ShieldCheck },
];

export function AppShell() {
  const { data: health, isError } = useHealth();
  const navigate = useNavigate();
  const location = useLocation();

  const healthy = !isError && health?.status === 'ok';

  return (
    <div className="flex min-h-screen bg-[var(--bg-page)]">
      <aside className="sticky top-0 flex h-screen w-16 flex-col border-r bg-[var(--bg-card)] xl:w-[240px]">
        <div className="flex h-14 items-center border-b px-4">
          <span className="hidden text-sm font-semibold tracking-wide xl:inline">OTA Dashboard</span>
          <span className="text-sm font-semibold xl:hidden">OTA</span>
        </div>
        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.to);

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn(
                  'flex h-10 items-center gap-3 rounded-[var(--radius-button)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-row-hover)] hover:text-[var(--text-primary)]',
                  active && 'bg-[color:var(--accent)]/15 text-[var(--text-primary)]',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="hidden xl:inline">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t p-2">
          <Button
            variant="ghost"
            className="h-10 w-full justify-start gap-3"
            onClick={() => {
              clearApiKey();
              navigate('/');
            }}
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden xl:inline">Logout</span>
          </Button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-[var(--bg-page)]/95 px-4 backdrop-blur">
          <h1 className="text-sm font-semibold tracking-wide">OTA Dashboard</h1>
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span className={cn('h-2 w-2 rounded-full', healthy ? 'bg-[var(--success)]' : 'bg-[var(--error)]')} />
            <Activity className="h-3.5 w-3.5" />
            <span>{healthy ? 'Health: OK' : 'Health: Down'}</span>
          </div>
        </header>
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
