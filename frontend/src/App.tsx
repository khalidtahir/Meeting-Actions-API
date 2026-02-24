import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { ProjectList } from './pages/ProjectList'
import { ProjectDashboard } from './pages/ProjectDashboard'

function App() {
  return (
    <BrowserRouter>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">
          <span className="navbar-logo">Wats Nxt?</span>
          <span className="navbar-tag">AI</span>
        </Link>
      </nav>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/projects/:projectId" element={<ProjectDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
