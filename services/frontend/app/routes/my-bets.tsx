import { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { queryAPI } from "../lib/api";

export function meta() {
    return [
        { title: "My Bets - Gaming Event System" },
        { name: "description", content: "View your bet history and results" },
    ];
}

export default function MyBets() {
    const { isAuthenticated, isLoading, getAccessTokenSilently, user, loginWithRedirect } = useAuth0();
    const [bets, setBets] = useState<any[] | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchBets = async () => {
            if (!isAuthenticated) return;
            try {
                setLoading(true);
                const token = await getAccessTokenSilently();
                const data = await queryAPI.getPlayerBets(user!.sub!, token);
                setBets(data.bets || []);
                setError(null);
            } catch (err: any) {
                console.error("Failed to fetch bets:", err);
                setError(err.message || "Failed to fetch bets");
                setBets([]);
            } finally {
                setLoading(false);
            }
        };

        if (!isLoading) fetchBets();
    }, [isAuthenticated, isLoading, getAccessTokenSilently, user]);

    if (isLoading || loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
                <div className="max-w-6xl mx-auto text-center py-16">
                    <div className="text-6xl mb-4">⏳</div>
                    <h1 className="text-3xl font-bold">Loading Your Bets...</h1>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
                <div className="max-w-6xl mx-auto text-center py-16">
                    <div className="text-6xl mb-4">🔒</div>
                    <h1 className="text-3xl font-bold mb-4">Authentication Required</h1>
                    <p className="text-gray-400 mb-8">Please log in to view your bets</p>
                    <button
                        onClick={() => loginWithRedirect()}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold"
                    >
                        Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
            <div className="max-w-6xl mx-auto">
                <div className="mb-8">
                    <a href="/" className="text-blue-400 hover:text-blue-300">← Back to Home</a>
                </div>

                <h1 className="text-4xl font-bold mb-4">My Bets</h1>
                <p className="text-gray-400 mb-6">Showing your most recent bets (most recent first)</p>

                {error && (
                    <div className="mb-6 p-4 bg-red-900 border-2 border-red-600 rounded-lg">
                        <strong className="block mb-2">Error</strong>
                        <div>{error}</div>
                    </div>
                )}

                <div className="bg-gray-800 rounded-lg border-2 border-gray-700 overflow-x-auto">
                    <table className="w-full table-auto">
                        <thead className="bg-gray-900">
                            <tr>
                                <th className="px-4 py-3 text-left text-sm font-semibold">Time</th>
                                <th className="px-4 py-3 text-left text-sm font-semibold">Game</th>
                                <th className="px-4 py-3 text-right text-sm font-semibold">Amount</th>
                                <th className="px-4 py-3 text-center text-sm font-semibold">Result</th>
                                <th className="px-4 py-3 text-left text-sm font-semibold">Correlation ID</th>
                                <th className="px-4 py-3 text-right text-sm font-semibold">Profit</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {(bets || []).map((b) => (
                                <tr key={b.bet_id} className="hover:bg-gray-750 transition-colors">
                                    <td className="px-4 py-3 text-sm">{new Date(b.timestamp).toLocaleString()}</td>
                                    <td className="px-4 py-3 text-sm">{b.game_type}</td>
                                    <td className="px-4 py-3 text-right text-sm font-mono">${b.amount.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-center text-sm uppercase font-semibold">{b.status}</td>
                                    <td className="px-4 py-3 text-sm font-mono break-words">{b.correlation_id}</td>
                                    <td className="px-4 py-3 text-right text-sm font-mono">{b.profit !== null ? (b.profit >= 0 ? `+$${b.profit.toFixed(2)}` : `-$${Math.abs(b.profit).toFixed(2)}`) : '-'}</td>
                                </tr>
                            ))}

                            {(!bets || bets.length === 0) && (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-gray-400">No bets found</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
