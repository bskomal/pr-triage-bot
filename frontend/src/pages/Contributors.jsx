import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    Trophy,
    Star,
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    Minus,
    User,
    Shield,
} from 'lucide-react'
import { supabase } from '../api/client'

// Fetch contributor data from Supabase
const getContributors = async () => {
    const { data, error } = await supabase
        .from('pr_analyses')
        .select('author, quality_score, quality_tier, is_slop, analyzed_at')
        .order('analyzed_at', { ascending: false })

    if (error) throw error

    // Group by author
    const grouped = {}
    data.forEach(pr => {
        if (!grouped[pr.author]) {
            grouped[pr.author] = []
        }
        grouped[pr.author].push(pr)
    })

    // Calculate profiles
    return Object.entries(grouped).map(([author, prs]) => {
        const scores = prs.map(p => p.quality_score || 0)
        const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length
        const slopCount = prs.filter(p => p.is_slop).length
        const slopRate = slopCount / prs.length
        const excellent = prs.filter(p => p.quality_tier === 'excellent').length

        // Trend
        let trend = 'stable'
        if (scores.length >= 6) {
            const recent = scores.slice(-3).reduce((a, b) => a + b, 0) / 3
            const older = scores.slice(0, 3).reduce((a, b) => a + b, 0) / 3
            if (recent > older + 10) trend = 'improving'
            else if (recent < older - 10) trend = 'declining'
        }

        // Rank
        let rank = 'newcomer'
        if (slopRate >= 0.5) rank = 'watch'
        else if (avgScore >= 75 && prs.length >= 5 && slopRate === 0) rank = 'champion'
        else if (prs.length >= 3 && avgScore >= 50) rank = 'regular'

        // Trust score
        let trust = avgScore
        if (prs.length >= 10) trust += 5
        if (slopRate === 0) trust += 10
        if (trend === 'improving') trust += 5
        trust -= slopRate * 30
        if (prs.length < 3) trust -= 10
        trust = Math.max(0, Math.min(100, trust))

        return {
            username: author,
            total_prs: prs.length,
            avg_score: Math.round(avgScore),
            excellent_prs: excellent,
            slop_count: slopCount,
            slop_rate: Math.round(slopRate * 100),
            trend,
            rank,
            trust_score: Math.round(trust),
        }
    }).sort((a, b) => b.trust_score - a.trust_score)
}

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

