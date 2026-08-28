import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts'
import {
    GitPullRequest, Shield, Star,
    TrendingUp, Users, Zap,
    AlertTriangle, CheckCircle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

import StatCard from '../components/StatCard'
import QualityBadge from '../components/QualityBadge'
import { getStats, getPRAnalyses, getQualityTrend } from '../api/client'

const PIE_COLORS = ['#3fb950', '#58a6ff', '#d29922', '#f85149']

export default function Dashboard() {
    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ['stats'],
        queryFn: getStats,
        refetchInterval: 30000,
    })

    const { data: recentPRs } = useQuery({
        queryKey: ['prs', 'recent'],
        queryFn: () => getPRAnalyses({ limit: 8 }),
        refetchInterval: 30000,
    })

    const { data: trend } = useQuery({
        queryKey: ['trend'],
        queryFn: () => getQualityTrend(null, 14),
    })

    // Tier distribution for pie chart
    const tierData = recentPRs
        ? Object.entries(
            recentPRs.reduce((acc, pr) => {
                acc[pr.quality_tier] = (acc[pr.quality_tier] || 0) + 1
                return acc
            }, {})
        ).map(([name, value]) => ({ name, value }))
        : []

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Hero Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center py-8"
                >
                    <motion.div
                        animate={{ scale: [1, 1.02, 1] }}
                        transition={{ duration: 3, repeat: Infinity }}
                        className="
              inline-flex items-center gap-2
              px-4 py-2 rounded-full mb-6
              bg-blue-500/10 border border-blue-500/20
              text-blue-400 text-sm font-medium
            "
                    >
                        <Zap className="w-4 h-4" />
                        Powered by Llama 3.2 — Running Locally
                    </motion.div>

                    <h1 className="text-5xl font-black mb-4">
                        <span className="gradient-text">
                            PR Triage Intelligence
                        </span>
                    </h1>
                    <p className="text-gray-400 text-xl max-w-2xl mx-auto">
                        AI-powered pull request analysis, quality scoring,
                        and slop detection — all running privately on your machine.
                    </p>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <StatCard
                        icon={<GitPullRequest className="w-6 h-6" />}
                        label="PRs Analyzed"
                        value={statsLoading ? '...' : stats?.total_prs ?? 0}
                        color="blue"
                        delay={0.1}
                    />
                    <StatCard
                        icon={<Star className="w-6 h-6" />}
                        label="Avg Quality"
                        value={statsLoading ? '...' : `${stats?.avg_quality ?? 0}`}
                        subtitle="out of 100"
                        color="green"
                        delay={0.2}
                    />
                    <StatCard
                        icon={<Shield className="w-6 h-6" />}
                        label="Slop Flagged"
                        value={statsLoading ? '...' : stats?.total_slop ?? 0}
                        color="red"
                        delay={0.3}
                    />
                    <StatCard
                        icon={<CheckCircle className="w-6 h-6" />}
                        label="Excellent PRs"
                        value={statsLoading ? '...' : stats?.excellent_prs ?? 0}
                        color="cyan"
                        delay={0.4}
                    />
                    <StatCard
                        icon={<Users className="w-6 h-6" />}
                        label="Contributors"
                        value={statsLoading ? '...' : stats?.total_authors ?? 0}
                        color="purple"
                        delay={0.5}
                    />
                    <StatCard
                        icon={<TrendingUp className="w-6 h-6" />}
                        label="Repos"
                        value={statsLoading ? '...' : stats?.total_repos ?? 0}
                        color="yellow"
                        delay={0.6}
                    />
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Quality Trend */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="lg:col-span-2 glass rounded-2xl p-6 border border-white/5"
                    >
                        <h3 className="text-lg font-semibold text-gray-200 mb-6 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-blue-400" />
                            Quality Trend (14 Days)
                        </h3>

                        {trend && trend.length > 0 ? (
                            <ResponsiveContainer width="100%" height={200}>
                                <AreaChart data={trend}>
                                    <defs>
                                        <linearGradient id="qualityGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#58a6ff" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#58a6ff" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="rgba(255,255,255,0.05)"
                                    />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        domain={[0, 100]}
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: '#161b22',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            borderRadius: '12px',
                                            color: '#e6edf3',
                                        }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="avg_score"
                                        stroke="#58a6ff"
                                        strokeWidth={2}
                                        fill="url(#qualityGrad)"
                                        dot={{ fill: '#58a6ff', strokeWidth: 2, r: 4 }}
                                        activeDot={{ r: 6, fill: '#79c0ff' }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-48 flex items-center justify-center">
                                <p className="text-gray-500 text-sm">
                                    No trend data yet. Run the bot to see charts!
                                </p>
                            </div>
                        )}
                    </motion.div>

                    {/* Tier Distribution */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="glass rounded-2xl p-6 border border-white/5"
                    >
                        <h3 className="text-lg font-semibold text-gray-200 mb-6 flex items-center gap-2">
                            <Star className="w-5 h-5 text-yellow-400" />
                            Quality Distribution
                        </h3>

                        {tierData.length > 0 ? (
                            <>
                                <ResponsiveContainer width="100%" height={160}>
                                    <PieChart>
                                        <Pie
                                            data={tierData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={45}
                                            outerRadius={75}
                                            paddingAngle={4}
                                            dataKey="value"
                                        >
                                            {tierData.map((_, i) => (
                                                <Cell
                                                    key={i}
                                                    fill={PIE_COLORS[i % PIE_COLORS.length]}
                                                />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{
                                                background: '#161b22',
                                                border: '1px solid rgba(255,255,255,0.1)',
                                                borderRadius: '12px',
                                                color: '#e6edf3',
                                            }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>

                                <div className="space-y-2 mt-2">
                                    {tierData.map((item, i) => (
                                        <div
                                            key={item.name}
                                            className="flex items-center justify-between text-sm"
                                        >
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className="w-2 h-2 rounded-full"
                                                    style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                                                />
                                                <span className="text-gray-400 capitalize">
                                                    {item.name}
                                                </span>
                                            </div>
                                            <span className="text-gray-300 font-medium">
                                                {item.value}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="h-40 flex items-center justify-center">
                                <p className="text-gray-500 text-sm text-center">
                                    No data yet
                                </p>
                            </div>
                        )}
                    </motion.div>
                </div>

                {/* Recent PRs Table */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="glass rounded-2xl border border-white/5 overflow-hidden"
                >
                    <div className="p-6 border-b border-white/5 flex justify-between items-center">
                        <h3 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
                            <GitPullRequest className="w-5 h-5 text-blue-400" />
                            Recent PR Analyses
                        </h3>
                        <a
                            href="/prs"
                            className="
                text-sm text-blue-400 hover:text-blue-300
                transition-colors flex items-center gap-1
              "
                        >
                            View all →
                        </a>
                    </div>

                    {recentPRs && recentPRs.length > 0 ? (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-white/5">
                                        {['PR', 'Repository', 'Author', 'Quality', 'Type', 'Priority', 'Slop', 'Analyzed'].map(h => (
                                            <th
                                                key={h}
                                                className="
                          px-6 py-3 text-left text-xs
                          font-semibold text-gray-500
                          uppercase tracking-wider
                        "
                                            >
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/3">
                                    {recentPRs.map((pr, i) => (
                                        <motion.tr
                                            key={pr.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            className="
                        hover:bg-white/2 transition-colors
                        group cursor-pointer
                      "
                                        >
                                            <td className="px-6 py-4">
                                                <div className="text-blue-400 font-semibold">
                                                    #{pr.pr_number}
                                                </div>
                                                <div className="text-xs text-gray-500 max-w-[200px] truncate">
                                                    {pr.title}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="text-xs font-mono text-gray-400">
                                                    {pr.repo}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="text-sm text-gray-300">
                                                    @{pr.author}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <QualityBadge
                                                    tier={pr.quality_tier}
                                                    score={pr.quality_score}
                                                />
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="
                          text-xs px-2 py-1 rounded-lg
                          bg-white/5 text-gray-400
                          border border-white/5
                        ">
                                                    {pr.pr_type || 'unknown'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`
                          text-xs px-2 py-1 rounded-lg font-medium
                          ${pr.priority === 'critical'
                                                        ? 'bg-red-500/15 text-red-400'
                                                        : pr.priority === 'high'
                                                            ? 'bg-orange-500/15 text-orange-400'
                                                            : pr.priority === 'medium'
                                                                ? 'bg-yellow-500/15 text-yellow-400'
                                                                : 'bg-gray-500/15 text-gray-400'
                                                    }
                        `}>
                                                    {pr.priority}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                {pr.is_slop ? (
                                                    <span className="
                            flex items-center gap-1 text-xs
                            text-red-400 bg-red-500/10
                            px-2 py-1 rounded-lg
                          ">
                                                        <AlertTriangle className="w-3 h-3" />
                                                        Flagged
                                                    </span>
                                                ) : (
                                                    <span className="
                            flex items-center gap-1 text-xs
                            text-green-400 bg-green-500/10
                            px-2 py-1 rounded-lg
                          ">
                                                        <CheckCircle className="w-3 h-3" />
                                                        Clean
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-xs text-gray-500">
                                                {formatDistanceToNow(
                                                    new Date(pr.analyzed_at),
                                                    { addSuffix: true }
                                                )}
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="py-24 text-center">
                            <motion.div
                                animate={{ y: [0, -10, 0] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                className="text-5xl mb-4"
                            >
                                🔍
                            </motion.div>
                            <h3 className="text-xl font-semibold text-gray-300 mb-2">
                                No PRs analyzed yet
                            </h3>
                            <p className="text-gray-500 mb-6">
                                Run the triage bot to start seeing results
                            </p>
                            <code className="
                block mx-auto max-w-lg
                bg-black/30 border border-white/10
                rounded-xl px-4 py-3
                text-sm text-green-400 font-mono
                text-left
              ">
                                python -m src.cli.main analyze-pr
                                --repo owner/repo --pr 1
                                --provider ollama --dry-run
                            </code>
                        </div>
                    )}
                </motion.div>

            </div>
        </div>
    )
}