import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertTriangle, X, Zap } from 'lucide-react'
import { supabase } from '../api/client'

export default function ToastNotification() {
    const [toasts, setToasts] = useState([])

    useEffect(() => {
        // Subscribe to real time PR insertions
        const channel = supabase
            .channel('pr_notifications')
            .on(
                'postgres_changes',
                {
                    event: 'INSERT',
                    schema: 'public',
                    table: 'pr_analyses',
                },
                (payload) => {
                    const pr = payload.new
                    addToast({
                        id: Date.now(),
                        type: pr.is_slop ? 'warning' : 'success',
                        title: pr.is_slop
                            ? '🚫 AI Slop Flagged'
                            : '✅ PR Analyzed',
                        message: `PR #${pr.pr_number}: ${pr.title?.slice(0, 50)
                            }... — Score: ${pr.quality_score}/100`,
                        pr,
                    })
                }
            )
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [])

    const addToast = (toast) => {
        setToasts(prev => [...prev, toast])
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== toast.id))
        }, 5000)
    }

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }

    return (
        <div className="
      fixed bottom-6 right-6 z-50
      flex flex-col gap-3
      max-w-sm w-full
    ">
            <AnimatePresence>
                {toasts.map(toast => (
                    <motion.div
                        key={toast.id}
                        initial={{ opacity: 0, x: 100, scale: 0.9 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 100, scale: 0.9 }}
                        transition={{ type: 'spring', stiffness: 300 }}
                        className={`
              glass rounded-2xl p-4 border
              shadow-[0_8px_32px_rgba(0,0,0,0.5)]
              ${toast.type === 'warning'
                                ? 'border-red-500/30 bg-red-500/5'
                                : 'border-green-500/30 bg-green-500/5'
                            }
            `}
                    >
                        <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className={`
                w-8 h-8 rounded-lg flex items-center
                justify-center shrink-0
                ${toast.type === 'warning'
                                    ? 'bg-red-500/20'
                                    : 'bg-green-500/20'
                                }
              `}>
                                {toast.type === 'warning' ? (
                                    <AlertTriangle className="w-4 h-4 text-red-400" />
                                ) : (
                                    <CheckCircle className="w-4 h-4 text-green-400" />
                                )}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="font-semibold text-sm text-white mb-0.5">
                                    {toast.title}
                                </div>
                                <div className="text-xs text-gray-400 leading-relaxed">
                                    {toast.message}
                                </div>
                            </div>

                            {/* Close */}
                            <button
                                onClick={() => removeToast(toast.id)}
                                className="
                  text-gray-500 hover:text-gray-300
                  transition-colors shrink-0
                "
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Progress bar */}
                        <motion.div
                            initial={{ width: '100%' }}
                            animate={{ width: '0%' }}
                            transition={{ duration: 5, ease: 'linear' }}
                            className={`
                h-0.5 mt-3 rounded-full
                ${toast.type === 'warning'
                                    ? 'bg-red-400'
                                    : 'bg-green-400'
                                }
              `}
                        />
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    )
}