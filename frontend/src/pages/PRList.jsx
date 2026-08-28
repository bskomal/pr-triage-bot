import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
    GitPullRequest,
    Filter,
    Search,
    AlertTriangle,
    CheckCircle,
    Star,
    ChevronDown,
    ExternalLink,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

import QualityBadge from '../components/QualityBadge'
import { getPRAnalyses } from '../api/client'

const TIERS = ['all', 'excellent', 'good', 'needs-work', 'poor']
const TYPES = ['all', 'bug', 'feature', 'docs', 'refactor', 'test', 'chore', 'security']
const PRIORITIES = ['all', 'critical', 'high', 'medium', 'low']

export default function PRList() {
    const [search, setSearch] = useState('')
    const [tier, setTier] = useState('all')
    const [type, setType] = useState('all')
    const [priority, setPriority] = useState('all')
    const [slopOnly, setSlopOnly] = useState(false)
    const [page, setPage] = useState(1)

    const { data: prs, isLoading } = useQuery({
        queryKey: ['prs', 'list', tier, type, priority, slopOnly, page],
        queryFn: () => getPRAnalyses({
            limit: 20,
            offset: (page - 1) * 20,
            tier: tier !== 'all' ? tier : null,
            isSlop: slopOnly ? true : null,
        }),
        refetchInterval: 30000,
    })

    // Client side filter
    const filtered = (prs || []).filter(pr => {
        const matchSearch = !search ||
            pr.title?.toLowerCase().includes(search.toLowerCase()) ||
            pr.author?.toLowerCase().includes(search.toLowerCase())
        const matchType = type === 'all' || pr.pr_type === type
        const matchPriority = priority === 'all' || pr.priority === priority
        return matchSearch && matchType && matchPriority
    })

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-7xl mx-auto space-y-6">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-between items-start"
                >
                    <div>
                        <h1 className="text-3xl font-black gradient-text mb-2">
                            Pull Request Analysis
                        </h1>
                        <p className="text-gray-400">
                            {filtered.length} PRs analyzed
                        </p>
                    </div>

                    {/* Slop toggle */}
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setSlopOnly(!slopOnly)}
                        className={`
              flex items-center gap-2 px-4 py-2
              rounded-xl border font-medium text-sm
              transition-all duration-200
              ${slopOnly
                                ? 'bg-red-500/20 border-red-500/40 text-red-400'
                                : 'bg-white/5 border-white/10 text-gray-400'
                            }
            `}
                    >
                        <AlertTriangle className="w-4 h-4" />
                        {slopOnly ? 'Showing Flagged Only' : 'Show Flagged Only'}
                    </motion.button>
                </motion.div>

                {/* Filters */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass rounded-2xl p-4 border border-white/5"
                >
                    <div className="flex flex-wrap gap-4">

                        {/* Search */}
                        <div className="flex-1 min-w-64 relative">
                            <Search className="
                absolute left-3 top-1/2 -translate-y-1/2
                w-4 h-4 text-gray-500
              " />
                            <input
                                type="text"
                                placeholder="Search by title or author..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="
                  w-full pl-10 pr-4 py-2.5
                  bg-white/5 border border-white/10
                  rounded-xl text-sm text-gray-300
                  placeholder-gray-600
                  focus:outline-none focus:border-blue-500/50
                  transition-colors
                "
                            />
                        </div>

                        {/* Tier filter */}
                        <FilterSelect
                            label="Quality"
                            value={tier}
                            options={TIERS}
                            onChange={setTier}
                        />

                        {/* Type filter */}
                        <FilterSelect
                            label="Type"
                            value={type}
                            options={TYPES}
                            onChange={setType}
                        />

                        {/* Priority filter */}
                        <FilterSelect
                            label="Priority"
                            value={priority}
                            options={PRIORITIES}
                            onChange={setPriority}
                        />
                    </div>
                </motion.div>

                {/* PR Cards Grid */}
                {isLoading ? (
                    <LoadingGrid />
                ) : filtered.length === 0 ? (
                    <EmptyState />
                ) : (
                    <div className="grid gap-4">
                        <AnimatePresence>
                            {filtered.map((pr, i) => (
                                <PRCard key={pr.id} pr={pr} index={i} />
                            ))}
                        </AnimatePresence>
                    </div>
                )}

                {/* Pagination */}
                {(prs?.length || 0) >= 20 && (
                    <div className="flex justify-center gap-3">
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="
                px-4 py-2 rounded-xl
                bg-white/5 border border-white/10
                text-gray-400 text-sm
                disabled:opacity-30
                hover:bg-white/10
                transition-all
              "
                        >
                            ← Previous
                        </motion.button>
                        <span className="
              px-4 py-2 rounded-xl
              bg-blue-500/10 border border-blue-500/20
              text-blue-400 text-sm font-medium
            ">
                            Page {page}
                        </span>
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => setPage(p => p + 1)}
                            className="
                px-4 py-2 rounded-xl
                bg-white/5 border border-white/10
                text-gray-400 text-sm
                hover:bg-white/10
                transition-all
              "
                        >
                            Next →
                        </motion.button>
                    </div>
                )}
            </div>
        </div>
    )
}

