import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ChatPage from "./pages/Chat";
import DashboardPage from "./pages/Dashboard";
import PackagesPage from "./pages/Packages";
import BenefitsPage from "./pages/Benefits";
import UsersPage from "./pages/Users";
import { UserProvider } from "./contexts/UserContext";

const App: React.FC = () => {
  return (
    <UserProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/packages" element={<PackagesPage />} />
          <Route path="/benefits" element={<BenefitsPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Routes>
      </Layout>
    </UserProvider>
  );
};

export default App;
