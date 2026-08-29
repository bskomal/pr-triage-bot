import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_KEY

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

// ─── PR Analyses ──────────────────────────
export const getPRAnalyses = async ({
    repo = null,
    limit = 20,
    offset = 0,
    tier = null,
    isSlop = null,
} = {}) => {
    let query = supabase
        .from('pr_analyses')
        .select('*')
        .order('analyzed_at', { ascending: false })
        .range(offset, offset + limit - 1)

    if (repo) query = query.eq('repo', repo)
    if (tier) query = query.eq('quality_tier', tier)
    if (isSlop !== null) query = query.eq('is_slop', isSlop)

    const { data, error } = await query
    if (error) throw error
    return data || []
}

export const getPRDetail = async (repo, prNumber) => {
    const { data, error } = await supabase
        .from('pr_analyses')
        .select('*')
        .eq('repo', repo)
        .eq('pr_number', prNumber)
        .order('analyzed_at', { ascending: false })
        .limit(1)
        .single()

    if (error) throw error
    return data
}

// ─── Stats ────────────────────────────────
export const getStats = async () => {
    const { data, error } = await supabase
        .from('pr_analyses')
        .select('quality_score, is_slop, author, repo, quality_tier')

    if (error) throw error

    const total = data.length
    const avgQuality = total > 0
        ? Math.round(
            data.reduce((sum, r) => sum + (r.quality_score || 0), 0)
            / total
        )
        : 0
    const totalSlop = data.filter(r => r.is_slop).length
    const repos = new Set(data.map(r => r.repo)).size
    const authors = new Set(data.map(r => r.author)).size
    const excellent = data.filter(
        r => r.quality_tier === 'excellent'
    ).length

    return {
        total_prs: total,
        avg_quality: avgQuality,
        total_slop: totalSlop,
        total_repos: repos,
        total_authors: authors,
        excellent_prs: excellent,
        slop_rate: total > 0
            ? Math.round((totalSlop / total) * 100)
            : 0,
    }
}

// ─── Quality Trend ────────────────────────
export const getQualityTrend = async (
    repo = null,
    days = 30
) => {
    const since = new Date()
    since.setDate(since.getDate() - days)

    let query = supabase
        .from('pr_analyses')
        .select('quality_score, analyzed_at, is_slop')
        .gte('analyzed_at', since.toISOString())
        .order('analyzed_at', { ascending: true })

    if (repo) query = query.eq('repo', repo)

    const { data, error } = await query
    if (error) throw error

    // Group by date
    const grouped = {}
    data.forEach(row => {
        const date = row.analyzed_at.split('T')[0]
        if (!grouped[date]) {
            grouped[date] = { scores: [], slop: 0, total: 0 }
        }
        grouped[date].scores.push(row.quality_score || 0)
        grouped[date].total++
        if (row.is_slop) grouped[date].slop++
    })

    return Object.entries(grouped).map(([date, vals]) => ({
        date,
        avg_score: Math.round(
            vals.scores.reduce((a, b) => a + b, 0)
            / vals.scores.length
        ),
        pr_count: vals.total,
        slop_count: vals.slop,
    }))
}

// ─── Digests ──────────────────────────────
export const getDigests = async (
    repo = null,
    limit = 10
) => {
    let query = supabase
        .from('digests')
        .select('*')
        .order('generated_at', { ascending: false })
        .limit(limit)

    if (repo) query = query.eq('repo', repo)

    const { data, error } = await query
    if (error) throw error
    return data || []
}

// ─── Repo Summary ─────────────────────────
export const getRepoSummary = async (repo) => {
    const { data, error } = await supabase
        .from('pr_analyses')
        .select('*')
        .eq('repo', repo)

    if (error) throw error
    if (!data || data.length === 0) return null

    const total = data.length
    const avgQuality = Math.round(
        data.reduce((s, r) => s + (r.quality_score || 0), 0)
        / total
    )
    const slopCount = data.filter(r => r.is_slop).length

    const typeCounts = {}
    data.forEach(r => {
        typeCounts[r.pr_type] = (typeCounts[r.pr_type] || 0) + 1
    })
    const mostCommonType = Object.entries(typeCounts)
        .sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown'

    return {
        repo,
        total_prs_analyzed: total,
        avg_quality_score: avgQuality,
        slop_rate: Math.round((slopCount / total) * 100),
        most_common_type: mostCommonType,
        last_analyzed: data[0]?.analyzed_at,
    }
}

// ─── Real-time subscription ───────────────
export const subscribeToPRs = (callback) => {
    return supabase
        .channel('pr_analyses')
        .on(
            'postgres_changes',
            { event: 'INSERT', schema: 'public', table: 'pr_analyses' },
            callback
        )
        .subscribe()
}

// ─── Contributor Detail ───────────────────
export const getContributorDetail = async (username) => {
    const { data, error } = await supabase
        .from('pr_analyses')
        .select('*')
        .eq('author', username)
        .order('analyzed_at', { ascending: false })

    if (error) throw error
    if (!data || data.length === 0) return null

    const prs = data
    const scores = prs.map(p => p.quality_score || 0)
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length
    const slopCount = prs.filter(p => p.is_slop).length
    const slopRate = slopCount / prs.length
    const excellent = prs.filter(p => p.quality_tier === 'excellent').length

    let trend = 'stable'
    if (scores.length >= 6) {
        const recent = scores.slice(-3).reduce((a, b) => a + b, 0) / 3
        const older = scores.slice(0, 3).reduce((a, b) => a + b, 0) / 3
        if (recent > older + 10) trend = 'improving'
        else if (recent < older - 10) trend = 'declining'
    }

    let rank = 'newcomer'
    if (slopRate >= 0.5) rank = 'watch'
    else if (avgScore >= 75 && prs.length >= 5 && slopRate === 0) rank = 'champion'
    else if (prs.length >= 3 && avgScore >= 50) rank = 'regular'

    let trust = avgScore
    if (prs.length >= 10) trust += 5
    if (slopRate === 0) trust += 10
    if (trend === 'improving') trust += 5
    trust -= slopRate * 30
    if (prs.length < 3) trust -= 10
    trust = Math.max(0, Math.min(100, trust))

    return {
        username,
        total_prs: prs.length,
        avg_score: Math.round(avgScore),
        excellent_prs: excellent,
        slop_count: slopCount,
        slop_rate: Math.round(slopRate * 100),
        trend,
        rank,
        trust_score: Math.round(trust),
        prs,
    }
}