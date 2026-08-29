import { motion } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    GitPullRequest,
    FileText,
    Activity,
    Bot,
    Zap,
    Users,
} from 'lucide-react'
import {
    LayoutDashboard,
    GitPullRequest,
    Users,
    FileText,
    Activity,
    Bot,
    Zap,
} from 'lucide-react'

const links = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/prs', label: 'PRs', icon: GitPullRequest },
    { to: '/contributors', label: 'Contributors', icon: Users },
    { to: '/digests', label: 'Digests', icon: FileText },
    { to: '/health', label: 'Health', icon: Activity },
]

export default function Navbar() {
    const { pathname } = useLocation()

    return (
        <motion.nav
            initial={{ y: -80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, type: 'spring' }}
            className="
        fixed top-0 left-0 right-0 z-50
        glass-strong border-b border-white/5
      "
        >
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center gap-8">

                {/* Brand */}
                <Link to="/" className="flex items-center gap-3 group">
                    <motion.div
                        animate={{ rotate: [0, 10, -10, 0] }}
                        transition={{ duration: 4, repeat: Infinity }}
                        className="
              w-9 h-9 rounded-xl
              bg-gradient-to-br from-blue-500 to-purple-600
              flex items-center justify-center
              shadow-[0_0_20px_rgba(88,166,255,0.4)]
              group-hover:shadow-[0_0_30px_rgba(88,166,255,0.6)]
              transition-all duration-300
            "
                    >
                        <Bot className="w-5 h-5 text-white" />
                    </motion.div>
                    <div>
                        <div className="
              font-bold text-base gradient-text
              leading-none
            ">
                            PR Triage Bot
                        </div>
                        <div className="text-xs text-gray-500 leading-none mt-0.5">
                            AI Maintainer Co-pilot
                        </div>
                    </div>
                </Link>

                {/* Links */}
                <div className="flex items-center gap-1 flex-1">
                    {links.map(({ to, label, icon: Icon }) => {
                        const active = pathname === to
                        return (
                            <Link
                                key={to}
                                to={to}
                                className={`
                  relative flex items-center gap-2
                  px-4 py-2 rounded-xl
                  text-sm font-medium
                  transition-all duration-200
                  ${active
                                        ? 'text-blue-400'
                                        : 'text-gray-400 hover:text-gray-200'
                                    }
                `}
                            >
                                {active && (
                                    <motion.div
                                        layoutId="navbar-active"
                                        className="
                      absolute inset-0 rounded-xl
                      bg-blue-500/10
                      border border-blue-500/20
                    "
                                        transition={{
                                            type: 'spring',
                                            stiffness: 300,
                                            damping: 30,
                                        }}
                                    />
                                )}
                                <Icon className="w-4 h-4 relative z-10" />
                                <span className="relative z-10">{label}</span>
                            </Link>
                        )
                    })}
                </div>

                {/* Live indicator */}
                <div className="flex items-center gap-2 text-xs text-gray-500">
                    <motion.div
                        animate={{ scale: [1, 1.3, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="w-2 h-2 rounded-full bg-green-400"
                    />
                    <span className="text-green-400 font-medium">Live</span>
                </div>

                {/* Powered by badge */}
                <div className="
          flex items-center gap-1.5 px-3 py-1.5
          rounded-full text-xs font-medium
          bg-purple-500/10 border border-purple-500/20
          text-purple-400
        ">
                    <Zap className="w-3 h-3" />
                    Llama 3.2
                </div>
            </div>
        </motion.nav>
    )
}