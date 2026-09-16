import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import EditLetter from './pages/EditLetter.jsx'
import NewLetter from './pages/NewLetter.jsx'
import { api } from './api.js'

export default function App() {
  const [letters, setLetters] = useState([])
  const [status, setStatus] = useState({ locked: false, cover_letter_id: null })
  const [refreshTick, setRefreshTick] = useState(0)

  const refresh = () => setRefreshTick((t) => t + 1)

  useEffect(() => {
    api.list().then(setLetters).catch(() => {})
  }, [refreshTick])

  useEffect(() => {
    const tick = () => {
      api.getStatus().then(setStatus).catch(() => {})
      if (letters.some((l) => l.status === 'generating')) {
        api.list().then(setLetters).catch(() => {})
      }
    }
    tick()
    const interval = setInterval(tick, 2000)
    return () => clearInterval(interval)
  }, [letters])

  return (
    <div className="flex h-full">
      <Sidebar letters={letters} status={status} onChange={refresh} />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/new" replace />} />
          <Route
            path="/new"
            element={<NewLetter status={status} onCreated={refresh} />}
          />
          <Route
            path="/letters/:id"
            element={<EditLetter status={status} onChange={refresh} />}
          />
        </Routes>
      </main>
    </div>
  )
}
