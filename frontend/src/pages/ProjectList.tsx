import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Project } from '../api'

export function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const p = await api.createProject({ name, description: description || undefined })
      setShowForm(false)
      setName('')
      setDescription('')
      navigate(`/projects/${p.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create project')
    }
  }

  if (loading) {
    return (
      <div className="animate-fade-in" style={{ textAlign: 'center', padding: '4rem 0' }}>
        <span className="spinner" style={{ width: 32, height: 32 }} />
        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Loading projects...</p>
      </div>
    )
  }

  return (
    <div className="animate-slide-up">
      <div style={{ marginBottom: '2.5rem' }}>
        <h1 style={{ marginBottom: '0.4rem' }}>Your projects</h1>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>
          Choose a project to manage or create a new one to get started.
        </p>
      </div>

      {error && <div className="message error">{error}</div>}

      {showForm ? (
        <div className="card animate-scale-in" style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ marginBottom: '1.25rem' }}>New project</h2>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label className="label">Project name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="e.g. Mobile App Redesign"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="label">Description (optional)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of the project..."
                style={{ minHeight: 80 }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.6rem' }}>
              <button type="submit" className="primary">Create project</button>
              <button type="button" onClick={() => { setShowForm(false); setError(null) }}>Cancel</button>
            </div>
          </form>
        </div>
      ) : (
        <button
          className="primary"
          onClick={() => setShowForm(true)}
          style={{ marginBottom: '1.5rem', fontSize: '0.95rem', padding: '0.65rem 1.5rem' }}
        >
          + New project
        </button>
      )}

      {projects.length === 0 && !showForm ? (
        <div
          className="card animate-fade-in"
          style={{
            textAlign: 'center',
            padding: '3.5rem 2rem',
            borderStyle: 'dashed',
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.5 }}>
            &#128203;
          </div>
          <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
            No projects yet
          </h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', maxWidth: 360, margin: '0 auto 1.5rem' }}>
            Create your first project and start importing meeting transcripts to track action items.
          </p>
          <button className="primary" onClick={() => setShowForm(true)}>
            + Create your first project
          </button>
        </div>
      ) : (
        <div className="stagger" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div
                className="card"
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1.15rem 1.5rem',
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.1rem',
                    fontWeight: 700,
                    color: 'var(--accent)',
                    flexShrink: 0,
                  }}
                >
                  {p.name.charAt(0).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong style={{ display: 'block', fontSize: '1rem' }}>{p.name}</strong>
                  {p.description && (
                    <p style={{
                      margin: '0.2rem 0 0',
                      color: 'var(--text-muted)',
                      fontSize: '0.875rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {p.description}
                    </p>
                  )}
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>&rsaquo;</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
