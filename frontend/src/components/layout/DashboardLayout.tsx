import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function DashboardLayout() {
  return (
    <div className="h-full">
      <Sidebar />
      <div className="lg:pl-64 h-full">
        <main className="min-h-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
