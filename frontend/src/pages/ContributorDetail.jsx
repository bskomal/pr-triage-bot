import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    ArrowLeft,
    Shield,
    Trophy,
    Star,
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    Minus,
    GitPullRequest,
    CheckCircle,
    XCircle,
    Calendar,
} from 'lucide-react'
import { getContributorDetail } from '../api/client'

const rankConfig = {
    champion: {
        emoji: '🏆',
        color: 'text-yellow-400',
        bg: 'bg-yellow-500/10',
        border: 'border-yellow-500/20',
        label: 'Champion',
    },
    regular: {
        emoji: '⭐',
        color: 'text-blue-400',
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/20',
        label: 'Regular',
    },
    newcomer: {
        emoji: '🌱',
        color: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        label: 'Newcomer',
    },
    watch: {
        emoji: '⚠️',
        color: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        label: 'Watch List',
    },
}

export default function ContributorDetail() {
    const { username } = useParams()

    const { data: profile, isLoading, error } = useQuery({
        queryKey: ['contributor', username],
        queryFn: () => getContributorDetail(username),
        enabled: Boolean(username),
    })

    if (isLoading) {
        return (
            <div className="min-h-screen pt-24 pb-16 px-6 flex items-center justify-center">
                <div className="text-gray-400 flex items-center gap-3">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"
                    />
                    <span>Loading contributor profile...</span>
                </div>
            </div>
        )
    }

    if (error || !profile) {
        return (
            <div className="min-h-screen pt-24 pb-16 px-6 max-w-4xl mx-auto space-y-6 text-center">
                <Link
                    to="/contributors"
                    className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-6"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Leaderboard
                </Link>
                <div className="glass p-8 rounded-2xl border border-white/5 space-y-4">
                    <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto" />
                    <h2 className="text-xl font-bold text-gray-200">Contributor Not Found</h2>
                    <p className="text-gray-400 text-sm">
                        No analysis history was found for author <span className="text-white font-mono">@{username}</span>.
                    </p>
                </div>
            </div>
        )
    }

    const rank = rankConfig[profile.rank] || rankConfig.newcomer
    const TrendIcon = profile.trend === 'improving'
        ? TrendingUp
        : profile.trend === 'declining'
            ? TrendingDown
            : Minus

    const trendColor = profile.trend === 'improving'
        ? 'text-green-400'
        : profile.trend === 'declining'
            ? 'text-red-400'
            : 'text-gray-500'

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-6xl mx-auto space-y-8">

                {/* Back Button */}
                <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <Link
                        to="/contributors"
                        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to Contributor Leaderboard
                    </Link>
                </motion.div>

                {/* Profile Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass rounded-3xl border border-white/10 p-8 relative overflow-hidden"
                >
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                        <div className="flex items-center gap-5">
                            <div className="
                                w-16 h-16 rounded-2xl
                                bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600
                                flex items-center justify-center
                                text-2xl font-black text-white shadow-lg
                                shadow-blue-500/20
                            ">
                                {profile.username[0]?.toUpperCase()}
                            </div>
                            <div>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-3xl font-black text-white">
                                        @{profile.username}
                                    </h1>
                                    <span className={`
                                        inline-flex items-center gap-1.5
                                        px-3 py-1 rounded-full text-xs font-semibold
                                        border ${rank.bg} ${rank.border} ${rank.color}
                                    `}>
                                        {rank.emoji} {rank.label}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                                    <span className="flex items-center gap-1">
                                        <Shield className="w-4 h-4 text-blue-400" />
                                        Contributor Intelligence Profile
                                    </span>
                                    <span>•</span>
                                    <span className={`flex items-center gap-1 font-medium ${trendColor}`}>
                                        <TrendIcon className="w-4 h-4" />
                                        {profile.trend.charAt(0).toUpperCase() + profile.trend.slice(1)} Quality Trend
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Trust Score Gauge */}
                        <div className="glass rounded-2xl border border-white/5 p-4 flex items-center gap-4 bg-white/5">
                            <div>
                                <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                                    Trust Score
                                </div>
                                <div className={`
                                    text-3xl font-black mt-0.5
                                    ${profile.trust_score >= 80 ? 'text-green-400'
                                        : profile.trust_score >= 60 ? 'text-blue-400'
                                            : profile.trust_score >= 40 ? 'text-yellow-400'
                                                : 'text-red-400'}
                                `}>
                                    {profile.trust_score}<span className="text-sm font-normal text-gray-500">/100</span>
                                </div>
                            </div>
                            <div className="w-24">
                                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${profile.trust_score}%` }}
                                        transition={{ duration: 1 }}
                                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Stat Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <StatCard
                        title="Total PRs Analyzed"
                        value={profile.total_prs}
                        icon={GitPullRequest}
                        color="text-blue-400"
                        delay={0.1}
                    />
                    <StatCard
                        title="Avg Quality Score"
                        value={`${profile.avg_score}/100`}
                        icon={Star}
                        color="text-purple-400"
                        delay={0.15}
                    />
                    <StatCard
                        title="Slop Rate"
                        value={`${profile.slop_rate}%`}
                        subtitle={`${profile.slop_count} flag(s)`}
                        icon={AlertTriangle}
                        color={profile.slop_rate > 20 ? 'text-red-400' : 'text-green-400'}
                        delay={0.2}
                    />
                    <StatCard
                        title="Excellent PRs"
                        value={profile.excellent_prs}
                        icon={Trophy}
                        color="text-yellow-400"
                        delay={0.25}
                    />
                </div>

                {/* PR History List */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass rounded-2xl border border-white/5 overflow-hidden space-y-0"
                >
                    <div className="p-6 border-b border-white/5 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
                            <GitPullRequest className="w-5 h-5 text-blue-400" />
                            Analyzed Pull Requests ({profile.prs.length})
                        </h2>
                    </div>

                    <div className="divide-y divide-white/5">
                        {profile.prs.map((pr) => {
                            const [owner, repoName] = (pr.repo || '').split('/')
                            return (
                                <div
                                    key={pr.id || pr.pr_number + pr.analyzed_at}
                                    className="p-5 hover:bg-white/2 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                                >
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-mono">
                                                {pr.repo} #{pr.pr_number}
                                            </span>
                                            {pr.is_slop && (
                                                <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 font-medium">
                                                    <AlertTriangle className="w-3 h-3" /> Slop Flagged
                                                </span>
                                            )}
                                            {pr.quality_tier && (
                                                <span className="text-xs px-2.5 py-0.5 rounded-full bg-white/5 border border-white/10 text-gray-300 capitalize">
                                                    {pr.quality_tier}
                                                </span>
                                            )}
                                        </div>
                                        <h3 className="text-base font-semibold text-gray-100 hover:text-blue-400 transition-colors">
                                            {owner && repoName ? (
                                                <Link to={`/pr/${owner}/${repoName}/${pr.pr_number}`}>
                                                    {pr.title || `PR #${pr.pr_number}`}
                                                </Link>
                                            ) : (
                                                <span>{pr.title || `PR #${pr.pr_number}`}</span>
                                            )}
                                        </h3>
                                        <div className="flex items-center gap-4 text-xs text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="w-3 h-3" />
                                                {new Date(pr.analyzed_at).toLocaleDateString(undefined, {
                                                    year: 'numeric',
                                                    month: 'short',
                                                    day: 'numeric',
                                                })}
                                            </span>
                                            {pr.pr_type && <span>Type: {pr.pr_type}</span>}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4 self-end md:self-center">
                                        <div className="text-right">
                                            <div className="text-xs text-gray-400 font-medium">Quality Score</div>
                                            <div className={`text-lg font-black ${
                                                pr.quality_score >= 80 ? 'text-green-400'
                                                : pr.quality_score >= 60 ? 'text-blue-400'
                                                : pr.quality_score >= 40 ? 'text-yellow-400'
                                                : 'text-red-400'
                                            }`}>
                                                {pr.quality_score || 0}/100
                                            </div>
                                        </div>

                                        {owner && repoName && (
                                            <Link
                                                to={`/pr/${owner}/${repoName}/${pr.pr_number}`}
                                                className="px-4 py-2 rounded-xl text-xs font-medium bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 transition-all"
                                            >
                                                View Analysis
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </motion.div>

            </div>
        </div>
    )
}

function StatCard({ title, value, subtitle, icon: Icon, color, delay }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className="glass rounded-2xl border border-white/5 p-5 card-3d"
        >
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                    {title}
                </span>
                <div className={`p-2 rounded-xl bg-white/5 ${color}`}>
                    <Icon className="w-4 h-4" />
                </div>
            </div>
            <div className="text-2xl font-black text-white">{value}</div>
            {subtitle && (
                <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
            )}
        </motion.div>
    )
}
