// Export context and provider from AuthContext.jsx
export { AuthContext, AuthProvider } from './AuthContext'
// Export routing utilities
export { URLs, pathForPendingFlow, pathForFlow, AuthChangeRedirector, AuthenticatedRoute, AnonymousRoute } from './routing'
// Export hooks for direct auth access - useAuth is the main hook to use from components
export { useAuth } from './AuthContext'
// Export useAuthentication as an alias for useAuth for backward compatibility
export { useAuth as useAuthentication } from './AuthContext'
// Export other utility hooks
export { useConfig, useUser, useAuthStatus } from './hooks'