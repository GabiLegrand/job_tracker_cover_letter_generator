import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import DeleteConfirmModal from '../components/DeleteConfirmModal.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function EditLetter({ status, onChange }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [letter, setLetter] = useState(null)
  const [companyName, setCompanyName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [letterContent, setLetterContent] = useState('')
  const [jobAdUrl, setJobAdUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = async () => {
    try {
      const data = await api.get(id)
      setLetter(data)
      setCompanyName(data.company_name)
      setJobTitle(data.job_title)
      setJobDescription(data.job_description)
      setLetterContent(data.letter_content || '')
      setJobAdUrl(data.job_ad_url || '')
    } catch (err) {
      setError(err.message || 'Failed to load')
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Poll while generating (or while the global lock points at this letter)
  useEffect(() => {
    if (!letter) return
    const mine = status.cover_letter_id === letter.id
    if (letter.status !== 'generating' && !mine) return
    const t = setInterval(load, 2000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [letter?.status, status.cover_letter_id, id])

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await api.update(id, {
        company_name: companyName,
        job_title: jobTitle,
        job_description: jobDescription,
        letter_content: letterContent,
        job_ad_url: jobAdUrl.trim() || null,
      })
      setLetter(updated)
      onChange()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError('')
    try {
      const updated = await api.regenerate(id)
      setLetter(updated)
      setLetterContent(updated.letter_content || '')
      onChange()
    } catch (err) {
      if (err.status === 409) {
        setError('Another generation is in progress. Please wait.')
      } else {
        setError(err.message || 'Failed to regenerate')
      }
    } finally {
      setRegenerating(false)
    }
  }

  const handleDelete = async () => {
    await api.remove(id)
    setConfirmDelete(false)
    onChange()
    navigate('/new')
  }

  const handleDownload = () => {
    const url = api.pdfUrl(id)
    const a = document.createElement('a')
    a.href = url
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  if (!letter) {
    return <div className="p-8 text-gray-500">Loading…</div>
  }

  const busy = regenerating || letter.status === 'generating'

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Edit cover letter</h1>
        <StatusBadge status={letter.status} />
      </div>

      {letter.status === 'failed' && letter.error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
          Generation failed: {letter.error_message}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Company</label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            disabled={busy || saving}
            className="w-full border rounded px-3 py-2 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Job title</label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            disabled={busy || saving}
            className="w-full border rounded px-3 py-2 disabled:bg-gray-100"
          />
        </div>
      </div>

      <details>
        <summary className="cursor-pointer text-sm text-gray-600 select-none">
          Job description
        </summary>
        <textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          disabled={busy || saving}
          rows={8}
          className="w-full mt-2 border rounded px-3 py-2 font-mono text-sm disabled:bg-gray-100"
        />
      </details>

      <div>
        <label className="block text-sm font-medium mb-1">
          Job ad URL
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={jobAdUrl}
            onChange={(e) => setJobAdUrl(e.target.value)}
            disabled={busy || saving}
            placeholder="https://..."
            className="flex-1 border rounded px-3 py-2 disabled:bg-gray-100"
          />
          {jobAdUrl && (
            <a
              href={jobAdUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-2 rounded border hover:bg-gray-100 text-sm whitespace-nowrap"
            >
              Open ↗
            </a>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          Letter content
        </label>
        <textarea
          value={letterContent}
          onChange={(e) => setLetterContent(e.target.value)}
          disabled={busy}
          rows={20}
          className="w-full border rounded px-3 py-2 font-serif text-sm disabled:bg-gray-100"
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-center">
        <button
          onClick={handleSave}
          disabled={saving || busy}
          className="px-4 py-2 rounded bg-gray-700 text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={handleRegenerate}
          disabled={busy || status.locked}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {regenerating ? 'Regenerating…' : 'Regenerate'}
        </button>
        <button
          onClick={handleDownload}
          disabled={letter.status !== 'ready'}
          className="px-4 py-2 rounded border hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Download PDF
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setConfirmDelete(true)}
          className="px-4 py-2 rounded border text-red-600 hover:bg-red-50"
        >
          Delete
        </button>
      </div>

      <div className="text-xs text-gray-500">
        <Link to="/new" className="underline">
          ← New cover letter
        </Link>
      </div>

      {confirmDelete && (
        <DeleteConfirmModal
          letter={letter}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}
