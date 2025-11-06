/**
 * Main layout with navigation
 */
import { Outlet } from "react-router";
import { Navigation } from "../components/Navigation";

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800">
      <Navigation />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
