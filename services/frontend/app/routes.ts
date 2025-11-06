import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  layout("routes/_layout.tsx", [
    index("routes/home.tsx"),
    route("play", "routes/play.tsx"),
    route("dashboard/:playerId", "routes/dashboard.$playerId.tsx"),
    route("my-bets", "routes/my-bets.tsx"),
    route("leaderboard", "routes/leaderboard.tsx"),
    route("account", "routes/account.tsx"),
    route("health", "routes/health.tsx"),
    route("architecture", "routes/architecture.tsx"),
  ]),
] satisfies RouteConfig;
