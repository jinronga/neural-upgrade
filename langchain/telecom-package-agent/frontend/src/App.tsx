import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ChatPage from "./pages/Chat";
import DashboardPage from "./pages/Dashboard";
import PackagesPage from "./pages/Packages";
import BenefitsPage from "./pages/Benefits";

const App: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/packages" element={<PackagesPage />} />
        <Route path="/benefits" element={<BenefitsPage />} />
      </Routes>
    </Layout>
  );
};

export default App;

