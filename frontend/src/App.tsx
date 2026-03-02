import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/layout/DashboardLayout';
import Dashboard from './pages/Dashboard';
import HistoricalExplorer from './pages/HistoricalExplorer';
import CorrelationMatrix from './pages/CorrelationMatrix';
import RiskMetrics from './pages/RiskMetrics';
import SectorRotation from './pages/SectorRotation';
import AskAI from './components/AskAI';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/explorer" element={<HistoricalExplorer />} />
          <Route path="/correlation" element={<CorrelationMatrix />} />
          <Route path="/risk" element={<RiskMetrics />} />
          <Route path="/sectors" element={<SectorRotation />} />
        </Route>
      </Routes>
      <AskAI />
    </BrowserRouter>
  );
}
