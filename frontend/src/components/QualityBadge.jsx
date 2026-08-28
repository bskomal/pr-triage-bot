import { motion } from 'framer-motion'

const tiers = {
    excellent: {
        label: 'Excellent',
        emoji: '🌟',
        class: 'bg-green-500/15 text-green-400 border-green-500/30',
        glow: 'shadow-[0_0_10px_rgba(63,185,80,0.3)]',
    },
    good: {
        label: 'Good',
        emoji: '✅',
        class: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
        glow: 'shadow-[0_0_10px_rgba(88,166,255,0.3)]',
    },
    'needs-work': {
        label: 'Needs Work',
        emoji: '⚠️',
        class: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
        glow: 'shadow-[0_0_10px_rgba(210,153,34,0.3)]',
    },
    poor: {
        label: 'Poor',
        emoji: '❌',
        class: 'bg-red-500/15 text-red-400 border-red-500/30',
        glow: 'shadow-[0_0_10px_rgba(248,81,73,0.3)]',
    },
}

export default function QualityBadge({ tier, score, showScore = true }) {
    const config = tiers[tier] || tiers['needs-work']

    return (
        <motion.div
            whileHover={{ scale: 1.05 }}
            className={`
        inline-flex items-center gap-1.5
        px-3 py-1 rounded-full text-xs font-semibold
        border ${config.class} ${config.glow}
        transition-all duration-200
      `}
        >
            <span>{config.emoji}</span>
            {showScore && <span>{score}/100</span>}
            <span>{config.label}</span>
        </motion.div>
    )
}