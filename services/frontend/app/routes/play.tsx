import { useState, type FormEvent } from "react";
import type { Route } from "./+types/play";
import { useAuth0 } from "@auth0/auth0-react";
import { commandAPI, type PlaceBetRequest, type BetResponse } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Place a Bet - Gaming Event System" },
    { name: "description", content: "Place bets on your favorite games" },
  ];
}

const GAME_TYPES = [
  { value: "slots", label: "Slots", icon: "🎰", enabled: true },
  { value: "blackjack", label: "Blackjack", icon: "🃏", enabled: true },
  { value: "roulette", label: "Roulette", icon: "🎡", enabled: true },
  { value: "poker", label: "Poker", icon: "♠️", enabled: false },
];

export default function Play() {
  const { isAuthenticated, user, loginWithRedirect, getAccessTokenSilently } = useAuth0();
  const [gameType, setGameType] = useState("slots");
  const [amount, setAmount] = useState("10");
  const [isPlacing, setIsPlacing] = useState(false);
  const [result, setResult] = useState<BetResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    if (!isAuthenticated) {
      loginWithRedirect();
      return;
    }

    setIsPlacing(true);
    setError(null);
    setResult(null);

    try {
      // Get Auth0 access token
      const token = await getAccessTokenSilently();

      // NOTE: Using 'sub' claim as player_id for demo purposes.
      // Access tokens don't include 'nickname' - that's only in ID tokens.
      // In production, you'd have a proper user registration system
      // that maps Auth0 user IDs to internal player IDs.
      const request: PlaceBetRequest = {
        player_id: user?.sub || "",
        game_type: gameType,
        amount: parseFloat(amount),
        session_id: `session_${Date.now()}`,
      };

      const response = await commandAPI.placeBet(request, token);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to place bet");
    } finally {
      setIsPlacing(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-4xl font-bold mb-4">Login Required</h1>
          <p className="text-xl text-gray-300 mb-8">
            Please login to place bets and play games.
          </p>
          <button
            onClick={() => loginWithRedirect()}
            className="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold text-lg transition-colors"
          >
            Login with Auth0
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <a href="/" className="text-blue-400 hover:text-blue-300">
            ← Back to Home
          </a>
        </div>

        <h1 className="text-4xl font-bold mb-4">Place a Bet</h1>
        <p className="text-gray-400 mb-8">
          Playing as: <span className="text-white font-semibold">{user?.name || user?.email}</span>
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Game Type</label>
            <div className="grid grid-cols-2 gap-3">
              {GAME_TYPES.map((game) => (
                <div key={game.value} className="relative group w-full">
                  <button
                    type="button"
                    onClick={() => game.enabled && setGameType(game.value)}
                    className={`w-full p-4 rounded-lg border-2 transition-all focus:outline-none ${
                      gameType === game.value
                        ? "border-blue-500 bg-blue-900/50 cursor-pointer"
                        : game.enabled
                        ? "border-gray-600 bg-gray-800 hover:border-gray-500 cursor-pointer"
                        : "border-dashed border-gray-500 bg-gray-800 cursor-not-allowed"
                    }`}
                    aria-disabled={!game.enabled}
                    title={!game.enabled ? "Coming soon" : undefined}
                  >
                    <div className="text-3xl mb-2">{game.icon}</div>
                    <div className="font-medium">{game.label}</div>
                  </button>

                  {/* Inline tooltip for disabled games */}
                  {!game.enabled && (
                    <div className="absolute left-1/2 -translate-x-1/2 mt-2 w-max px-2 py-1 text-xs rounded bg-black bg-opacity-80 text-white opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      Coming soon
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Bet Amount */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Bet Amount ($)
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              min="10"
              max="1000"
              step="0.01"
              className="w-full px-4 py-3 bg-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-white"
              required
            />
            <div className="mt-3 flex gap-2 flex-wrap">
              {[10, 25, 50, 100, 250, 500].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setAmount(preset.toString())}
                  className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-500 cursor-pointer text-sm font-medium transition-colors"
                >
                  ${preset}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Min: $10, Max: $1000
            </p>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isPlacing}
            className="w-full py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 cursor-pointer disabled:cursor-not-allowed rounded-lg font-semibold text-lg transition-colors"
          >
            {isPlacing ? "Placing Bet..." : "Place Bet"}
          </button>
        </form>

        {/* Error Display */}
        {error && (
          <div className="mt-6 p-4 bg-red-900 border-2 border-red-600 rounded-lg">
            <h3 className="font-bold mb-2">Error</h3>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className="mt-6 p-6 bg-green-900 border-2 border-green-600 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">✅ Bet Placed Successfully!</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-300">Bet ID:</span>
                <span className="font-mono font-bold">{result.bet_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Correlation ID:</span>
                <span className="font-mono">{result.correlation_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Status:</span>
                <span className="uppercase font-bold">{result.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Timestamp:</span>
                <span>{new Date(result.timestamp).toLocaleString()}</span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-green-800 rounded text-xs">
              <p className="text-green-200">
                💡 Events are being processed. Check your{" "}
                <a href={`/dashboard/${user?.sub}`} className="underline font-bold">
                  dashboard
                </a>{" "}
                in a few seconds to see the results!
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
