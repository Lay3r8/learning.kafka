import { useLoaderData } from "react-router";
import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import type { Route } from "./+types/health";
import { commandAPI, queryAPI } from "../lib/api";

export function meta({ }: Route.MetaArgs) {
  return [
    { title: "System Health - Gaming Event System" },
    { name: "description", content: "Monitor microservices health and status" },
  ];
}

interface ServiceHealth {
  name: string;
  status: "healthy" | "degraded" | "down";
  responseTime?: number;
  error?: string;
}

async function checkService(
  name: string,
  checkFn: () => Promise<any>
): Promise<ServiceHealth> {
  const startTime = performance.now();
  try {
    await checkFn();
    const responseTime = performance.now() - startTime;
    return {
      name,
      status: responseTime < 1000 ? "healthy" : "degraded",
      responseTime,
    };
  } catch (error) {
    return {
      name,
      status: "down",
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

export async function loader() {
  // Return an initial empty state. Actual service checks are performed client-side
  // after RBAC is evaluated to avoid server-side loader throwing for unauthorized users.
  return {
    services: [],
    timestamp: Date.now(),
  };
}

export default function Health() {
  const loaderData = useLoaderData<typeof loader>();
  const { services: initialServices, timestamp: initialTimestamp } = loaderData;
  const { isAuthenticated, isLoading, user, getAccessTokenSilently } = useAuth0();

  let isAdmin = false;
  try {
    const claimKey = Object.keys(user || {}).find((k) => k.toLowerCase().includes("role"));
    const roles = claimKey && (user as any)[claimKey] ? (user as any)[claimKey] : (user as any).role;
    isAdmin = !isLoading && isAuthenticated && Array.isArray(roles) && roles.includes("Admin");
  } catch (e) {
    // If role extraction fails during SSR, default to non-admin to avoid throwing
    console.error("Role extraction failed", e);
    isAdmin = false;
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="mb-8">
            <a href="/" className="text-blue-400 hover:text-blue-300">← Back to Home</a>
          </div>
          <div className="p-6 bg-red-900 border-2 border-red-700 rounded-lg">
            <h2 className="text-2xl font-bold mb-2">Unauthorized access</h2>
            <p className="text-gray-300">You do not have permission to view this page.</p>
          </div>
        </div>
      </div>
    );
  }
  // client-side health state
  const [services, setServices] = useState<ServiceHealth[]>((initialServices as ServiceHealth[]) || []);
  const [timestamp, setTimestamp] = useState<number>(initialTimestamp || Date.now());
  const [loadingHealth, setLoadingHealth] = useState(false);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    try {
      // Try to get an access token from Auth0 SDK when available
      let accessToken: string | null = null;
      try {
        if (isAuthenticated && getAccessTokenSilently) {
          accessToken = await getAccessTokenSilently();
        }
      } catch (e) {
        accessToken = null;
      }

      const [commandHealth, queryHealth] = await Promise.all([
        checkService("Command Service", () => commandAPI.getHealth(accessToken || undefined)),
        checkService("Query Service", () => queryAPI.getHealth(accessToken || undefined)),
      ]);
      setServices([commandHealth, queryHealth]);
      setTimestamp(Date.now());
    } catch (e) {
      console.error("Health fetch failed", e);
    } finally {
      setLoadingHealth(false);
    }
  };

  // If admin, perform service checks client-side and auto-refresh
  useEffect(() => {
    let interval: number | undefined;
    const load = async () => {
      try {
        let accessToken: string | null = null;
        try {
          if (isAuthenticated && getAccessTokenSilently) {
            accessToken = await getAccessTokenSilently();
          }
        } catch (e) {
          accessToken = null;
        }

        const [commandHealth, queryHealth] = await Promise.all([
          checkService("Command Service", () => commandAPI.getHealth(accessToken || undefined)),
          checkService("Query Service", () => queryAPI.getHealth(accessToken || undefined)),
        ]);
        setServices([commandHealth, queryHealth]);
        setTimestamp(Date.now());
      } catch (e) {
        // On error, mark services as down explicitly
        console.error("Health check failed", e);
        setServices([
          { name: "Command Service", status: "down", error: (e as Error).message },
          { name: "Query Service", status: "down", error: (e as Error).message },
        ]);
        setTimestamp(Date.now());
      }
    };

    if (isAdmin) {
      load();
      interval = window.setInterval(load, 5000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAdmin]);

  const allHealthy = services.length > 0 && services.every((s) => s.status === "healthy");
  const anyDown = services.some((s) => s.status === "down");

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
            <h1 className="text-4xl font-bold">System Health</h1>
            <p className="text-gray-400 mt-2">Microservices Status Monitor</p>
          </div>
          <button
            onClick={() => fetchHealth()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            disabled={loadingHealth}
          >
            {loadingHealth ? "Checking..." : "🔄 Refresh"}
          </button>
        </div>

        {/* Overall Status */}
        <div className={`p-6 rounded-lg border-2 mb-8 ${allHealthy
            ? "bg-green-900 border-green-600"
            : anyDown
              ? "bg-red-900 border-red-600"
              : "bg-yellow-900 border-yellow-600"
          }`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">
                {allHealthy ? "✅ All Systems Operational" :
                  anyDown ? "❌ System Degraded" :
                    "⚠️ Performance Issues Detected"}
              </h2>
              <p className="text-sm opacity-90">
                Last checked: {new Date(timestamp).toLocaleString()}
              </p>
            </div>
            <div className="text-5xl">
              {allHealthy ? "🟢" : anyDown ? "🔴" : "🟡"}
            </div>
          </div>
        </div>

        {/* Service Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {services.map((service) => (
            <div
              key={service.name}
              className={`p-6 rounded-lg border-2 ${service.status === "healthy"
                  ? "bg-gray-800 border-green-600"
                  : service.status === "degraded"
                    ? "bg-gray-800 border-yellow-600"
                    : "bg-gray-800 border-red-600"
                }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold">{service.name}</h3>
                  <div className="flex items-center gap-2 mt-2">
                    <span
                      className={`inline-block w-3 h-3 rounded-full ${service.status === "healthy"
                          ? "bg-green-500"
                          : service.status === "degraded"
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                    ></span>
                    <span className="text-sm font-medium uppercase">
                      {service.status}
                    </span>
                  </div>
                </div>
                <div className="text-3xl">
                  {service.status === "healthy" && "✅"}
                  {service.status === "degraded" && "⚠️"}
                  {service.status === "down" && "❌"}
                </div>
              </div>

              {service.responseTime !== undefined && (
                <div className="mt-4">
                  <div className="text-sm text-gray-400 mb-1">Response Time</div>
                  <div className={`text-2xl font-bold ${service.responseTime < 500 ? "text-green-400" :
                      service.responseTime < 1000 ? "text-yellow-400" :
                        "text-red-400"
                    }`}>
                    {service.responseTime.toFixed(0)}ms
                  </div>
                </div>
              )}

              {service.error && (
                <div className="mt-4 p-3 bg-red-950 border border-red-700 rounded">
                  <div className="text-xs text-red-200">
                    <strong>Error:</strong> {service.error}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* System Architecture */}
        <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
          <h2 className="text-2xl font-bold mb-6">Architecture Overview</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg">
              <div className="text-3xl">📝</div>
              <div className="flex-1">
                <div className="font-bold">Command Service</div>
                <div className="text-sm text-gray-400">
                  Handles bet placement (write operations)
                </div>
              </div>
              <div className="text-sm text-gray-400">Port 5000</div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg">
              <div className="text-3xl">📊</div>
              <div className="flex-1">
                <div className="font-bold">Query Service</div>
                <div className="text-sm text-gray-400">
                  Provides player stats and leaderboards (read operations)
                </div>
              </div>
              <div className="text-sm text-gray-400">Port 5001</div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg">
              <div className="text-3xl">⚡</div>
              <div className="flex-1">
                <div className="font-bold">Event Processor</div>
                <div className="text-sm text-gray-400">
                  Consumes Kafka events and updates query database
                </div>
              </div>
              <div className="text-sm text-gray-400">Background</div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg">
              <div className="text-3xl">📬</div>
              <div className="flex-1">
                <div className="font-bold">Apache Kafka</div>
                <div className="text-sm text-gray-400">
                  Event streaming platform (KRaft mode)
                </div>
              </div>
              <div className="text-sm text-gray-400">Port 9092</div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg">
              <div className="text-3xl">💾</div>
              <div className="flex-1">
                <div className="font-bold">Redis</div>
                <div className="text-sm text-gray-400">
                  Query-side data store and leaderboard
                </div>
              </div>
              <div className="text-sm text-gray-400">Port 6379</div>
            </div>
          </div>
        </div>

        {/* Auto-refresh indicator */}
        <div className="mt-6 text-center text-xs text-gray-500">
          Auto-refreshing every 5 seconds
        </div>
      </div>
    </div>
  );
}
