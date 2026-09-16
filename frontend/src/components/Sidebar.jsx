import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import DeleteConfirmModal from './DeleteConfirmModal.jsx'
import LetterRow from './LetterRow.jsx'
import { api } from '../api.js'

export default function Sidebar({ letters, status, onChange }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [pendingDelete, setPendingDelete] = useState(null)

  const handleDelete = async () => {
    if (!pendingDelete) return
    await api.remove(pendingDelete.id)
    if (location.pathname === `/letters/${pendingDelete.id}`) {
      navigate('/new')
    }
    setPendingDelete(null)
    onChange()
  }

  return (
    <aside className="w-80 border-r bg-white flex flex-col">
      <div className="p-4 border-b">
        <Link
          to="/new"
          aria-disabled={status.locked}
          onClick={(e) => {
            if (status.locked) e.preventDefault()
          }}
          title={status.locked ? 'generation in progress' : ''}
          className={`block w-full text-center py-2 rounded font-medium transition ${
            status.locked
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed pointer-events-none'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          + New cover letter
        </Link>
      </div>
      <div className="flex-1 overflow-auto">
        {letters.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">No letters yet.</p>
        ) : (
          <ul>
            {letters.map((l) => (
              <LetterRow
                key={l.id}
                letter={l}
                onDelete={() => setPendingDelete(l)}
              />
            ))}
          </ul>
        )}
      </div>
      {pendingDelete && (
        <DeleteConfirmModal
          letter={pendingDelete}
          onCancel={() => setPendingDelete(null)}
          onConfirm={handleDelete}
        />
      )}
    </aside>
  )
}
