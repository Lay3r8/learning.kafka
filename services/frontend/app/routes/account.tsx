import type { Route } from "./+types/account";
import { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useNavigate } from "react-router";
import { userAPI } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Account Settings - Gaming Platform" },
    { name: "description", content: "Manage your account settings" },
  ];
}

export default function Account() {
  const { user, logout, getAccessTokenSilently } = useAuth0();
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDeleteAccount = async () => {
    if (!user?.sub) return;

    setIsDeleting(true);
    setError(null);

    try {
      const token = await getAccessTokenSilently();
      await userAPI.deleteUser(user.sub, token);

      // Logout and redirect to home
      logout({
        logoutParams: {
          returnTo: window.location.origin,
        },
      });
    } catch (err: any) {
      console.error("Failed to delete account:", err);
      setError(err.message || "Failed to delete account. Please try again.");
      setIsDeleting(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Authentication Required</h2>
          <p className="text-gray-300">Please log in to access account settings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">Account Settings</h1>

        {/* User Information */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
          <h2 className="text-2xl font-semibold mb-4">Profile Information</h2>
          <div className="space-y-3">
            <div>
              <label className="text-gray-400 text-sm">Email</label>
              <p className="text-white text-lg">{user.email}</p>
            </div>
            <div>
              <label className="text-gray-400 text-sm">Username</label>
              <p className="text-white text-lg">{user.nickname || user.name}</p>
            </div>
            <div>
              <label className="text-gray-400 text-sm">User ID</label>
              <p className="text-white text-sm font-mono break-all">{user.sub}</p>
            </div>
            {user.email_verified !== undefined && (
              <div>
                <label className="text-gray-400 text-sm">Email Status</label>
                <p className="text-white">
                  {user.email_verified ? (
                    <span className="text-green-400">✓ Verified</span>
                  ) : (
                    <span className="text-yellow-400">⚠ Not Verified</span>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-900/20 rounded-lg p-6 border-2 border-red-500">
          <h2 className="text-2xl font-semibold mb-4 text-red-400">Danger Zone</h2>
          <p className="text-gray-300 mb-4">
            Once you delete your account, there is no going back. This will:
          </p>
          <ul className="list-disc list-inside text-gray-300 mb-6 space-y-2">
            <li>Permanently delete your account from Auth0</li>
            <li>Deactivate your account in our system</li>
            <li>Remove your wallet and transaction history</li>
            <li>Delete all your betting data</li>
            <li>Remove you from all leaderboards</li>
          </ul>

          {error && (
            <div className="mb-4 p-4 bg-red-500/20 border border-red-500 rounded text-red-200">
              {error}
            </div>
          )}

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded transition-colors"
            >
              Delete My Account
            </button>
          ) : (
            <div className="space-y-4">
              <div className="bg-red-800/30 border border-red-600 rounded p-4">
                <p className="text-red-200 font-semibold mb-2">
                  ⚠️ Are you absolutely sure?
                </p>
                <p className="text-red-300 text-sm">
                  This action cannot be undone. This will permanently delete your account and
                  remove all associated data.
                </p>
              </div>
              <div className="flex gap-4">
                <button
                  onClick={handleDeleteAccount}
                  disabled={isDeleting}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded transition-colors"
                >
                  {isDeleting ? "Deleting..." : "Yes, Delete My Account"}
                </button>
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setError(null);
                  }}
                  disabled={isDeleting}
                  className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Back Button */}
        <div className="mt-8">
          <button
            onClick={() => navigate(-1)}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>
    </div>
  );
}
