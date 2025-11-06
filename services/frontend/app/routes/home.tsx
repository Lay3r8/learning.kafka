import type { Route } from "./+types/home";
import { Link } from "react-router";
import { useAuth0 } from "@auth0/auth0-react";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Gaming Event System - CQRS Demo" },
    { name: "description", content: "Event-driven betting system with CQRS and Event Sourcing" },
  ];
}

export default function Home() {
  const { isAuthenticated, user, loginWithRedirect } = useAuth0();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4">Gaming Event System</h1>
          <p className="text-xl text-gray-300">CQRS Event Sourcing Demo</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {/* Play Now Card */}
          <Link
            to="/play"
            className="bg-gradient-to-br from-green-600 to-green-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
          >
            <div className="text-4xl mb-4">🎮</div>
            <h2 className="text-2xl font-bold mb-2">Play Now</h2>
            <p className="text-green-100">Place bets and win prizes</p>
          </Link>

          {/* Dashboard Card */}
          {isAuthenticated ? (
            <Link
              to={`/dashboard/${user?.sub}`}
              className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
            >
              <div className="text-4xl mb-4">📊</div>
              <h2 className="text-2xl font-bold mb-2">Dashboard</h2>
              <p className="text-blue-100">View your stats and balance</p>
            </Link>
          ) : (
            <button
              onClick={() => loginWithRedirect()}
              className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl text-left"
            >
              <div className="text-4xl mb-4">📊</div>
              <h2 className="text-2xl font-bold mb-2">Dashboard</h2>
              <p className="text-blue-100">Login to view your stats</p>
            </button>
          )}

          {/* Leaderboard Card */}
          <Link
            to="/leaderboard"
            className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
          >
            <div className="text-4xl mb-4">🏆</div>
            <h2 className="text-2xl font-bold mb-2">Leaderboard</h2>
            <p className="text-purple-100">Top players rankings</p>
          </Link>

          {/* System Health Card */}
          <Link
            to="/health"
            className="bg-gradient-to-br from-red-600 to-red-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
          >
            <div className="text-4xl mb-4">❤️</div>
            <h2 className="text-2xl font-bold mb-2">System Health</h2>
            <p className="text-red-100">Service monitoring</p>
          </Link>

          {/* Architecture Card */}
          <Link
            to="/architecture"
            className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
          >
            <div className="text-4xl mb-4">🏗️</div>
            <h2 className="text-2xl font-bold mb-2">Architecture</h2>
            <p className="text-indigo-100">System design overview</p>
          </Link>

          {/* Documentation Card */}
          <a
            href="http://localhost:5000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gradient-to-br from-gray-600 to-gray-700 rounded-lg p-8 hover:scale-105 transition-transform shadow-xl"
          >
            <div className="text-4xl mb-4">📚</div>
            <h2 className="text-2xl font-bold mb-2">API Docs</h2>
            <p className="text-gray-100">OpenAPI documentation</p>
          </a>
        </div>

        {/* Future Features Placeholder */}
        <div className="mt-12 p-6 bg-gray-800 rounded-lg border-2 border-dashed border-gray-600 max-w-4xl mx-auto">
          <h3 className="text-xl font-bold mb-2">Coming Soon (Phase 2)</h3>
          <ul className="text-gray-300 space-y-2">
            <li> Wallet Service with transaction rollback simulation</li>
            <li>📈 Advanced analytics and betting patterns</li>
            <li>🔔 Real-time notifications via WebSocket</li>
            <li>🎲 More game types and betting strategies</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