export default function Contributors() {
    const { data: contributors, isLoading } = useQuery({
        queryKey: ['contributors'],
        queryFn: getContributors,
        refetchInterval: 60000,
    })

    const champions = contributors?.filter(c => c.rank === 'champion') || []
    const watchList = contributors?.filter(c => c.rank === 'watch') || []

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-3xl font-black gradient-text mb-2">
                        Contributor Intelligence
                    </h1>
                    <p className="text-gray-400">
                        AI-powered contributor reputation and trust scoring
                    </p>
                </motion.div>

                {/* Champions Row */}
                {champions.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                        <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
                            <Trophy className="w-5 h-5 text-yellow-400" />
                            Hall of Champions
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {champions.slice(0, 3).map((c, i) => (
                                <ChampionCard key={c.username} contributor={c} position={i + 1} />
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Watch List Alert */}
                {watchList.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="
              glass rounded-2xl border border-red-500/20
              p-6 bg-red-500/5
            "
                    >
                        <h2 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5" />
                            Watch List — High Slop Rate
                        </h2>
                        <div className="flex flex-wrap gap-3">
                            {watchList.map(c => (
                                <Link
                                    key={c.username}
                                    to={`/contributors/${c.username}`}
                                    className="
                    flex items-center gap-2 px-3 py-2
                    bg-red-500/10 border border-red-500/20
                    rounded-xl text-sm text-red-300
                    hover:bg-red-500/20 transition-colors
                  "
                                >
                                    <AlertTriangle className="w-3 h-3" />
                                    @{c.username}
                                    <span className="text-red-500 text-xs">
                                        {c.slop_rate}% slop
                                    </span>
                                </Link>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Full Leaderboard */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass rounded-2xl border border-white/5 overflow-hidden"
                >
                    <div className="p-6 border-b border-white/5">
                        <h2 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
                            <Shield className="w-5 h-5 text-blue-400" />
                            Contributor Leaderboard
                        </h2>
                    </div>

                    {isLoading ? (
                        <div className="p-8 text-center text-gray-500">
                            Loading contributors...
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-white/5">
                                        {['Rank', 'Contributor', 'Trust Score', 'Avg Quality', 'PRs', 'Slop Rate', 'Trend', 'Status'].map(h => (
                                            <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/3">
                                    {(contributors || []).map((c, i) => (
                                        <ContributorRow
                                            key={c.username}
                                            contributor={c}
                                            position={i + 1}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    )
}

function ChampionCard({ contributor: c, position }) {
    const positionEmoji = ['🥇', '🥈', '🥉'][position - 1] || '🏅'

    return (
        <motion.div
            whileHover={{ scale: 1.03, rotateY: 5 }}
            className="
        glass rounded-2xl border border-yellow-500/20
        bg-yellow-500/5 p-6 text-center
        card-3d
      "
        >
            <div className="text-4xl mb-2">{positionEmoji}</div>
            <div className="text-2xl mb-1">🏆</div>
            <Link
                to={`/contributors/${c.username}`}
                className="font-bold text-white text-lg mb-1 block hover:text-yellow-400 transition-colors"
            >
                @{c.username}
            </Link>
            <div className="text-yellow-400 text-2xl font-black mb-1">
                {c.trust_score}
            </div>
            <div className="text-xs text-gray-500 mb-3">
                Trust Score
            </div>
            <div className="flex justify-center gap-3 text-xs text-gray-400">
                <span>{c.total_prs} PRs</span>
                <span>•</span>
                <span>{c.avg_score}/100 avg</span>
            </div>
        </motion.div>
    )
}

function ContributorRow({ contributor: c, position }) {
    const rank = rankConfig[c.rank] || rankConfig.newcomer
    const TrendIcon = c.trend === 'improving'
        ? TrendingUp
        : c.trend === 'declining'
            ? TrendingDown
            : Minus

    const trendColor = c.trend === 'improving'
        ? 'text-green-400'
        : c.trend === 'declining'
            ? 'text-red-400'
            : 'text-gray-500'

    return (
        <motion.tr
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="hover:bg-white/2 transition-colors"
        >
            <td className="px-6 py-4 text-gray-500 font-mono text-sm">
                #{position}
            </td>
            <td className="px-6 py-4">
                <Link
                    to={`/contributors/${c.username}`}
                    className="flex items-center gap-2 group cursor-pointer"
                >
                    <div className="
            w-8 h-8 rounded-full
            bg-gradient-to-br from-blue-500 to-purple-600
            flex items-center justify-center
            text-xs font-bold text-white
            group-hover:scale-105 transition-transform
          ">
                        {c.username[0].toUpperCase()}
                    </div>
                    <span className="text-gray-200 font-medium group-hover:text-blue-400 transition-colors">
                        @{c.username}
                    </span>
                </Link>
            </td>
            <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                    <span className={`
            text-lg font-black
            ${c.trust_score >= 80 ? 'text-green-400'
                            : c.trust_score >= 60 ? 'text-blue-400'
                                : c.trust_score >= 40 ? 'text-yellow-400'
                                    : 'text-red-400'
                        }
          `}>
                        {c.trust_score}
                    </span>
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${c.trust_score}%` }}
                            transition={{ duration: 1 }}
                            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                        />
                    </div>
                </div>
            </td>
            <td className="px-6 py-4 text-gray-300 font-medium">
                {c.avg_score}/100
            </td>
            <td className="px-6 py-4 text-gray-400">
                {c.total_prs}
            </td>
            <td className="px-6 py-4">
                <span className={`
          text-sm font-medium
          ${c.slop_rate === 0 ? 'text-green-400'
                        : c.slop_rate <= 20 ? 'text-yellow-400'
                            : 'text-red-400'
                    }
        `}>
                    {c.slop_rate}%
                </span>
            </td>
            <td className="px-6 py-4">
                <TrendIcon className={`w-4 h-4 ${trendColor}`} />
            </td>
            <td className="px-6 py-4">
                <span className={`
          inline-flex items-center gap-1.5
          px-2.5 py-1 rounded-full text-xs font-medium
          border ${rank.bg} ${rank.border} ${rank.color}
        `}>
                    {rank.emoji} {rank.label}
                </span>
            </td>
        </motion.tr>
    )
}