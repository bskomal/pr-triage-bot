import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    GitPullRequest,
    AlertTriangle,
    CheckCircle,
    ExternalLink,
    ArrowLeft,
    User,
    Calendar,
    FileCode,
    Tag,
    Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatDistanceToNow, format } from 'date-fns'

import QualityBadge from '../components/QualityBadge'
import ScoreBar from '../components/ScoreBar'
import { getPRDetail } from '../api/client'

const DIMENSION_LABELS = {
    description_quality: 'Description Quality',
    test_coverage: 'Test Coverage',
    documentation: 'Documentation',
    scope_focus: 'Scope Focus',
    commit_quality: 'Commit Quality',
    linked_issue: 'Issue Linkage',
}

export default function PRDetail() {
    const { owner, repo, number } = useParams()
    const fullRepo = `${owner}/${repo}`

    const { data: pr, isLoading, error } = useQuery({
        queryKey: ['pr', fullRepo, number],
        queryFn: () => getPRDetail(fullRepo, parseInt(number)),
    })

    if (isLoading) return <LoadingState />
    if (error || !pr) return <ErrorState repo={fullRepo} number={number} />

    const signals = Array.isArray(pr.slop_signals)
        ? pr.slop_signals
        : JSON.parse(pr.slop_signals || '[]')

    const labels = Array.isArray(pr.recommended_labels)
        ? pr.recommended_labels
        : JSON.parse(pr.recommended_labels || '[]')

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-5xl mx-auto space-y-6">

                {/* Back button */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <Link
                        to="/prs"
                        className="
              inline-flex items-center gap-2
              text-gray-400 hover:text-gray-200
              transition-colors text-sm
            "
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to PRs
                    </Link>
                </motion.div>

                {/* PR Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="
            glass rounded-2xl border border-white/5 p-8
            relative overflow-hidden
          "
                >
                    {/* Background glow */}
                    <div className={`
            absolute top-0 right-0 w-64 h-64
            rounded-full blur-3xl opacity-10
            ${pr.is_slop
                            ? 'bg-red-500'
                            : pr.quality_tier === 'excellent'
                                ? 'bg-green-500'
                                : 'bg-blue-500'
                        }
          `} />

                    <div className="relative z-10">
                        {/* PR number and title */}
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="
                    text-blue-400 font-bold text-2xl
                    flex items-center gap-2
                  ">
                                        <GitPullRequest className="w-6 h-6" />
                                        PR #{pr.pr_number}
                                    </span>
                                    <QualityBadge
                                        tier={pr.quality_tier}
                                        score={pr.quality_score}
                                    />
                                    {pr.is_slop && (
                                        <span className="
                      flex items-center gap-1 text-sm
                      text-red-400 bg-red-500/10
                      px-3 py-1 rounded-full
                      border border-red-500/20
                      animate-pulse
                    ">
                                            <AlertTriangle className="w-4 h-4" />
                                            AI Slop Flagged
                                        </span>
                                    )}
                                </div>

                                <h1 className="
                  text-2xl font-bold text-white mb-4
                ">
                                    {pr.title}
                                </h1>

                                {/* Meta info */}
                                <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                                    <span className="flex items-center gap-1.5">
                                        <User className="w-4 h-4" />
                                        @{pr.author}
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <FileCode className="w-4 h-4" />
                                        {pr.files_changed} files changed
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <Calendar className="w-4 h-4" />
                                        {format(
                                            new Date(pr.analyzed_at),
                                            'MMM d, yyyy HH:mm'
                                        )}
                                    </span>
                                    <span className="
                    font-mono text-xs bg-white/5
                    px-2 py-1 rounded-lg
                    border border-white/10
                  ">
                                        {pr.repo}
                                    </span>
                                </div>
                            </div>

                            {/* View on GitHub */}
                            {pr.url && (
                                <a
                                    href={pr.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="
                    flex items-center gap-2
                    px-4 py-2 rounded-xl
                    bg-white/5 border border-white/10
                    text-gray-300 text-sm
                    hover:bg-white/10
                    transition-all shrink-0
                  "
                                >
                                    <ExternalLink className="w-4 h-4" />
                                    View on GitHub
                                </a>
                            )}
                        </div>

                        {/* Labels */}
                        {labels.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-4">
                                <Tag className="w-4 h-4 text-gray-500 self-center" />
                                {labels.map(label => (
                                    <span
                                        key={label}
                                        className="
                      text-xs px-3 py-1 rounded-full
                      bg-white/5 border border-white/10
                      text-gray-300
                    "
                                    >
                                        {label}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* Two column layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                    {/* Quality Score Breakdown */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                        className="
              glass rounded-2xl border border-white/5 p-6
            "
                    >
                        <h2 className="
              text-lg font-semibold text-gray-200 mb-6
              flex items-center gap-2
            ">
                            <Zap className="w-5 h-5 text-yellow-400" />
                            Quality Score Breakdown
                        </h2>

                        {/* Overall score big display */}
                        <div className="text-center mb-8">
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{
                                    delay: 0.3,
                                    type: 'spring',
                                    stiffness: 200,
                                }}
                                className={`
                  text-7xl font-black mb-2
                  ${pr.quality_score >= 80 ? 'text-green-400'
                                        : pr.quality_score >= 60 ? 'text-blue-400'
                                            : pr.quality_score >= 40 ? 'text-yellow-400'
                                                : 'text-red-400'
                                    }
                `}
                            >
                                {pr.quality_score}
                            </motion.div>
                            <div className="text-gray-400 text-sm">
                                out of 100
                            </div>
                            <QualityBadge
                                tier={pr.quality_tier}
                                score={pr.quality_score}
                                showScore={false}
                            />
                        </div>

                        {/* Score bars */}
                        <div className="space-y-5">
                            {Object.entries(DIMENSION_LABELS).map(
                                ([key, label], i) => (
                                    <ScoreBar
                                        key={key}
                                        label={label}
                                        score={50}
                                        delay={i * 0.1}
                                    />
                                )
                            )}
                        </div>

                        {/* Feedback */}
                        {pr.feedback && (
                            <div className="
                mt-6 p-4 rounded-xl
                bg-blue-500/5 border border-blue-500/20
              ">
                                <p className="text-sm text-blue-300 leading-relaxed">
                                    💡 {pr.feedback}
                                </p>
                            </div>
                        )}
                    </motion.div>

                    {/* Slop Detection */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="space-y-6"
                    >

                        {/* Slop Analysis Card */}
                        <div className={`
              glass rounded-2xl border p-6
              ${pr.is_slop
                                ? 'border-red-500/20'
                                : 'border-green-500/20'
                            }
            `}>
                            <h2 className="
                text-lg font-semibold text-gray-200 mb-6
                flex items-center gap-2
              ">
                                <AlertTriangle className={`
                  w-5 h-5
                  ${pr.is_slop ? 'text-red-400' : 'text-green-400'}
                `} />
                                Slop Detection Analysis
                            </h2>

                            {/* Verdict */}
                            <div className={`
                flex items-center gap-3 p-4
                rounded-xl mb-6
                ${pr.is_slop
                                    ? 'bg-red-500/10 border border-red-500/20'
                                    : 'bg-green-500/10 border border-green-500/20'
                                }
              `}>
                                {pr.is_slop ? (
                                    <AlertTriangle className="w-8 h-8 text-red-400 shrink-0" />
                                ) : (
                                    <CheckCircle className="w-8 h-8 text-green-400 shrink-0" />
                                )}
                                <div>
                                    <div className={`
                    font-bold text-lg
                    ${pr.is_slop ? 'text-red-400' : 'text-green-400'}
                  `}>
                                        {pr.is_slop ? 'AI Slop Detected' : 'Looks Genuine'}
                                    </div>
                                    <div className="text-sm text-gray-400">
                                        Confidence: {Math.round(
                                            (pr.slop_confidence || 0) * 100
                                        )}% | Severity: {pr.slop_severity || 'low'}
                                    </div>
                                </div>
                            </div>

                            {/* Confidence bar */}
                            <div className="mb-6">
                                <div className="flex justify-between text-xs text-gray-500 mb-2">
                                    <span>Slop Confidence</span>
                                    <span>
                                        {Math.round((pr.slop_confidence || 0) * 100)}%
                                    </span>
                                </div>
                                <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{
                                            width: `${(pr.slop_confidence || 0) * 100}%`
                                        }}
                                        transition={{ duration: 1, delay: 0.5 }}
                                        className={`
                      h-full rounded-full
                      ${pr.is_slop
                                                ? 'bg-gradient-to-r from-red-500 to-pink-400'
                                                : 'bg-gradient-to-r from-green-500 to-emerald-400'
                                            }
                    `}
                                    />
                                </div>
                            </div>

                            {/* Signals */}
                            {signals.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-gray-400 mb-3">
                                        Signals Detected:
                                    </h3>
                                    <div className="space-y-2">
                                        {signals.map((signal, i) => (
                                            <motion.div
                                                key={signal}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: i * 0.1 }}
                                                className="
                          flex items-center gap-2 text-sm
                          text-red-300 bg-red-500/5
                          px-3 py-2 rounded-lg
                          border border-red-500/10
                        "
                                            >
                                                <AlertTriangle className="w-3 h-3 shrink-0" />
                                                {signal.replace(/_/g, ' ')}
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {signals.length === 0 && !pr.is_slop && (
                                <div className="
                  flex items-center gap-2 text-sm
                  text-green-300 bg-green-500/5
                  px-3 py-2 rounded-lg
                  border border-green-500/10
                ">
                                    <CheckCircle className="w-4 h-4" />
                                    No suspicious signals detected
                                </div>
                            )}
                        </div>

                        {/* PR Stats Card */}
                        <div className="
              glass rounded-2xl border border-white/5 p-6
            ">
                            <h2 className="
                text-lg font-semibold text-gray-200 mb-4
              ">
                                PR Statistics
                            </h2>
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    {
                                        label: 'Additions',
                                        value: `+${pr.additions}`,
                                        color: 'text-green-400',
                                    },
                                    {
                                        label: 'Deletions',
                                        value: `-${pr.deletions}`,
                                        color: 'text-red-400',
                                    },
                                    {
                                        label: 'Files Changed',
                                        value: pr.files_changed,
                                        color: 'text-blue-400',
                                    },
                                    {
                                        label: 'Type',
                                        value: pr.pr_type || 'unknown',
                                        color: 'text-purple-400',
                                    },
                                    {
                                        label: 'Priority',
                                        value: pr.priority || 'medium',
                                        color: 'text-yellow-400',
                                    },
                                    {
                                        label: 'Complexity',
                                        value: pr.complexity || 'medium',
                                        color: 'text-cyan-400',
                                    },
                                ].map(stat => (
                                    <div
                                        key={stat.label}
                                        className="
                      bg-white/3 rounded-xl p-3
                      border border-white/5
                    "
                                    >
                                        <div className="text-xs text-gray-500 mb-1">
                                            {stat.label}
                                        </div>
                                        <div className={`
                      font-bold capitalize ${stat.color}
                    `}>
                                            {stat.value}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
    )
}

function LoadingState() {
    return (
        <div className="min-h-screen pt-24 px-6">
            <div className="max-w-5xl mx-auto space-y-6">
                {[1, 2, 3].map(i => (
                    <div
                        key={i}
                        className="glass rounded-2xl border border-white/5 h-48 animate-pulse"
                    />
                ))}
            </div>
        </div>
    )
}

function ErrorState({ repo, number }) {
    return (
        <div className="min-h-screen pt-24 px-6 flex items-center justify-center">
            <div className="text-center">
                <div className="text-5xl mb-4">😕</div>
                <h2 className="text-2xl font-bold text-gray-300 mb-2">
                    PR Not Found
                </h2>
                <p className="text-gray-500 mb-6">
                    PR #{number} in {repo} has not been analyzed yet
                </p>
                <Link
                    to="/prs"
                    className="
            px-6 py-3 rounded-xl
            bg-blue-500/10 border border-blue-500/20
            text-blue-400 font-medium
            hover:bg-blue-500/20 transition-all
          "
                >
                    Back to PR List
                </Link>
            </div>
        </div>
    )
}