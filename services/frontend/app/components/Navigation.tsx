/**
 * Navigation component with Auth0 authentication
 */
import { useAuth0 } from "@auth0/auth0-react";
import { Link, useLocation } from "react-router";
import { useMemo, useState, useRef, useEffect } from "react";
import { AuthModal } from "./AuthModal";

export function Navigation() {
  const { isAuthenticated, isLoading, user, logout } = useAuth0();
  const [adminOpen, setAdminOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const adminRef = useRef<HTMLDivElement | null>(null);

  // Close admin dropdown when clicking outside (pointer) or pressing Escape.
  // Use pointerdown for better support across input types and to avoid race
  // conditions with focus/blur during navigation.
  const location = useLocation();

  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (!adminRef.current) return;
      if (!(e.target instanceof Node)) return;
      if (!adminRef.current.contains(e.target as Node)) {
        setAdminOpen(false);
      }
    }

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setAdminOpen(false);
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  // Close the admin menu on navigation (so it collapses when a Link causes a route change).
  useEffect(() => {
    setAdminOpen(false);
  }, [location.pathname]);

  // Determine roles from token claims (Auth0 places custom claims under URL keys sometimes)
  const roles: string[] = useMemo(() => {
    if (!user) return [];
    // roles may be present under different keys; check the common Microsoft schema and 'role'
    const claimKey = Object.keys(user).find((k) => k.toLowerCase().includes("role"));
    if (claimKey && Array.isArray((user as any)[claimKey])) {
      return (user as any)[claimKey] as string[];
    }
    // fallback: check 'role' property
    if ((user as any).role && Array.isArray((user as any).role)) {
      return (user as any).role as string[];
    }
    return [];
  }, [user]);

  const isAdmin = roles.includes("Admin");

  return (
    <nav className="bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center gap-8">
          <Link to="/" className="text-xl font-bold">
            Gaming Platform
          </Link>
          <div className="hidden md:flex gap-4 items-center">
            <Link to="/play" className="hover:text-blue-400 transition">
              Play
            </Link>
            <Link to="/leaderboard" className="hover:text-blue-400 transition">
              Leaderboard
            </Link>
            {isAuthenticated && (
              <Link to={`/dashboard/${user?.sub}`} className="hover:text-blue-400 transition">
                Dashboard
              </Link>
            )}

            {/* Admin menu */}
            {isAdmin && (
              <div className="relative" ref={adminRef}>
                <button
                  onClick={() => setAdminOpen((s) => !s)}
                  className="hover:text-blue-400 transition px-2 py-1 rounded"
                  aria-expanded={adminOpen}
                >
                  Admin ▾
                </button>
                {adminOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-gray-800 border border-gray-700 rounded shadow-lg z-50">
                    <Link to="/architecture" className="block px-4 py-2 hover:bg-gray-700">Architecture</Link>
                    <Link to="/health" className="block px-4 py-2 hover:bg-gray-700">Health</Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {isLoading ? (
            <div className="text-gray-400">Loading...</div>
          ) : isAuthenticated ? (
            <>
              <div className="flex items-center gap-2">
                {user?.picture && (
                  <img
                    src={user.picture}
                    alt={user.name}
                    className="w-8 h-8 rounded-full"
                  />
                )}
                <span className="text-sm">{user?.name || user?.email}</span>
              </div>
              <Link
                to="/account"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
              >
                Account
              </Link>
              <button
                onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition"
              >
                Logout
              </button>
            </>
          ) : (
            <button
              onClick={() => setAuthModalOpen(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Auth Modal */}
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </nav>
  );
}
