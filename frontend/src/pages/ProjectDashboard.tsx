import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ActionItem, ProjectDetail, ProposalResponse, ReconciliationProposal } from '../api'

const POLL_INTERVAL_MS = 15000

export function ProjectDashboard() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [actions, setActions] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadWeek, setUploadWeek] = useState(1)
  const [uploadTranscript, setUploadTranscript] = useState('')
  const [uploading, setUploading] = useState(false)
  const [proposalView, setProposalView] = useState<ProposalResponse | null>(null)
  const [rejectionFeedback, setRejectionFeedback] = useState('')
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showAddAction, setShowAddAction] = useState(false)
  const [newDesc, setNewDesc] = useState('')
  const [newType, setNewType] = useState('task')
  const [newOwner, setNewOwner] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDesc, setEditDesc] = useState('')
  const [editOwner, setEditOwner] = useState('')
  const [editStatus, setEditStatus] = useState<string>('')

  const load = useCallback(() => {
    if (!projectId) return
    setError(null)
    Promise.all([api.getProject(projectId), api.getProjectActions(projectId)])
      .then(([p, a]) => { setProject(p); setActions(a) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!projectId) return
    const id = setInterval(load, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [projectId, load])

  const fetchProposal = useCallback(
    async (previousProposal?: ReconciliationProposal | null, feedback?: string) => {
      if (!projectId || !uploadTranscript.trim()) return
      setUploading(true)
      setMessage(null)
      try {
        const payload: {
          meeting_title: string; transcript: string; week_number: number
          previous_proposal?: ReconciliationProposal; rejection_feedback?: string
        } = {
          meeting_title: uploadTitle || 'Uploaded meeting',
          transcript: uploadTranscript,
          week_number: uploadWeek,
        }
        if (previousProposal && feedback?.trim()) {
          payload.previous_proposal = previousProposal
          payload.rejection_feedback = feedback.trim()
        }
        const res = await api.getProposal(projectId, payload)
        setProposalView(res)
        setShowRejectInput(false)
        setRejectionFeedback('')
      } catch (e) {
        setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to generate proposal' })
      } finally {
        setUploading(false)
      }
    },
    [projectId, uploadTitle, uploadWeek, uploadTranscript]
  )

  const handleGenerateProposal = async (e: React.FormEvent) => {
    e.preventDefault()
    setProposalView(null)
    setShowRejectInput(false)
    setRejectionFeedback('')
    await fetchProposal()
  }

  const handleGetRevisedProposal = async () => {
    await fetchProposal(proposalView?.proposal ?? null, rejectionFeedback)
  }

  const handleApproveProposal = async () => {
    if (!projectId || !proposalView || !uploadTranscript.trim()) return
    setApplying(true)
    setMessage(null)
    try {
      await api.applyProposal(projectId, {
        meeting_title: uploadTitle || 'Uploaded meeting',
        transcript: uploadTranscript,
        week_number: uploadWeek,
        proposal: proposalView.proposal,
      })
      setMessage({ type: 'success', text: 'Proposal applied — action items updated.' })
      setProposalView(null)
      setUploadTranscript('')
      setRejectionFeedback('')
      setShowRejectInput(false)
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to apply proposal' })
    } finally {
      setApplying(false)
    }
  }

  const handleCancelProposal = () => {
    setProposalView(null)
    setShowRejectInput(false)
    setRejectionFeedback('')
  }

  const handleAddAction = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projectId || !newDesc.trim()) return
    setMessage(null)
    try {
      await api.createProjectAction(projectId, {
        description: newDesc,
        type: newType,
        owner: newOwner.trim() || undefined,
      })
      setMessage({ type: 'success', text: 'Action added.' })
      setShowAddAction(false)
      setNewDesc('')
      setNewOwner('')
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to add action' })
    }
  }

  const startEdit = (a: ActionItem) => {
    setEditingId(a.id)
    setEditDesc(a.description)
    setEditOwner(a.owner || '')
    setEditStatus(a.status)
  }

  const handleUpdateAction = async (meetingId: string, actionId: string) => {
    setMessage(null)
    try {
      await api.updateAction(meetingId, actionId, {
        description: editDesc,
        owner: editOwner || undefined,
        status: editStatus,
      })
      setMessage({ type: 'success', text: 'Action updated.' })
      setEditingId(null)
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Update failed' })
    }
  }

  const handleDeleteAction = async (meetingId: string, actionId: string) => {
    if (!confirm('Delete this action?')) return
    setMessage(null)
    try {
      await api.deleteAction(meetingId, actionId)
      setMessage({ type: 'success', text: 'Action deleted.' })
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Delete failed' })
    }
  }

  const byOwner = actions.reduce<Record<string, ActionItem[]>>((acc, a) => {
    const key = a.owner?.trim() || 'Unassigned'
    if (!acc[key]) acc[key] = []
    acc[key].push(a)
    return acc
  }, {})

  const openCount = actions.filter((a) => a.status === 'OPEN').length
  const completedCount = actions.filter((a) => a.status === 'COMPLETED').length

  if (loading && !project) {
    return (
      <div className="animate-fade-in" style={{ textAlign: 'center', padding: '4rem 0' }}>
        <span className="spinner" style={{ width: 32, height: 32 }} />
        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Loading project...</p>
      </div>
    )
  }

  if (error && !project) return <div className="message error">{error}</div>
  if (!projectId || !project) return null

  return (
    <div className="animate-slide-up">
      {/* Back link */}
      <Link
        to="/"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.3rem',
          fontSize: '0.875rem',
          color: 'var(--text-muted)',
          marginBottom: '1.25rem',
          transition: 'color var(--transition-fast)',
        }}
      >
        &larr; Back to projects
      </Link>

      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginBottom: '0.3rem' }}>{project.name}</h1>
        {project.description && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>{project.description}</p>
        )}
      </div>

      {/* Stats bar */}
      <div
        style={{
          display: 'flex',
          gap: '0.75rem',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
        }}
      >
        <StatPill label="Total" value={actions.length} color="var(--accent)" bg="var(--accent-subtle)" />
        <StatPill label="Open" value={openCount} color="var(--accent)" bg="var(--accent-subtle)" />
        <StatPill label="Done" value={completedCount} color="var(--green)" bg="var(--green-bg)" />
        <StatPill label="Meetings" value={project.meeting_count} color="var(--amber)" bg="var(--amber-bg)" />
      </div>

      {message && <div className={`message ${message.type}`}>{message.text}</div>}

      {/* Upload transcript */}
      <section className="card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ marginBottom: '0.35rem' }}>Upload transcript</h2>
        <p className="section-subtitle">
          Paste meeting minutes and generate an AI proposal. Review changes before anything is saved.
        </p>
        <form onSubmit={handleGenerateProposal}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', marginBottom: '1.1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="label">Meeting title</label>
              <input value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} placeholder="e.g. Week 3 standup" />
            </div>
            <div className="form-group" style={{ marginBottom: 0, width: 100 }}>
              <label className="label">Week #</label>
              <input
                type="number" min={1} value={uploadWeek}
                onChange={(e) => setUploadWeek(parseInt(e.target.value, 10) || 1)}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="label">Transcript</label>
            <textarea
              value={uploadTranscript}
              onChange={(e) => setUploadTranscript(e.target.value)}
              placeholder="Paste meeting transcript here..."
              required
            />
          </div>
          <button type="submit" className="primary" disabled={uploading}>
            {uploading && <span className="spinner" />}
            {uploading ? 'Generating proposal...' : 'Generate proposal'}
          </button>
        </form>
      </section>

      {/* Proposal review */}
      {proposalView && (
        <section className="card animate-scale-in" style={{ marginBottom: '1rem', border: '1px solid rgba(129,140,248,0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
            <h2 style={{ margin: 0 }}>Review proposal</h2>
            <span className="navbar-tag">AI</span>
          </div>
          <p className="section-subtitle">
            Compare current state with proposed changes. Approve to commit, or reject with feedback.
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '1.5rem',
            marginBottom: '1.25rem',
          }}>
            {/* Current state */}
            <div style={{
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem 1.15rem',
              border: '1px solid var(--border-subtle)',
            }}>
              <h3 style={{ marginBottom: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Current open items
              </h3>
              {proposalView.current_actions.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No open actions.</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: '1.15rem', listStyle: 'none' }}>
                  {proposalView.current_actions.map((a) => (
                    <li key={a.id} style={{ marginBottom: '0.4rem', paddingLeft: '0.75rem', borderLeft: '2px solid var(--accent)', fontSize: '0.9rem' }}>
                      {a.description}
                      {a.owner && <span style={{ color: 'var(--text-muted)', marginLeft: '0.4rem' }}>({a.owner})</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Proposed changes */}
            <div style={{
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem 1.15rem',
              border: '1px solid var(--border-subtle)',
            }}>
              <h3 style={{ marginBottom: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Proposed changes
              </h3>

              {proposalView.proposal.completed.length > 0 && (
                <ProposalGroup label="Completed" color="var(--green)" items={proposalView.proposal.completed} />
              )}
              {proposalView.proposal.carryover.length > 0 && (
                <ProposalGroup label="Carryover" color="var(--amber)" items={proposalView.proposal.carryover} />
              )}
              {proposalView.proposal.new_actions.length > 0 && (
                <ProposalGroup label="New" color="var(--accent)" items={proposalView.proposal.new_actions.map((n, i) => ({ ...n, id: `new-${i}` }))} />
              )}
              {proposalView.proposal.risk_flags.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--red)', marginBottom: '0.35rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Risks / Blockers
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '1.15rem', color: 'var(--red)', fontSize: '0.875rem' }}>
                    {proposalView.proposal.risk_flags.map((r, i) => <li key={i} style={{ marginBottom: '0.2rem' }}>{r}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Summary */}
          <div style={{
            background: 'var(--accent-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.75rem 1rem',
            marginBottom: '1.25rem',
            fontSize: '0.9rem',
            color: 'var(--text-primary)',
            borderLeft: '3px solid var(--accent)',
          }}>
            <strong style={{ marginRight: '0.4rem' }}>Summary:</strong>
            {proposalView.proposal.summary}
          </div>

          {showRejectInput ? (
            <div className="animate-fade-in">
              <div className="form-group">
                <label className="label">What should the AI change?</label>
                <textarea
                  value={rejectionFeedback}
                  onChange={(e) => setRejectionFeedback(e.target.value)}
                  placeholder="e.g. Don't mark 'API fix' as completed — we're still testing."
                  rows={3}
                  style={{ minHeight: 80 }}
                />
              </div>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <button className="primary" disabled={uploading} onClick={handleGetRevisedProposal}>
                  {uploading && <span className="spinner" />}
                  Get revised proposal
                </button>
                <button onClick={() => { setShowRejectInput(false); setRejectionFeedback('') }}>Cancel</button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <button className="primary" disabled={applying} onClick={handleApproveProposal}>
                {applying && <span className="spinner" />}
                {applying ? 'Applying...' : 'Approve & save'}
              </button>
              <button onClick={() => setShowRejectInput(true)}>Reject &amp; request changes</button>
              <button onClick={handleCancelProposal}>Cancel</button>
            </div>
          )}
        </section>
      )}

      {/* Action items */}
      <section className="card">
        <div className="section-header">
          <h2 style={{ margin: 0 }}>Action items</h2>
          <button
            className={showAddAction ? '' : 'primary'}
            onClick={() => setShowAddAction(!showAddAction)}
          >
            {showAddAction ? 'Cancel' : '+ Add action'}
          </button>
        </div>

        {showAddAction && (
          <form onSubmit={handleAddAction} className="animate-scale-in" style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="form-group">
              <label className="label">Description</label>
              <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="What needs to be done?" required autoFocus />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="label">Type</label>
                <select value={newType} onChange={(e) => setNewType(e.target.value)}>
                  <option value="task">Task</option>
                  <option value="decision">Decision</option>
                  <option value="follow_up">Follow-up</option>
                  <option value="question">Question</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label className="label">Owner (optional)</label>
                <input value={newOwner} onChange={(e) => setNewOwner(e.target.value)} placeholder="Name" />
              </div>
            </div>
            <button type="submit" className="primary">Add action</button>
          </form>
        )}

        {actions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem', opacity: 0.4 }}>&#9776;</div>
            <p style={{ color: 'var(--text-muted)' }}>
              No action items yet. Upload a transcript or add one manually.
            </p>
          </div>
        ) : (
          <div className="stagger">
            {Object.entries(byOwner).map(([owner, items]) => (
              <div key={owner} style={{ marginBottom: '1.75rem' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.6rem',
                }}>
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: owner === 'Unassigned' ? 'var(--bg-glass)' : 'var(--accent-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: owner === 'Unassigned' ? 'var(--text-muted)' : 'var(--accent)',
                  }}>
                    {owner === 'Unassigned' ? '?' : owner.charAt(0).toUpperCase()}
                  </div>
                  <h3 style={{ fontSize: '0.95rem', margin: 0 }}>{owner}</h3>
                  <span style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    background: 'var(--bg-glass)',
                    padding: '0.1rem 0.45rem',
                    borderRadius: '999px',
                  }}>
                    {items.length}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {items.map((a) => (
                    <div
                      key={a.id}
                      style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-glass)',
                        borderRadius: 'var(--radius-md)',
                        padding: '0.85rem 1.1rem',
                        transition: 'all var(--transition-fast)',
                      }}
                    >
                      {editingId === a.id ? (
                        <div className="animate-fade-in">
                          <div className="form-group">
                            <label className="label">Description</label>
                            <input value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div className="form-group">
                              <label className="label">Owner</label>
                              <input value={editOwner} onChange={(e) => setEditOwner(e.target.value)} />
                            </div>
                            <div className="form-group">
                              <label className="label">Status</label>
                              <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                                <option value="OPEN">Open</option>
                                <option value="COMPLETED">Completed</option>
                                <option value="CARRYOVER">Carryover</option>
                              </select>
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button className="primary" onClick={() => handleUpdateAction(a.meeting_id, a.id)}>Save</button>
                            <button onClick={() => setEditingId(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                            <span className={`badge ${a.status.toLowerCase()}`}>{a.status}</span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                              {a.type.replace('_', ' ')}
                            </span>
                          </div>
                          <p style={{ margin: '0.3rem 0 0', color: 'var(--text-primary)', fontSize: '0.925rem' }}>{a.description}</p>
                          {a.week_number != null && (
                            <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Week {a.week_number}</p>
                          )}
                          <div style={{ marginTop: '0.6rem', display: 'flex', gap: '0.45rem' }}>
                            <button onClick={() => startEdit(a)} style={{ fontSize: '0.8rem', padding: '0.3rem 0.7rem' }}>Edit</button>
                            <button className="danger" onClick={() => handleDeleteAction(a.meeting_id, a.id)} style={{ fontSize: '0.8rem', padding: '0.3rem 0.7rem' }}>Delete</button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

/* Small stat pill component */
function StatPill({ label, value, color, bg }: { label: string; value: number; color: string; bg: string }) {
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.45rem',
      padding: '0.35rem 0.85rem',
      borderRadius: '999px',
      background: bg,
      border: `1px solid ${color}22`,
      fontSize: '0.85rem',
    }}>
      <span style={{ fontWeight: 700, color }}>{value}</span>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
    </div>
  )
}

/* Proposal group helper */
function ProposalGroup({ label, color, items }: { label: string; color: string; items: { id: string; description: string; owner?: string }[] }) {
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{
        fontSize: '0.8rem',
        fontWeight: 600,
        color,
        marginBottom: '0.3rem',
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}>
        {label}
      </div>
      <ul style={{ margin: 0, paddingLeft: '1.15rem', listStyle: 'none' }}>
        {items.map((item) => (
          <li key={item.id} style={{
            marginBottom: '0.3rem',
            paddingLeft: '0.75rem',
            borderLeft: `2px solid ${color}`,
            fontSize: '0.875rem',
            color: 'var(--text-primary)',
          }}>
            {item.description}
            {item.owner && <span style={{ color: 'var(--text-muted)', marginLeft: '0.4rem' }}>({item.owner})</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
