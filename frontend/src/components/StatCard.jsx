import { motion } from 'framer-motion'

const colorMap = {
    blue: {
        bg: 'from-blue-500/10 to-blue-600/5',
        border: 'border-blue-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(88,166,255,0.3)]',
        text: 'text-blue-400',
        icon: 'bg-blue-500/20',
    },
    green: {
        bg: 'from-green-500/10 to-green-600/5',
        border: 'border-green-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(63,185,80,0.3)]',
        text: 'text-green-400',
        icon: 'bg-green-500/20',
    },
    red: {
        bg: 'from-red-500/10 to-red-600/5',
        border: 'border-red-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(248,81,73,0.3)]',
        text: 'text-red-400',
        icon: 'bg-red-500/20',
    },
    purple: {
        bg: 'from-purple-500/10 to-purple-600/5',
        border: 'border-purple-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(188,140,255,0.3)]',
        text: 'text-purple-400',
        icon: 'bg-purple-500/20',
    },
    yellow: {
        bg: 'from-yellow-500/10 to-yellow-600/5',
        border: 'border-yellow-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(210,153,34,0.3)]',
        text: 'text-yellow-400',
        icon: 'bg-yellow-500/20',
    },
    cyan: {
        bg: 'from-cyan-500/10 to-cyan-600/5',
        border: 'border-cyan-500/20',
        glow: 'hover:shadow-[0_0_30px_rgba(57,213,255,0.3)]',
        text: 'text-cyan-400',
        icon: 'bg-cyan-500/20',
    },
}

export default function StatCard({
    icon,
    label,
    value,
    subtitle,
    color = 'blue',
    delay = 0,
    trend,
}) {
    const c = colorMap[color] || colorMap.blue

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
                duration: 0.5,
                delay,
                type: 'spring',
                stiffness: 100,
            }}
            whileHover={{
                scale: 1.03,
                rotateX: 5,
                rotateY: 5,
            }}
            className={`
        relative overflow-hidden rounded-2xl p-6
        bg-gradient-to-br ${c.bg}
        border ${c.border}
        ${c.glow}
        transition-all duration-300
        cursor-default
        card-3d
        glass
      `}
            style={{ transformStyle: 'preserve-3d' }}
        >
            {/* Background orb */}
            <div className={`
        absolute -top-8 -right-8
        w-32 h-32 rounded-full
        ${c.icon} blur-2xl opacity-50
      `} />

            {/* Icon */}
            <div className={`
        inline-flex items-center justify-center
        w-12 h-12 rounded-xl ${c.icon}
        mb-4 text-2xl
      `}>
                {icon}
            </div>

            {/* Value */}
            <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: delay + 0.2, type: 'spring' }}
                className={`text-4xl font-bold ${c.text} mb-1`}
            >
                {value}
            </motion.div>

            {/* Label */}
            <div className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                {label}
            </div>

            {/* Subtitle */}
            {subtitle && (
                <div className="text-xs text-gray-500 mt-1">
                    {subtitle}
                </div>
            )}

            {/* Trend */}
            {trend !== undefined && (
                <div className={`
          absolute top-4 right-4
          text-xs font-semibold px-2 py-1 rounded-full
          ${trend >= 0
                        ? 'text-green-400 bg-green-500/10'
                        : 'text-red-400 bg-red-500/10'
                    }
        `}>
                    {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
                </div>
            )}

            {/* Shine effect */}
            <div className="
        absolute inset-0 opacity-0 hover:opacity-100
        transition-opacity duration-300
        bg-gradient-to-tr from-transparent via-white/3 to-transparent
        pointer-events-none
      " />
        </motion.div>
    )
}