import { useLoaderData, useRevalidator, useParams } from "react-router";
import { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import type { Route } from "./+types/dashboard.$playerId";
import { queryAPI } from "../lib/api";

export function meta({ params }: Route.MetaArgs) {
  return [
    { title: `${params.playerId} - Player Dashboard` },
    { name: "description", content: "View player statistics and performance" },
  ];
}

// No server loader - all data fetching happens client-side with Auth0
export default function Dashboard() {
  const params = useParams();
  const playerId = params.playerId!;
  const { getAccessTokenSilently, isAuthenticated, isLoading } = useAuth0();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch player stats with auth token
  const fetchStats = async () => {
    if (!isAuthenticated) {
      setError("Please log in to view your dashboard");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const token = await getAccessTokenSilently();
      const data = await queryAPI.getPlayerStats(playerId, token);
      setStats(data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load player stats:", err);
      setError(err.message || "Failed to load player data");
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  // Initial load only (stop automatic refresh)
  useEffect(() => {
    if (!isLoading) {
      fetchStats();
    }
  }, [isAuthenticated, isLoading, playerId]);

  // Show loading state
  if (isLoading || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-16">
            <div className="text-6xl mb-4">⏳</div>
            <h1 className="text-3xl font-bold">Loading Dashboard...</h1>
          </div>
        </div>
      </div>
    );
  }

  // Show auth error
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🔒</div>
            <h1 className="text-3xl font-bold mb-4">Authentication Required</h1>
            <p className="text-gray-400 mb-8">Please log in to view your dashboard</p>
          </div>
        </div>
      </div>
    );
  }

  // If no stats (new player or error), show "no data" message
  if (!stats) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="mb-8">
            <a href="/" className="text-blue-400 hover:text-blue-300">
              ← Back to Home
            </a>
          </div>
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🎮</div>
            <h1 className="text-3xl font-bold mb-4">No Player Data Found</h1>
            <p className="text-gray-400 mb-8">
              {error || "This player hasn't placed any bets yet. Start playing to see your stats!"}
            </p>
            <a
              href="/play"
              className="inline-block px-8 py-4 bg-green-600 hover:bg-green-700 rounded-lg font-semibold text-lg transition-colors"
            >
              Place Your First Bet
            </a>
          </div>
        </div>
      </div>
    );
  }

  const totalBets = stats.win_count + stats.loss_count;
  const winRate = totalBets > 0
    ? (stats.win_count / totalBets * 100).toFixed(1)
    : "0.0";

  const netProfit = stats.total_won - stats.total_lost;
  const isProfitable = netProfit > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <a href="/" className="text-blue-400 hover:text-blue-300">
            ← Back to Home
          </a>
        </div>

        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold">{playerId}</h1>
            <p className="text-gray-400 mt-2">Player Dashboard</p>
          </div>
          <div className="flex items-start gap-3">
            <button
              onClick={fetchStats}
              className="px-4 py-2 w-40 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? "Refreshing..." : "🔄 Refresh"}
            </button>

            <a
              href="/my-bets"
              className="inline-block px-4 py-2 w-40 text-center bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              My Bets
            </a>

            <a
              href="/play"
              className="inline-block px-4 py-2 w-40 text-center bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
            >
              Place New Bet
            </a>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Bets */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Total Bets</div>
            <div className="text-3xl font-bold">{totalBets}</div>
          </div>

          {/* Win Rate */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Win Rate</div>
            <div className="text-3xl font-bold text-green-400">{winRate}%</div>
            <div className="text-xs text-gray-500 mt-1">
              {stats.win_count}W / {stats.loss_count}L
            </div>
          </div>

          {/* Total Wagered */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Total Wagered</div>
            <div className="text-3xl font-bold">${stats.total_wagered.toFixed(2)}</div>
          </div>

          {/* Net Profit/Loss */}
          <div className={`p-6 rounded-lg border-2 ${
            isProfitable
              ? "bg-green-900 border-green-600"
              : "bg-red-900 border-red-600"
          }`}>
            <div className="text-gray-300 text-sm mb-2">Net Profit/Loss</div>
            <div className={`text-3xl font-bold ${
              isProfitable ? "text-green-300" : "text-red-300"
            }`}>
              {isProfitable ? "+" : ""}${netProfit.toFixed(2)}
            </div>
            <div className="text-xs text-gray-300 mt-1">
              Won: ${stats.total_won.toFixed(2)} / Lost: ${stats.total_lost.toFixed(2)}
            </div>
          </div>
        </div>

        {/* Performance Summary */}
        <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
          <h2 className="text-2xl font-bold mb-6">Performance Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-gray-400 text-sm mb-2">Games Played</div>
              <div className="text-3xl font-bold text-blue-400">{stats.games_played}</div>
            </div>
            <div>
              <div className="text-gray-400 text-sm mb-2">Current Balance</div>
              <div className="text-3xl font-bold text-yellow-400">${stats.balance.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-400 text-sm mb-2">Avg Bet Size</div>
              <div className="text-3xl font-bold text-purple-400">
                ${totalBets > 0 ? (stats.total_wagered / totalBets).toFixed(2) : "0.00"}
              </div>
            </div>
          </div>
        </div>

        {/* Last update indicator */}
        <div className="mt-6 text-center text-xs text-gray-500">
          Last update: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
