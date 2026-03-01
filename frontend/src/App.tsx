import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/layout/DashboardLayout';
import Dashboard from './pages/Dashboard';
import HistoricalExplorer from './pages/HistoricalExplorer';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/explorer" element={<HistoricalExplorer />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
