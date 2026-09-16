const styles = {
  pending: 'bg-gray-100 text-gray-700',
  generating: 'bg-blue-100 text-blue-700 animate-pulse',
  ready: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export default function StatusBadge({ status }) {
  const cls = styles[status] || styles.pending
  return (
    <span
      className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${cls}`}
    >
      {status}
    </span>
  )
}
