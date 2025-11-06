import { useLoaderData, useRevalidator } from "react-router";
import { useEffect } from "react";
import type { Route } from "./+types/leaderboard";
import { queryAPI } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Leaderboard - Gaming Event System" },
    { name: "description", content: "Top players ranked by balance" },
  ];
}

export async function loader() {
  try {
    const data = await queryAPI.getLeaderboard(50);
    return data;
  } catch (error) {
    console.error("Failed to load leaderboard:", error);
    // Return empty leaderboard on error
    return { leaderboard: [] };
  }
}

export default function Leaderboard() {
  const leaderboard = useLoaderData<typeof loader>();
  const revalidator = useRevalidator();

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      revalidator.revalidate();
    }, 10000);
    return () => clearInterval(interval);
  }, [revalidator]);

  // Safety check - ensure leaderboard data exists
  if (!leaderboard || !leaderboard.leaderboard) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="mb-8">
            <a href="/" className="text-blue-400 hover:text-blue-300">
              ← Back to Home
            </a>
          </div>
          <div className="text-center py-16">
            <div className="text-6xl mb-4">⚠️</div>
            <h1 className="text-3xl font-bold mb-4">Unable to Load Leaderboard</h1>
            <p className="text-gray-400">Please try again later</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <a href="/" className="text-blue-400 hover:text-blue-300">
            ← Back to Home
          </a>
        </div>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold">🏆 Leaderboard</h1>
            <p className="text-gray-400 mt-2">Top {leaderboard.leaderboard.length} Players by Balance</p>
          </div>
          <button
            onClick={() => revalidator.revalidate()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            disabled={revalidator.state === "loading"}
          >
            {revalidator.state === "loading" ? "Refreshing..." : "🔄 Refresh"}
          </button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Showing Top</div>
            <div className="text-3xl font-bold text-blue-400">{leaderboard.leaderboard.length}</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Last Updated</div>
            <div className="text-lg font-bold">{new Date().toLocaleTimeString()}</div>
          </div>
        </div>

        {/* Leaderboard Table */}
        <div className="bg-gray-800 rounded-lg border-2 border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Rank</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Player ID</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold">Balance</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {leaderboard.leaderboard.map((entry) => {
                  const medalColor =
                    entry.rank === 1 ? "text-yellow-400" :
                    entry.rank === 2 ? "text-gray-300" :
                    entry.rank === 3 ? "text-orange-400" :
                    "text-gray-500";

                  return (
                    <tr key={entry.player_id} className="hover:bg-gray-750 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className={`text-2xl ${medalColor}`}>
                            {entry.rank === 1 && "🥇"}
                            {entry.rank === 2 && "🥈"}
                            {entry.rank === 3 && "🥉"}
                            {entry.rank > 3 && `#${entry.rank}`}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-mono font-medium">{entry.player_id}</div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className={`text-xl font-bold ${
                          entry.balance >= 1000 ? "text-green-400" :
                          entry.balance >= 0 ? "text-blue-400" :
                          "text-red-400"
                        }`}>
                          ${entry.balance.toFixed(2)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <a
                          href={`/dashboard/${entry.player_id}`}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
                        >
                          View Stats
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Empty State */}
        {leaderboard.leaderboard.length === 0 && (
          <div className="bg-gray-800 p-12 rounded-lg border-2 border-gray-700 text-center">
            <div className="text-6xl mb-4">🎰</div>
            <h3 className="text-2xl font-bold mb-2">No Players Yet</h3>
            <p className="text-gray-400 mb-6">Be the first to place a bet!</p>
            <a
              href="/play"
              className="inline-block px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold transition-colors"
            >
              Place Your First Bet
            </a>
          </div>
        )}

        {/* Auto-refresh indicator */}
        <div className="mt-6 text-center text-xs text-gray-500">
          Auto-refreshing every 10 seconds
        </div>
      </div>
    </div>
  );
}
