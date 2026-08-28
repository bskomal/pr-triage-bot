import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
    Activity,
    TrendingUp,
    Shield,
    Star,
    GitPullRequest,
    AlertTriangle,
    Users,
    Award,
} from 'lucide-react'
import {
    RadarChart, Radar, PolarGrid,
    PolarAngleAxis, ResponsiveContainer,
    AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip,
    BarChart, Bar,
} from 'recharts'

import { getStats, getQualityTrend, getPRAnalyses } from '../api/client'

export default function RepoHealth() {
    const { data: stats } = useQuery({
        queryKey: ['stats'],
        queryFn: getStats,
        refetchInterval: 30000,
    })

    const { data: trend } = useQuery({
        queryKey: ['trend', 30],
        queryFn: () => getQualityTrend(null, 30),
    })

    const { data: prs } = useQuery({
        queryKey: ['prs', 'all'],
        queryFn: () => getPRAnalyses({ limit: 100 }),
    })

    // Health score calculation
    const healthScore = stats ? Math.round(
        (stats.avg_quality * 0.4) +
        ((100 - stats.slop_rate) * 0.3) +
        ((stats.excellent_prs / Math.max(stats.total_prs, 1)) * 100 * 0.3)
    ) : 0

    // Type distribution
    const typeData = prs
        ? Object.entries(
            prs.reduce((acc, pr) => {
                const t = pr.pr_type || 'unknown'
                acc[t] = (acc[t] || 0) + 1
                return acc
            }, {})
        ).map(([name, value]) => ({ name, value }))
        : []

    // Radar chart data
    const radarData = [
        {
            metric: 'Quality',
            value: stats?.avg_quality || 0,
            fullMark: 100,
        },
        {
            metric: 'No Slop',
            value: 100 - (stats?.slop_rate || 0),
            fullMark: 100,
        },
        {
            metric: 'Excellence',
            value: stats
                ? Math.round(
                    (stats.excellent_prs / Math.max(stats.total_prs, 1)) * 100
                )
                : 0,
            fullMark: 100,
        },
        {
            metric: 'Volume',
            value: Math.min((stats?.total_prs || 0) * 10, 100),
            fullMark: 100,
        },
        {
            metric: 'Contributors',
            value: Math.min((stats?.total_authors || 0) * 20, 100),
            fullMark: 100,
        },
    ]

    const healthColor =
        healthScore >= 80 ? '#3fb950' :
            healthScore >= 60 ? '#58a6ff' :
                healthScore >= 40 ? '#d29922' : '#f85149'

    return (
        <div className="min-h-screen pt-24 pb-16 px-6">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-3xl font-black gradient-text mb-2">
                        Repository Health
                    </h1>
                    <p className="text-gray-400">
                        Comprehensive health analysis of your repositories
                    </p>
                </motion.div>

                {/* Health Score Hero */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 }}
                    className="
            glass rounded-2xl border border-white/5 p-8
            relative overflow-hidden
          "
                >
                    <div className="
            absolute inset-0 opacity-5
            bg-gradient-radial from-blue-500 to-transparent
          " />

                    <div className="relative z-10 flex items-center justify-between">
                        <div>
                            <h2 className="
                text-xl font-semibold text-gray-300 mb-2
              ">
                                Overall Repository Health Score
                            </h2>
                            <p className="text-gray-500 text-sm max-w-md">
                                Calculated from quality scores, slop rate,
                                excellent PR ratio, and contributor activity
                            </p>
                        </div>

                        <div className="text-right">
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.3, type: 'spring' }}
                                className="text-8xl font-black"
                                style={{ color: healthColor }}
                            >
                                {healthScore}
                            </motion.div>
                            <div className="text-gray-400 text-sm">
                                Health Score / 100
                            </div>
                        </div>
                    </div>

                    {/* Health bar */}
                    <div className="
            mt-6 h-3 bg-white/5 rounded-full overflow-hidden
          ">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${healthScore}%` }}
                            transition={{ duration: 1.5, delay: 0.5 }}
                            className="h-full rounded-full"
                            style={{
                                background: `linear-gradient(90deg, ${healthColor}88, ${healthColor})`,
                                boxShadow: `0 0 20px ${healthColor}44`,
                            }}
                        />
                    </div>
                </motion.div>

                {/* Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                    {/* Radar Chart */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                        className="glass rounded-2xl border border-white/5 p-6"
                    >
                        <h3 className="
              text-lg font-semibold text-gray-200 mb-6
              flex items-center gap-2
            ">
                            <Activity className="w-5 h-5 text-purple-400" />
                            Health Dimensions
                        </h3>
                        <ResponsiveContainer width="100%" height={280}>
                            <RadarChart data={radarData}>
                                <PolarGrid stroke="rgba(255,255,255,0.05)" />
                                <PolarAngleAxis
                                    dataKey="metric"
                                    tick={{ fill: '#6b7280', fontSize: 12 }}
                                />
                                <Radar
                                    name="Health"
                                    dataKey="value"
                                    stroke="#58a6ff"
                                    fill="#58a6ff"
                                    fillOpacity={0.15}
                                    strokeWidth={2}
                                />
                            </RadarChart>
                        </ResponsiveContainer>
                    </motion.div>

                    {/* PR Type Distribution */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="glass rounded-2xl border border-white/5 p-6"
                    >
                        <h3 className="
              text-lg font-semibold text-gray-200 mb-6
              flex items-center gap-2
            ">
                            <GitPullRequest className="w-5 h-5 text-blue-400" />
                            PR Type Distribution
                        </h3>
                        {typeData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart data={typeData}>
                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="rgba(255,255,255,0.05)"
                                    />
                                    <XAxis
                                        dataKey="name"
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
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
                                    <Bar
                                        dataKey="value"
                                        fill="#58a6ff"
                                        radius={[6, 6, 0, 0]}
                                        fillOpacity={0.8}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="
                h-64 flex items-center justify-center
                text-gray-500 text-sm
              ">
                                No data yet
                            </div>
                        )}
                    </motion.div>

                    {/* 30-Day Quality Trend */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="
              lg:col-span-2
              glass rounded-2xl border border-white/5 p-6
            "
                    >
                        <h3 className="
              text-lg font-semibold text-gray-200 mb-6
              flex items-center gap-2
            ">
                            <TrendingUp className="w-5 h-5 text-green-400" />
                            30-Day Quality Trend
                        </h3>
                        {trend && trend.length > 0 ? (
                            <ResponsiveContainer width="100%" height={220}>
                                <AreaChart data={trend}>
                                    <defs>
                                        <linearGradient
                                            id="scoreGrad"
                                            x1="0" y1="0" x2="0" y2="1"
                                        >
                                            <stop
                                                offset="5%"
                                                stopColor="#3fb950"
                                                stopOpacity={0.3}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor="#3fb950"
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                        <linearGradient
                                            id="slopGrad"
                                            x1="0" y1="0" x2="0" y2="1"
                                        >
                                            <stop
                                                offset="5%"
                                                stopColor="#f85149"
                                                stopOpacity={0.3}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor="#f85149"
                                                stopOpacity={0}
                                            />
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
                                        name="Avg Quality"
                                        stroke="#3fb950"
                                        strokeWidth={2}
                                        fill="url(#scoreGrad)"
                                        dot={{ fill: '#3fb950', r: 3 }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="slop_count"
                                        name="Slop Count"
                                        stroke="#f85149"
                                        strokeWidth={2}
                                        fill="url(#slopGrad)"
                                        dot={{ fill: '#f85149', r: 3 }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="
                h-48 flex items-center justify-center
                text-gray-500 text-sm
              ">
                                No trend data yet — run the bot daily!
                            </div>
                        )}
                    </motion.div>
                </div>

                {/* Key Metrics */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="grid grid-cols-2 md:grid-cols-4 gap-4"
                >
                    {[
                        {
                            icon: <Star className="w-6 h-6" />,
                            label: 'Avg Quality',
                            value: `${stats?.avg_quality || 0}/100`,
                            color: 'text-yellow-400',
                            bg: 'bg-yellow-500/10',
                            border: 'border-yellow-500/20',
                        },
                        {
                            icon: <Shield className="w-6 h-6" />,
                            label: 'Slop Rate',
                            value: `${stats?.slop_rate || 0}%`,
                            color: 'text-red-400',
                            bg: 'bg-red-500/10',
                            border: 'border-red-500/20',
                        },
                        {
                            icon: <Award className="w-6 h-6" />,
                            label: 'Excellence Rate',
                            value: stats
                                ? `${Math.round(
                                    (stats.excellent_prs /
                                        Math.max(stats.total_prs, 1)) * 100
                                )}%`
                                : '0%',
                            color: 'text-green-400',
                            bg: 'bg-green-500/10',
                            border: 'border-green-500/20',
                        },
                        {
                            icon: <Users className="w-6 h-6" />,
                            label: 'Contributors',
                            value: stats?.total_authors || 0,
                            color: 'text-purple-400',
                            bg: 'bg-purple-500/10',
                            border: 'border-purple-500/20',
                        },
                    ].map((metric, i) => (
                        <motion.div
                            key={metric.label}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.5 + i * 0.1 }}
                            whileHover={{ scale: 1.03 }}
                            className={`
                glass rounded-2xl p-6 text-center
                border ${metric.border}
                ${metric.bg}
                transition-all duration-200
              `}
                        >
                            <div className={`
                inline-flex items-center justify-center
                w-12 h-12 rounded-xl ${metric.bg}
                mb-3 ${metric.color}
              `}>
                                {metric.icon}
                            </div>
                            <div className={`
                text-3xl font-black mb-1 ${metric.color}
              `}>
                                {metric.value}
                            </div>
                            <div className="text-xs text-gray-500 uppercase tracking-wider">
                                {metric.label}
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            </div>
        </div>
    )
}