// ─── PR Card ──────────────────────────────────
function PRCard({ pr, index }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{
                scale: 1.01,
                transition: { duration: 0.2 },
            }}
            className="
        glass rounded-2xl border border-white/5
        hover:border-blue-500/20
        transition-all duration-300
        overflow-hidden group
      "
        >
            <div className="p-6">
                <div className="flex items-start justify-between gap-4">

                    {/* Left — PR Info */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                            <span className="
                text-blue-400 font-bold text-lg
                flex items-center gap-1
              ">
                                <GitPullRequest className="w-4 h-4" />
                                #{pr.pr_number}
                            </span>
                            <QualityBadge
                                tier={pr.quality_tier}
                                score={pr.quality_score}
                            />
                            {pr.is_slop && (
                                <span className="
                  flex items-center gap-1 text-xs
                  text-red-400 bg-red-500/10
                  px-2 py-1 rounded-full
                  border border-red-500/20
                ">
                                    <AlertTriangle className="w-3 h-3" />
                                    AI Slop Flagged
                                </span>
                            )}
                        </div>

                        <h3 className="
              text-gray-200 font-semibold text-base
              truncate mb-1 group-hover:text-white
              transition-colors
            ">
                            {pr.title}
                        </h3>

                        <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>@{pr.author}</span>
                            <span className="font-mono text-xs">
                                {pr.repo}
                            </span>
                            <span>
                                {formatDistanceToNow(
                                    new Date(pr.analyzed_at),
                                    { addSuffix: true }
                                )}
                            </span>
                        </div>
                    </div>

                    {/* Right — Meta */}
                    <div className="flex flex-col items-end gap-2 shrink-0">
                        {/* Type badge */}
                        <span className={`
              text-xs px-3 py-1 rounded-full font-medium
              border
              ${pr.pr_type === 'bug'
                                ? 'bg-red-500/10 text-red-400 border-red-500/20'
                                : pr.pr_type === 'feature'
                                    ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                    : pr.pr_type === 'docs'
                                        ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                        : pr.pr_type === 'security'
                                            ? 'bg-orange-500/10 text-orange-400 border-orange-500/20'
                                            : 'bg-white/5 text-gray-400 border-white/10'
                            }
            `}>
                            {pr.pr_type || 'unknown'}
                        </span>

                        {/* Priority badge */}
                        <span className={`
              text-xs px-3 py-1 rounded-full font-semibold
              ${pr.priority === 'critical'
                                ? 'bg-red-500/15 text-red-400'
                                : pr.priority === 'high'
                                    ? 'bg-orange-500/15 text-orange-400'
                                    : pr.priority === 'medium'
                                        ? 'bg-yellow-500/15 text-yellow-400'
                                        : 'bg-gray-500/15 text-gray-500'
                            }
            `}>
                            {pr.priority} priority
                        </span>

                        {/* Changes */}
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-green-400">
                                +{pr.additions}
                            </span>
                            <span className="text-red-400">
                                -{pr.deletions}
                            </span>
                            <span className="text-gray-500">
                                {pr.files_changed} files
                            </span>
                        </div>
                    </div>
                </div>

                {/* Bottom — Score bars preview */}
                <div className="mt-4 pt-4 border-t border-white/5">
                    <div className="flex items-center justify-between">
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-gray-500">
                                    Quality Score
                                </span>
                                <span className={`
                  text-xs font-bold
                  ${pr.quality_score >= 80 ? 'text-green-400'
                                        : pr.quality_score >= 60 ? 'text-blue-400'
                                            : pr.quality_score >= 40 ? 'text-yellow-400'
                                                : 'text-red-400'
                                    }
                `}>
                                    {pr.quality_score}/100
                                </span>
                            </div>
                            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${pr.quality_score}%` }}
                                    transition={{ duration: 1, delay: 0.2 }}
                                    className={`
                    h-full rounded-full
                    ${pr.quality_score >= 80
                                            ? 'bg-gradient-to-r from-green-500 to-emerald-400'
                                            : pr.quality_score >= 60
                                                ? 'bg-gradient-to-r from-blue-500 to-cyan-400'
                                                : pr.quality_score >= 40
                                                    ? 'bg-gradient-to-r from-yellow-500 to-orange-400'
                                                    : 'bg-gradient-to-r from-red-500 to-pink-400'
                                        }
                  `}
                                />
                            </div>
                        </div>

                        {/* View PR link */}
                        <a
                            href={pr.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="
                ml-4 flex items-center gap-1
                text-xs text-blue-400
                hover:text-blue-300
                transition-colors
              "
                            onClick={e => e.stopPropagation()}
                        >
                            GitHub
                            <ExternalLink className="w-3 h-3" />
                        </a>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

// ─── Filter Select ─────────────────────────────
function FilterSelect({ label, value, options, onChange }) {
    return (
        <div className="relative">
            <select
                value={value}
                onChange={e => onChange(e.target.value)}
                className="
          appearance-none
          bg-white/5 border border-white/10
          rounded-xl px-4 py-2.5 pr-8
          text-sm text-gray-300
          focus:outline-none focus:border-blue-500/50
          transition-colors cursor-pointer
          capitalize
        "
            >
                {options.map(opt => (
                    <option
                        key={opt}
                        value={opt}
                        className="bg-gray-900 capitalize"
                    >
                        {label}: {opt}
                    </option>
                ))}
            </select>
            <ChevronDown className="
        absolute right-2.5 top-1/2 -translate-y-1/2
        w-3.5 h-3.5 text-gray-500 pointer-events-none
      " />
        </div>
    )
}

// ─── Loading Grid ──────────────────────────────
function LoadingGrid() {
    return (
        <div className="space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
                <div
                    key={i}
                    className="
            glass rounded-2xl border border-white/5
            h-32 animate-pulse
          "
                />
            ))}
        </div>
    )
}

// ─── Empty State ───────────────────────────────
function EmptyState() {
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
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="text-5xl mb-4"
            >
                🔍
            </motion.div>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">
                No PRs found
            </h3>
            <p className="text-gray-500">
                Try adjusting your filters
            </p>
        </motion.div>
    )
}