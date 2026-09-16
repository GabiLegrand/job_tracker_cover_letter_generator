import { Link } from 'react-router-dom'
import StatusBadge from './StatusBadge.jsx'
import { api } from '../api.js'

export default function LetterRow({ letter, onDelete }) {
  const handleDownload = () => {
    const url = api.pdfUrl(letter.id)
    const a = document.createElement('a')
    a.href = url
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <li className="border-b p-3 hover:bg-gray-50">
      <div className="flex items-start justify-between gap-2">
        <Link to={`/letters/${letter.id}`} className="flex-1 min-w-0 block">
          <div className="font-medium truncate">{letter.company_name}</div>
          <div className="text-sm text-gray-600 truncate">
            {letter.job_title}
          </div>
          <div className="mt-1">
            <StatusBadge status={letter.status} />
          </div>
        </Link>
        <div className="flex flex-col gap-1 shrink-0">
          <button
            onClick={handleDownload}
            disabled={letter.status !== 'ready'}
            className="text-xs px-2 py-1 rounded border hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            PDF
          </button>
          {letter.job_ad_url && (
            <a
              href={letter.job_ad_url}
              target="_blank"
              rel="noopener noreferrer"
              title={letter.job_ad_url}
              className="text-xs px-2 py-1 rounded border text-blue-600 hover:bg-blue-50 text-center"
            >
              Job ad ↗
            </a>
          )}
          <button
            onClick={onDelete}
            className="text-xs px-2 py-1 rounded border text-red-600 hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      </div>
    </li>
  )
}
