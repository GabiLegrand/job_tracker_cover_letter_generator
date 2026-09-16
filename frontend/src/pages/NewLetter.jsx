import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function NewLetter({ status, onCreated }) {
  const navigate = useNavigate()
  const [companyName, setCompanyName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [jobAdUrl, setJobAdUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (status.locked) {
      setError('Another generation is in progress. Please wait.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const letter = await api.create({
        company_name: companyName,
        job_title: jobTitle || null,
        job_description: jobDescription,
        job_ad_url: jobAdUrl.trim() || null,
      })
      onCreated()
      navigate(`/letters/${letter.id}`)
    } catch (err) {
      if (err.status === 409) {
        setError('Another generation is in progress. Please wait.')
      } else {
        setError(err.message || 'Failed to generate.')
      }
      setSubmitting(false)
    }
  }

  const disabled = submitting || status.locked

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">New cover letter</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Company name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
            disabled={disabled}
            className="w-full border rounded px-3 py-2 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Job title{' '}
            <span className="text-gray-400">
              (optional — inferred if blank)
            </span>
          </label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            disabled={disabled}
            className="w-full border rounded px-3 py-2 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Job ad URL <span className="text-gray-400">(optional)</span>
          </label>
          <input
            type="url"
            value={jobAdUrl}
            onChange={(e) => setJobAdUrl(e.target.value)}
            disabled={disabled}
            placeholder="https://..."
            className="w-full border rounded px-3 py-2 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Job description <span className="text-red-500">*</span>
          </label>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            required
            rows={12}
            disabled={disabled}
            className="w-full border rounded px-3 py-2 font-mono text-sm disabled:bg-gray-100"
            placeholder="Paste the full job ad here…"
          />
        </div>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={disabled}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Generating… (may take up to ~30s)' : 'Generate cover letter'}
        </button>
        {status.locked && !submitting && (
          <p className="text-xs text-gray-500">
            Another letter is currently being generated.
          </p>
        )}
      </form>
    </div>
  )
}
