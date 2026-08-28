import { motion } from 'framer-motion'

const getColor = (score) => {
    if (score >= 80) return 'from-green-500 to-emerald-400'
    if (score >= 60) return 'from-blue-500 to-cyan-400'
    if (score >= 40) return 'from-yellow-500 to-orange-400'
    return 'from-red-500 to-pink-400'
}

export default function ScoreBar({
    label,
    score,
    reason,
    delay = 0,
}) {
    const color = getColor(score)

    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <span className="text-sm text-gray-300 font-medium">
                    {label}
                </span>
                <span className={`
          text-sm font-bold
          ${score >= 80 ? 'text-green-400'
                        : score >= 60 ? 'text-blue-400'
                            : score >= 40 ? 'text-yellow-400'
                                : 'text-red-400'
                    }
        `}>
                    {score}
                </span>
            </div>

            {/* Bar */}
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${score}%` }}
                    transition={{
                        duration: 1,
                        delay,
                        ease: [0.4, 0, 0.2, 1],
                    }}
                    className={`
            h-full rounded-full
            bg-gradient-to-r ${color}
            relative
          `}
                >
                    {/* Shimmer */}
                    <motion.div
                        animate={{ x: ['-100%', '100%'] }}
                        transition={{
                            duration: 2,
                            repeat: Infinity,
                            repeatDelay: 1,
                        }}
                        className="
              absolute inset-0
              bg-gradient-to-r
              from-transparent via-white/30 to-transparent
            "
                    />
                </motion.div>
            </div>

            {/* Reason */}
            {reason && (
                <p className="text-xs text-gray-500">{reason}</p>
            )}
        </div>
    )
}