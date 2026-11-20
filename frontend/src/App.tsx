import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthContext";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RouteErrorPage } from "@/pages/RouteErrorPage";
import { FaceAnalysisPage } from "@/pages/analysis/FaceAnalysisPage";
import { MotionAnalysisPage } from "@/pages/analysis/MotionAnalysisPage";
import { MultimodalPage } from "@/pages/analysis/MultimodalPage";
import { NewAnalysisPage } from "@/pages/analysis/NewAnalysisPage";
import { VoiceAnalysisPage } from "@/pages/analysis/VoiceAnalysisPage";
import { AuditPage } from "@/pages/records/AuditPage";
import { HistoryPage } from "@/pages/records/HistoryPage";
import { ReportsPage } from "@/pages/records/ReportsPage";
import { SessionDetailPage } from "@/pages/records/SessionDetailPage";
import { DiagnosticsPage } from "@/pages/system/DiagnosticsPage";
import { SettingsPage } from "@/pages/system/SettingsPage";

const router = createBrowserRouter([
  {
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        // Everything below requires a valid, server-checked admin session.
        element: <ProtectedRoute />,
        children: [
          {
            element: <AppShell />,
            errorElement: <RouteErrorPage />,
            children: [
              { index: true, element: <DashboardPage /> },
              { path: "analysis", element: <Navigate to="/analysis/new" replace /> },
              { path: "analysis/new", element: <NewAnalysisPage /> },
              { path: "analysis/face", element: <FaceAnalysisPage /> },
              { path: "analysis/motion", element: <MotionAnalysisPage /> },
              { path: "analysis/voice", element: <VoiceAnalysisPage /> },
              { path: "analysis/combined", element: <MultimodalPage /> },
              { path: "history", element: <HistoryPage /> },
              { path: "history/:id", element: <SessionDetailPage /> },
              { path: "reports", element: <ReportsPage /> },
              { path: "audit", element: <AuditPage /> },
              { path: "diagnostics", element: <DiagnosticsPage /> },
              { path: "settings", element: <SettingsPage /> },
              { path: "*", element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]);

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
