export default function DeleteConfirmModal({ letter, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-lg">
        <h2 className="text-lg font-semibold mb-2">Delete cover letter?</h2>
        <p className="text-sm text-gray-600 mb-4">
          Delete the letter for <strong>{letter.company_name}</strong> —{' '}
          <strong>{letter.job_title}</strong>? This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded border hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
