/**
 * Auth Modal Component - Sign In / Sign Up
 *
 * Provides a modal dialog for users to either:
 * 1. Sign in (redirects to Auth0)
 * 2. Sign up (creates account in our system + Auth0)
 */
import { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { userAPI } from "../lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { loginWithRedirect } = useAuth0();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSignIn = async () => {
    // Redirect to Auth0 login
    await loginWithRedirect();
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Create user in our system (which also creates in Auth0)
      await userAPI.signup({
        email,
        password,
        username: username || undefined,
      });

      setSignupSuccess(true);

      // After 2 seconds, redirect to sign in
      setTimeout(() => {
        loginWithRedirect();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign up");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setUsername("");
    setError("");
    setSignupSuccess(false);
  };

  const switchMode = (newMode: "signin" | "signup") => {
    resetForm();
    setMode(newMode);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-8 max-w-md w-full mx-4 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white text-2xl"
        >
          ×
        </button>

        {/* Header */}
        <h2 className="text-3xl font-bold mb-6 text-white">
          {mode === "signin" ? "Sign In" : "Create Account"}
        </h2>

        {signupSuccess ? (
          <div className="bg-green-900 border border-green-600 rounded p-4 mb-4">
            <p className="text-green-100">
              ✅ Account created successfully! Redirecting to sign in...
            </p>
          </div>
        ) : mode === "signin" ? (
          // Sign In Mode
          <div>
            <p className="text-gray-300 mb-6">
              Sign in to your Gaming Platform account
            </p>
            <button
              onClick={handleSignIn}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition"
            >
              Sign In with Auth0
            </button>
            <p className="text-gray-400 text-sm mt-6 text-center">
              Don't have an account?{" "}
              <button
                onClick={() => switchMode("signup")}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign up
              </button>
            </p>
          </div>
        ) : (
          // Sign Up Mode
          <form onSubmit={handleSignUp}>
            {error && (
              <div className="bg-red-900 border border-red-600 rounded p-3 mb-4">
                <p className="text-red-100 text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">
                  Email *
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">
                  Username (optional)
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="johndoe"
                />
              </div>

              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">
                  Password *
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="Min. 8 characters"
                />
                <p className="text-gray-400 text-xs mt-1">
                  Password must be at least 8 characters
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-bold py-3 rounded-lg transition"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>

            <p className="text-gray-400 text-sm mt-6 text-center">
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => switchMode("signin")}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign in
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
