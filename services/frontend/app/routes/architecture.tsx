import type { Route } from "./+types/architecture";
import { useAuth0 } from "@auth0/auth0-react";

function hasAdminRole(user: any) {
  if (!user) return false;
  const claimKey = Object.keys(user).find((k) => k.toLowerCase().includes("role"));
  if (claimKey && Array.isArray((user as any)[claimKey])) return (user as any)[claimKey].includes("Admin");
  if ((user as any).role && Array.isArray((user as any).role)) return (user as any).role.includes("Admin");
  return false;
}

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Architecture - Gaming Event System" },
    { name: "description", content: "CQRS event-driven architecture overview" },
  ];
}

export default function Architecture() {
  const { isAuthenticated, isLoading, user } = useAuth0();
  const isAdmin = !isLoading && isAuthenticated && hasAdminRole(user);

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
        <div className="max-w-7xl mx-auto">
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
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <a href="/" className="text-blue-400 hover:text-blue-300">
            ← Back to Home
          </a>
        </div>

        <h1 className="text-4xl font-bold mb-4">System Architecture</h1>
        <p className="text-gray-400 mb-8">
          Event-Driven CQRS Pattern with Apache Kafka
        </p>

        {/* Architecture Diagram */}
        <div className="bg-gray-800 p-8 rounded-lg border-2 border-gray-700 mb-8">
          <h2 className="text-2xl font-bold mb-6 text-center">Data Flow</h2>

          <div className="space-y-8">
            {/* Command Side */}
            <div className="flex items-center gap-4">
              <div className="flex-1 text-right">
                <div className="text-sm text-gray-400">Client Request</div>
                <div className="text-lg font-bold">POST /api/v1/bets</div>
              </div>
              <div className="text-3xl">→</div>
              <div className="flex-1 bg-blue-900 border-2 border-blue-600 p-6 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">📝</div>
                  <div>
                    <div className="font-bold text-xl">Command Service</div>
                    <div className="text-sm text-blue-200">Write Side (Port 5000)</div>
                  </div>
                </div>
                <div className="mt-3 text-xs text-blue-100 space-y-1">
                  <div>• Validates bet request</div>
                  <div>• Simulates game outcome</div>
                  <div>• Publishes events to Kafka</div>
                </div>
              </div>
            </div>

            {/* Kafka Event Bus */}
            <div className="flex items-center justify-center">
              <div className="text-3xl">↓</div>
            </div>

            <div className="bg-purple-900 border-2 border-purple-600 p-6 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="text-3xl">📬</div>
                <div>
                  <div className="font-bold text-xl">Apache Kafka (KRaft)</div>
                  <div className="text-sm text-purple-200">Event Streaming Platform</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-purple-800 p-3 rounded text-center">
                  <div className="text-xs text-purple-200 mb-1">Topic</div>
                  <div className="font-mono font-bold text-sm">bet.placed</div>
                </div>
                <div className="bg-purple-800 p-3 rounded text-center">
                  <div className="text-xs text-purple-200 mb-1">Topic</div>
                  <div className="font-mono font-bold text-sm">bet.won</div>
                </div>
                <div className="bg-purple-800 p-3 rounded text-center">
                  <div className="text-xs text-purple-200 mb-1">Topic</div>
                  <div className="font-mono font-bold text-sm">bet.lost</div>
                </div>
              </div>
            </div>

            {/* Event Processor */}
            <div className="flex items-center justify-center">
              <div className="text-3xl">↓</div>
            </div>

            <div className="bg-yellow-900 border-2 border-yellow-600 p-6 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="text-3xl">⚡</div>
                <div>
                  <div className="font-bold text-xl">Event Processor</div>
                  <div className="text-sm text-yellow-200">Event Sourcing Engine</div>
                </div>
              </div>
              <div className="mt-3 text-xs text-yellow-100 space-y-1">
                <div>• Consumes events from Kafka</div>
                <div>• Applies state changes to Redis</div>
                <div>• Updates player stats & leaderboard</div>
                <div>• Guarantees eventual consistency</div>
              </div>
            </div>

            {/* Redis Storage */}
            <div className="flex items-center justify-center">
              <div className="text-3xl">↓</div>
            </div>

            <div className="bg-red-900 border-2 border-red-600 p-6 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="text-3xl">💾</div>
                <div>
                  <div className="font-bold text-xl">Redis</div>
                  <div className="text-sm text-red-200">Query-Side Data Store</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-red-800 p-3 rounded">
                  <div className="text-xs text-red-200 mb-1">Hash</div>
                  <div className="font-mono text-sm">player:*:stats</div>
                </div>
                <div className="bg-red-800 p-3 rounded">
                  <div className="text-xs text-red-200 mb-1">Sorted Set</div>
                  <div className="font-mono text-sm">leaderboard:balance</div>
                </div>
              </div>
            </div>

            {/* Query Service */}
            <div className="flex items-center justify-center">
              <div className="text-3xl">↓</div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1 bg-green-900 border-2 border-green-600 p-6 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">📊</div>
                  <div>
                    <div className="font-bold text-xl">Query Service</div>
                    <div className="text-sm text-green-200">Read Side (Port 5001)</div>
                  </div>
                </div>
                <div className="mt-3 text-xs text-green-100 space-y-1">
                  <div>• GET /api/v1/players/:id/stats</div>
                  <div>• GET /api/v1/leaderboard</div>
                  <div>• Fast read-optimized queries</div>
                </div>
              </div>
              <div className="text-3xl">→</div>
              <div className="flex-1 text-left">
                <div className="text-sm text-gray-400">Client Response</div>
                <div className="text-lg font-bold">JSON Data</div>
              </div>
            </div>
          </div>
        </div>

        {/* Key Concepts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* CQRS */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span className="text-2xl">🔄</span>
              CQRS Pattern
            </h3>
            <p className="text-sm text-gray-300 mb-3">
              Command Query Responsibility Segregation separates write (commands) and read (queries) operations.
            </p>
            <div className="space-y-2 text-xs">
              <div className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Commands modify state (Command Service)</span>
              </div>
              <div className="flex gap-2">
                <span className="text-green-400">•</span>
                <span>Queries retrieve data (Query Service)</span>
              </div>
              <div className="flex gap-2">
                <span className="text-purple-400">•</span>
                <span>Independent scaling and optimization</span>
              </div>
            </div>
          </div>

          {/* Event Sourcing */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span className="text-2xl">📜</span>
              Event Sourcing
            </h3>
            <p className="text-sm text-gray-300 mb-3">
              State changes are stored as immutable events in Kafka, providing complete audit trail.
            </p>
            <div className="space-y-2 text-xs">
              <div className="flex gap-2">
                <span className="text-purple-400">•</span>
                <span>All state changes captured as events</span>
              </div>
              <div className="flex gap-2">
                <span className="text-yellow-400">•</span>
                <span>Event replay for debugging</span>
              </div>
              <div className="flex gap-2">
                <span className="text-red-400">•</span>
                <span>Temporal queries (state at any time)</span>
              </div>
            </div>
          </div>

          {/* Eventual Consistency */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span className="text-2xl">⏱️</span>
              Eventual Consistency
            </h3>
            <p className="text-sm text-gray-300 mb-3">
              Query side eventually reflects command side changes after event processing.
            </p>
            <div className="space-y-2 text-xs">
              <div className="flex gap-2">
                <span className="text-green-400">•</span>
                <span>Async event processing (typically &lt;1s)</span>
              </div>
              <div className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Higher availability and performance</span>
              </div>
              <div className="flex gap-2">
                <span className="text-purple-400">•</span>
                <span>Trade-off: not immediately consistent</span>
              </div>
            </div>
          </div>

          {/* Scalability */}
          <div className="bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span className="text-2xl">📈</span>
              Horizontal Scaling
            </h3>
            <p className="text-sm text-gray-300 mb-3">
              Each service can scale independently based on workload demands.
            </p>
            <div className="space-y-2 text-xs">
              <div className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Multiple Command Service instances</span>
              </div>
              <div className="flex gap-2">
                <span className="text-green-400">•</span>
                <span>Multiple Query Service instances</span>
              </div>
              <div className="flex gap-2">
                <span className="text-yellow-400">•</span>
                <span>Kafka consumer groups for parallelism</span>
              </div>
            </div>
          </div>
        </div>

        {/* Technology Stack */}
        <div className="mt-8 bg-gray-800 p-6 rounded-lg border-2 border-gray-700">
          <h2 className="text-2xl font-bold mb-6">Technology Stack</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h4 className="font-bold text-blue-400 mb-3">Backend Services</h4>
              <ul className="text-sm space-y-2 text-gray-300">
                <li>• Python 3.11</li>
                <li>• FastAPI 0.104.1</li>
                <li>• Pydantic for validation</li>
                <li>• Structured logging</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-purple-400 mb-3">Infrastructure</h4>
              <ul className="text-sm space-y-2 text-gray-300">
                <li>• Apache Kafka 4.0.1 (KRaft)</li>
                <li>• Redis 8.2.2</li>
                <li>• Docker Compose</li>
                <li>• Kubernetes ready</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-green-400 mb-3">Frontend</h4>
              <ul className="text-sm space-y-2 text-gray-300">
                <li>• React 19.2</li>
                <li>• React Router 7</li>
                <li>• TypeScript</li>
                <li>• TailwindCSS</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
