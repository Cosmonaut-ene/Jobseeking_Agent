import type { Job } from '../api/client'

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  reviewed: 'bg-purple-100 text-purple-800',
  dismissed: 'bg-gray-100 text-gray-600',
  applied: 'bg-yellow-100 text-yellow-800',
  interview: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  offer: 'bg-emerald-100 text-emerald-800',
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'text-green-700' : pct >= 40 ? 'text-yellow-700' : 'text-red-600'
  return (
    <span className={`font-bold text-sm ${color}`}>{pct}%</span>
  )
}

interface Props {
  job: Job
  selected?: boolean
  onClick?: () => void
}

export default function JobCard({ job, selected, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
        selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-sm text-gray-900 truncate">{job.title || 'Untitled'}</p>
          <p className="text-xs text-gray-500 truncate">{job.company}{job.location ? ` · ${job.location}` : ''}</p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[job.status] ?? 'bg-gray-100 text-gray-600'}`}>
            {job.status}
          </span>
          <ScoreBadge score={job.match_score} />
        </div>
      </div>
      {job.skills_required.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {job.skills_required.slice(0, 4).map((s) => (
            <span key={s} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
              {s}
            </span>
          ))}
          {job.skills_required.length > 4 && (
            <span className="text-xs text-gray-400">+{job.skills_required.length - 4}</span>
          )}
        </div>
      )}
    </div>
  )
}
