import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    FileText,
    Calendar,
    GitPullRequest,
    AlertTriangle,
    Star,
    ChevronDown,
    ChevronUp,
} from 'lucide-react'
import { useState } from 'react'
import { format, formatDistanceToNow } from 'date-fns'
import { getDigests } from '../api/client'

export default function DigestList() {
    const { data: digests, isLoading } = useQuery({
        queryKey: ['digests'],
        queryFn: () => getDigests(null, 20),
        refetchInterval: 60000,
    })

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-5xl mx-auto space-y-6">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-3xl font-black gradient-text mb-2">
                        Triage Digests
                    </h1>
                    <p className="text-gray-400">
                        Daily summaries of your repository health
                    </p>
                </motion.div>

                {/* Digests */}
                {isLoading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map(i => (
                            <div
                                key={i}
                                className="glass rounded-2xl border border-white/5 h-32 animate-pulse"
                            />
                        ))}
                    </div>
                ) : digests?.length === 0 ? (
                    <EmptyDigests />
                ) : (
                    <div className="space-y-4">
                        {digests?.map((digest, i) => (
                            <DigestCard
                                key={digest.id}
                                digest={digest}
                                index={i}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

function DigestCard({ digest, index }) {
    const [expanded, setExpanded] = useState(false)

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="
        glass rounded-2xl border border-white/5
        hover:border-blue-500/20
        transition-all duration-300
        overflow-hidden
      "
        >
            {/* Header */}
            <div
                className="p-6 cursor-pointer"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        {/* Icon */}
                        <div className="
              w-12 h-12 rounded-xl
              bg-blue-500/10 border border-blue-500/20
              flex items-center justify-center
            ">
                            <FileText className="w-6 h-6 text-blue-400" />
                        </div>

                        {/* Info */}
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className="
                  font-bold text-gray-200 text-lg
                ">
                                    {digest.repo}
                                </span>
                                <span className="
                  text-xs px-2 py-0.5 rounded-full
                  bg-blue-500/10 border border-blue-500/20
                  text-blue-400
                ">
                                    {digest.format}
                                </span>
                            </div>
                            <div className="
                flex items-center gap-1.5
                text-sm text-gray-500
              ">
                                <Calendar className="w-3.5 h-3.5" />
                                {format(
                                    new Date(digest.generated_at),
                                    'MMMM d, yyyy — HH:mm'
                                )}
                                <span className="text-gray-600">•</span>
                                {formatDistanceToNow(
                                    new Date(digest.generated_at),
                                    { addSuffix: true }
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Stats + Toggle */}
                    <div className="flex items-center gap-6">
                        <div className="flex gap-4 text-sm">
                            <div className="text-center">
                                <div className="font-bold text-blue-400">
                                    {digest.total_prs}
                                </div>
                                <div className="text-xs text-gray-500">PRs</div>
                            </div>
                            <div className="text-center">
                                <div className="font-bold text-red-400">
                                    {digest.slop_flagged}
                                </div>
                                <div className="text-xs text-gray-500">Flagged</div>
                            </div>
                            <div className="text-center">
                                <div className="font-bold text-green-400">
                                    {digest.avg_quality}
                                </div>
                                <div className="text-xs text-gray-500">Avg Score</div>
                            </div>
                            <div className="text-center">
                                <div className="font-bold text-yellow-400">
                                    {digest.critical_prs}
                                </div>
                                <div className="text-xs text-gray-500">Critical</div>
                            </div>
                        </div>

                        <motion.div
                            animate={{ rotate: expanded ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <ChevronDown className="w-5 h-5 text-gray-500" />
                        </motion.div>
                    </div>
                </div>
            </div>

            {/* Expanded Content */}
            <motion.div
                initial={false}
                animate={{
                    height: expanded ? 'auto' : 0,
                    opacity: expanded ? 1 : 0,
                }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
            >
                <div className="px-6 pb-6 border-t border-white/5 pt-4">
                    {/* Health bars */}
                    <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                            <div className="text-xs text-gray-500 mb-1">
                                PR Volume
                            </div>
                            <div className="h-2 bg-white/5 rounded-full">
                                <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{
                                        width: `${Math.min(digest.total_prs * 10, 100)}%`
                                    }}
                                />
                            </div>
                        </div>
                        <div>
                            <div className="text-xs text-gray-500 mb-1">
                                Quality Health
                            </div>
                            <div className="h-2 bg-white/5 rounded-full">
                                <div
                                    className={`
                    h-full rounded-full
                    ${digest.avg_quality >= 70
                                            ? 'bg-green-500'
                                            : 'bg-yellow-500'
                                        }
                  `}
                                    style={{ width: `${digest.avg_quality}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Content preview */}
                    {digest.content && (
                        <div className="
              bg-black/20 rounded-xl p-4
              border border-white/5
              text-sm text-gray-400
              font-mono leading-relaxed
            ">
                            {digest.content.slice(0, 300)}
                            {digest.content.length > 300 && '...'}
                        </div>
                    )}
                </div>
            </motion.div>
        </motion.div>
    )
}

function EmptyDigests() {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="
        glass rounded-2xl border border-white/5
        py-24 text-center
      "
        >
            <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="text-5xl mb-4"
            >
                📋
            </motion.div>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">
                No digests yet
            </h3>
            <p className="text-gray-500 mb-4">
                Run a full triage to generate your first digest
            </p>
            <code className="
        block mx-auto max-w-lg
        bg-black/30 border border-white/10
        rounded-xl px-4 py-3
        text-sm text-green-400 font-mono
      ">
                python -m src.cli.main triage
                --repo owner/repo --provider ollama
            </code>
        </motion.div>
    )
}