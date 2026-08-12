import { Routes, Route, Navigate } from "react-router-dom";
import AdvisorPage from "./pages/AdvisorPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/"           element={<AdvisorPage />} />
      <Route path="/reports"    element={<Navigate to="/" replace />} />
      <Route path="/admin"      element={<AdminPage />} />
      <Route path="*"           element={<Navigate to="/" replace />} />
    </Routes>
  );
}
