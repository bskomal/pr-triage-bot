import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'

import Navbar from './components/Navbar'
import ParticleBackground from './components/ParticleBackground'
import Dashboard from './pages/Dashboard'
import PRList from './pages/PRList'
import PRDetail from './pages/PRDetail'
import DigestList from './pages/DigestList'
import RepoHealth from './pages/RepoHealth'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 2,
    },
  },
})

const PageWrapper = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="relative min-h-screen grid-bg">

          {/* 3D Particle Background */}
          <ParticleBackground />

          {/* Ambient glow orbs */}
          <div className="
            fixed top-1/4 left-1/4 w-96 h-96
            bg-blue-500/5 rounded-full blur-3xl
            pointer-events-none animate-float-slow
          " />
          <div className="
            fixed bottom-1/4 right-1/4 w-96 h-96
            bg-purple-500/5 rounded-full blur-3xl
            pointer-events-none animate-float
          " />
          <div className="
            fixed top-3/4 left-3/4 w-64 h-64
            bg-green-500/3 rounded-full blur-3xl
            pointer-events-none animate-float-fast
          " />

          {/* Navbar */}
          <Navbar />

          {/* Pages */}
          <AnimatePresence mode="wait">
            <Routes>
              <Route
                path="/"
                element={
                  <PageWrapper>
                    <Dashboard />
                  </PageWrapper>
                }
              />
              <Route
                path="/prs"
                element={
                  <PageWrapper>
                    <PRList />
                  </PageWrapper>
                }
              />
              <Route
                path="/pr/:owner/:repo/:number"
                element={
                  <PageWrapper>
                    <PRDetail />
                  </PageWrapper>
                }
              />
              <Route
                path="/digests"
                element={
                  <PageWrapper>
                    <DigestList />
                  </PageWrapper>
                }
              />
              <Route
                path="/health"
                element={
                  <PageWrapper>
                    <RepoHealth />
                  </PageWrapper>
                }
              />
            </Routes>
          </AnimatePresence>

        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}