import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api.js';
import AnswerMarkdown from './AnswerMarkdown.jsx';

const SESSION_REPOSITORY_KEY = 'repolens.selectedRepositoryId';

function Icon({ name, size = 18, strokeWidth = 1.8 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };
  const paths = {
    ask: <><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 12h8M8 9h5"/></>,
    repos: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 5.5v15M8 7h8M8 11h6"/></>,
    status: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/><path d="M16 7h3v3"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    external: <><path d="M14 3h7v7M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></>,
    chevron: <><path d="m6 9 6 6 6-6"/></>,
    code: <><path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    alert: <><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 2.4 17.5A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 1.8-2.5L13.7 3.9a2 2 0 0 0-3.4 0Z"/></>,
    send: <><path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/></>,
    link: <><path d="M10 13a5 5 0 0 0 7.1 0l3-3A5 5 0 0 0 13 2.9l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.1 0l-3 3A5 5 0 0 0 11 21.1l1.7-1.7"/></>,
    sparkle: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z"/></>,
  };
  return <svg {...common}>{paths[name] || paths.code}</svg>;
}

function StatusPill({ status }) {
  const value = (status || 'unknown').toLowerCase();
  const label = value === 'indexed' ? 'Indexed' : value === 'partial' ? 'Partially indexed' : value === 'indexing' ? 'Indexing' : value === 'failed' ? 'Failed' : value === 'pending' ? 'Pending' : value;
  return <span className={`status-pill status-${value}`}><i />{label}</span>;
}

function Sidebar({ activeView, setActiveView, repository, repositories, selectRepository, apiOnline }) {
  const navItems = [
    { id: 'ask', label: 'Ask code', icon: 'ask' },
    { id: 'repositories', label: 'Repositories', icon: 'repos' },
    { id: 'status', label: 'Indexing & status', icon: 'status' },
  ];
  return (
    <aside className="sidebar">
      <a className="brand" href="#home" onClick={(event) => { event.preventDefault(); setActiveView('ask'); }}>
        <span className="brand-mark"><Icon name="code" size={21} /></span>
        <span className="brand-copy"><strong>RepoLens</strong><small>AI code companion</small></span>
      </a>

      <div className="side-label">WORKSPACE</div>
      <nav className="main-nav" aria-label="Main navigation">
        {navItems.map((item) => (
          <button key={item.id} className={`nav-item ${activeView === item.id ? 'active' : ''}`} onClick={() => setActiveView(item.id)}>
            <Icon name={item.icon} size={18} /><span>{item.label}</span>
            {item.id === 'repositories' && repositories.length > 0 && <span className="nav-count">{repositories.length}</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-repository">
        <div className="side-label">CURRENT REPOSITORY</div>
        {repository ? (
          <button className="current-repo" onClick={() => setActiveView('ask')}>
            <span className="repo-initial">{repository.name?.slice(0, 1).toUpperCase() || 'R'}</span>
            <span className="current-repo-copy"><strong>{repository.name}</strong><small>{repository.status || 'unknown'}</small></span>
            <span className="repo-live-dot" />
          </button>
        ) : (
          <button className="empty-repo-link" onClick={() => setActiveView('repositories')}>
            <span className="empty-repo-icon"><Icon name="plus" size={15} /></span>
            <span>No repository yet</span>
          </button>
        )}
      </div>

      <div className="sidebar-footer">
        <div className={`connection-indicator ${apiOnline ? 'is-online' : ''}`}><span /><div><strong>{apiOnline ? 'API connected' : 'API unavailable'}</strong><small>{apiOnline ? 'Ready for questions' : 'Check backend connection'}</small></div></div>
        <div className="sidebar-version"><span>REPOLENS AI</span><span>LOCAL WORKSPACE</span></div>
      </div>
    </aside>
  );
}

function Topbar({ repository, apiOnline, setActiveView }) {
  return (
    <header className="topbar">
      <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{repository?.name || 'Getting started'}</strong></div>
      <div className="topbar-right">
        <span className={`api-status ${apiOnline ? 'online' : ''}`}><i />{apiOnline ? 'Connected' : 'Offline'}</span>
        <button className="topbar-help" onClick={() => setActiveView('status')} aria-label="View system status"><Icon name="status" size={17} /></button>
      </div>
    </header>
  );
}

function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return <div className="error-banner" role="alert"><Icon name="alert" size={18} /><span>{message}</span><button onClick={onDismiss} aria-label="Dismiss error">×</button></div>;
}

function EmptyWorkspace({ sourceUrl, setSourceUrl, onIngest, busy, error, dismissError }) {
  return (
    <div className="welcome-layout">
      <section className="welcome-main">
        <ErrorBanner message={error} onDismiss={dismissError} />
        <div className="welcome-eyebrow"><span className="eyebrow-line" />YOUR CODEBASE, UNDERSTOOD</div>
        <h1>A little more clarity<br />for your <em>codebase.</em></h1>
        <p className="welcome-description">Connect a GitHub repository and ask the questions that help you move forward. Answers come with source citations, so you can follow the thread back to the code.</p>

        <form className="connect-form" onSubmit={onIngest}>
          <label htmlFor="repository-url">GitHub repository URL</label>
          <div className="url-input-wrap"><Icon name="link" size={18} /><input id="repository-url" type="url" inputMode="url" autoComplete="url" placeholder="https://github.com/owner/repository" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} required disabled={busy} /><button type="submit" className="primary-button" disabled={busy || !sourceUrl.trim()}>{busy ? <><span className="spinner" />Analyzing</> : <>Analyze repository <Icon name="arrow" size={16} /></>}</button></div>
          <span className="form-hint">Public GitHub repositories are analyzed and indexed for code-aware answers.</span>
        </form>

        <div className="welcome-note"><span className="note-icon"><Icon name="sparkle" size={17} /></span><span><strong>Answers grounded in source.</strong> Explore functions, trace execution, and get pointed back to the files that matter.</span></div>
      </section>
      <aside className="welcome-aside">
        <div className="aside-topline"><span>HOW IT WORKS</span><Icon name="code" size={18} /></div>
        <div className="process-list">
          <div className="process-step"><span className="step-number">01</span><div><strong>Connect a repository</strong><p>RepoLens reads supported source files from GitHub.</p></div></div>
          <div className="process-connector" />
          <div className="process-step"><span className="step-number">02</span><div><strong>Build a code index</strong><p>Code is parsed into searchable, structure-aware chunks.</p></div></div>
          <div className="process-connector" />
          <div className="process-step"><span className="step-number">03</span><div><strong>Ask with confidence</strong><p>Answers include citations to source files and lines.</p></div></div>
        </div>
        <div className="aside-bottom"><span className="aside-orb" /><span>Made for the moments<br />when you’re new to a codebase.</span></div>
      </aside>
    </div>
  );
}

function Citation({ source, index }) {
  const snippet = typeof source.snippet === 'string' ? source.snippet : '';
  const range = source.start_line != null
    ? `L${source.start_line}${source.end_line != null && source.end_line !== source.start_line ? `–${source.end_line}` : ''}`
    : null;
  return (
    <details className="citation-card" open={index === 0 && Boolean(snippet.trim())}>
      <summary><span className="citation-index">{String(index + 1).padStart(2, '0')}</span><span className="citation-file"><Icon name="code" size={15} /><code>{source.file_path}</code></span>{source.symbol_name && <span className="citation-symbol">{source.symbol_name}</span>}{range && <span className="citation-range">{range}</span>}<Icon name="chevron" size={16} /></summary>
      <div className="citation-content">{snippet.trim() ? <pre><code>{snippet}</code></pre> : <p className="muted-copy">No source snippet was returned for this citation.</p>}</div>
    </details>
  );
}

function ChatWorkspace({ repository, messages, onAsk, busy, error, dismissError }) {
  const [question, setQuestion] = useState('');
  const inputRef = useRef(null);
  const canAsk = ['indexed', 'partial'].includes((repository?.status || '').toLowerCase());
  const submit = (event) => {
    event?.preventDefault();
    if (!question.trim() || busy || !canAsk) return;
    const current = question.trim();
    setQuestion('');
    onAsk(current);
  };

  useEffect(() => { inputRef.current?.focus(); }, [repository?.id]);

  return (
    <div className="chat-page">
      <div className="page-heading-row"><div><div className="page-kicker">REPOSITORY Q&amp;A</div><h1>Ask your codebase.</h1><p>Explore the implementation with answers grounded in source.</p></div><div className="repo-heading-chip"><span className="repo-initial small">{repository.name?.slice(0, 1).toUpperCase() || 'R'}</span><div><strong>{repository.name}</strong><small>{repository.source_url?.replace(/^https?:\/\//, '') || 'GitHub repository'}</small></div><StatusPill status={repository.status} /></div></div>
      <ErrorBanner message={error} onDismiss={dismissError} />

      <div className={`conversation ${messages.length ? 'has-messages' : ''}`}>
        {messages.length === 0 ? (
          <div className="chat-empty"><span className="chat-empty-icon"><Icon name="ask" size={22} /></span><div className="page-kicker">A GOOD PLACE TO START</div><h2>What would you like to understand?</h2><p>Ask about a function, a flow, or how a part of the system fits together.</p><div className="suggestion-row"><button onClick={() => setQuestion('Where does the application start?')}>Where does the application start?</button><button onClick={() => setQuestion('How is a request handled?')}>How is a request handled?</button></div></div>
        ) : messages.map((message) => (
          <article key={message.id} className="message-group">
            <div className="question-row"><span className="question-avatar">Y</span><div className="question-content"><span className="message-label">YOUR QUESTION</span><p>{message.question}</p></div></div>
            <div className="answer-row"><span className="answer-avatar"><Icon name="code" size={17} /></span><div className="answer-content"><div className="answer-label-row"><span className="message-label">REPOLENS ANSWER</span><span className="grounded-mark"><i />SOURCE-GROUNDED</span></div>{message.pending ? <div className="answer-pending"><span className="thinking-dots"><i /><i /><i /></span><span>Reading the relevant code…</span></div> : <><AnswerMarkdown text={message.answer} />{message.sources?.length ? <div className="citations"><div className="citations-heading"><span>Sources</span><span>{message.sources.length} {message.sources.length === 1 ? 'citation' : 'citations'}</span></div>{message.sources.map((source, index) => <Citation key={`${source.file_path}-${source.start_line}-${index}`} source={source} index={index} />)}</div> : <div className="no-citations"><Icon name="alert" size={15} />No source citations were returned for this answer.</div>}</>}</div></div>
          </article>
        ))}
      </div>

      {!canAsk && <div className="index-required"><Icon name="alert" size={17} /><span>This repository is not ready for questions. Its current status is <strong>{repository.status}</strong>.</span></div>}
      <form className="question-composer" onSubmit={submit}>
        <textarea ref={inputRef} aria-label="Ask a question about this repository" placeholder={canAsk ? 'Ask a question about this repository…' : 'Index this repository to start asking questions'} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(event); } }} rows={2} disabled={!canAsk || busy} maxLength={4000} />
        <div className="composer-footer"><span>Answers cite files and line ranges <span className="composer-dot">·</span> Enter to send</span><button type="submit" className="send-button" disabled={!question.trim() || busy || !canAsk} aria-label="Send question">{busy ? <span className="spinner light" /> : <Icon name="send" size={17} />}</button></div>
      </form>
      <div className="privacy-note">RepoLens answers from the indexed repository context. Verify important details in the cited source.</div>
    </div>
  );
}

function RepositoryList({ repositories, selectedRepository, selectRepository, onConnect, loading }) {
  return (
    <div className="standard-page">
      <div className="page-kicker">YOUR WORKSPACE</div><div className="standard-heading"><div><h1>Repositories</h1><p>Choose a codebase to explore, or connect another public GitHub repository.</p></div><button className="primary-button" onClick={onConnect}><Icon name="plus" size={16} /> Connect repository</button></div>
      {loading ? <div className="loading-card"><span className="spinner" />Loading repositories…</div> : repositories.length === 0 ? <div className="empty-list"><span className="empty-list-mark"><Icon name="repos" size={22} /></span><h2>No repositories connected</h2><p>Add a public GitHub repository to begin exploring its code.</p><button className="secondary-button" onClick={onConnect}>Connect your first repository <Icon name="arrow" size={15} /></button></div> : <div className="repository-list">{repositories.map((repo) => <button className={`repository-row ${selectedRepository?.id === repo.id ? 'selected' : ''}`} key={repo.id} onClick={() => selectRepository(repo)}><span className="repo-initial">{repo.name?.slice(0, 1).toUpperCase() || 'R'}</span><span className="repository-main"><strong>{repo.name}</strong><small>{repo.source_url || 'No source URL recorded'}</small></span><StatusPill status={repo.status} /><span className="repo-date">Added {repo.created_at ? new Date(repo.created_at).toLocaleDateString() : 'date unavailable'}</span><Icon name="arrow" size={17} /></button>)}</div>}
      <div className="repo-footnote"><Icon name="link" size={15} /><span>Repository ingestion and indexing are handled by your connected RepoLens backend.</span></div>
    </div>
  );
}

function KeyValue({ label, value }) {
  if (value == null || value === '') return null;
  return <div className="detail-row"><span>{label}</span><strong>{String(value)}</strong></div>;
}

function StatusPage({ repository, lastOperation, onIndex, busy, error, dismissError, onBrowse, apiOnline }) {
  const canIndex = ['pending', 'failed'].includes((repository?.status || '').toLowerCase());
  const summary = lastOperation?.indexing || lastOperation?.result?.indexing;
  return (
    <div className="standard-page">
      <div className="page-kicker">SYSTEM OVERVIEW</div><div className="standard-heading"><div><h1>Indexing &amp; status</h1><p>See what RepoLens knows about the selected repository.</p></div></div>
      <ErrorBanner message={error} onDismiss={dismissError} />
      {repository ? <div className="status-layout"><section className="status-card main-status-card"><div className="status-card-head"><div className="status-repo-title"><span className="repo-initial">{repository.name?.slice(0, 1).toUpperCase() || 'R'}</span><div><span className="page-kicker">SELECTED REPOSITORY</span><h2>{repository.name}</h2></div></div><StatusPill status={repository.status} /></div><a className="repository-url" href={repository.source_url || undefined} target="_blank" rel="noreferrer"><Icon name="external" size={15} />{repository.source_url || 'No source URL recorded'}</a><div className="status-divider" /><div className="status-details"><KeyValue label="Repository ID" value={repository.id} /><KeyValue label="Source type" value={repository.source_type} /><KeyValue label="Added to RepoLens" value={repository.created_at ? new Date(repository.created_at).toLocaleString() : null} /><KeyValue label="Last updated" value={repository.updated_at ? new Date(repository.updated_at).toLocaleString() : null} /></div>{canIndex && <button className="primary-button status-action" onClick={onIndex} disabled={busy}>{busy ? <><span className="spinner" />Indexing repository…</> : <>Retry indexing <Icon name="arrow" size={16} /></>}</button>}{['indexed', 'partial'].includes((repository.status || '').toLowerCase()) && <div className="status-ready"><span><Icon name="check" size={16} /></span><div><strong>Ready to explore</strong><small>Ask a question to retrieve relevant source and receive a cited answer.</small></div><button className="text-link" onClick={onBrowse}>Go to Ask Code <Icon name="arrow" size={14} /></button></div>}</section>
        <aside className="status-side-column"><div className="status-card api-health-card"><span className="health-icon"><Icon name="status" size={18} /></span><div className="page-kicker">BACKEND CONNECTION</div><h3>RepoLens API</h3><p>Repository operations and answers are served by the connected FastAPI backend.</p><div className="health-state"><i className={`health-dot ${apiOnline ? 'online' : 'offline'}`} />{apiOnline ? 'Backend health check succeeded' : 'Backend health check unavailable'}</div></div>{summary && <div className="status-card index-summary"><div className="page-kicker">LATEST INDEXING RESULT</div><h3>Index summary</h3><div className="status-details"><KeyValue label="Result" value={summary.status} /><KeyValue label="Files processed" value={summary.processed_files} /><KeyValue label="Files with errors" value={summary.failed_files} /><KeyValue label="Symbols parsed" value={summary.total_symbols} /><KeyValue label="Chunks created" value={summary.total_chunks} /><KeyValue label="Chunks indexed" value={summary.indexed_chunks} /></div>{Array.isArray(summary.errors) && summary.errors.length > 0 && <details className="operation-errors"><summary>{summary.errors.length} indexing {summary.errors.length === 1 ? 'note' : 'notes'}</summary>{summary.errors.map((entry, index) => <p key={index}><code>{entry.file_path || entry.stage || 'Indexing'}</code> — {entry.message}</p>)}</details>}</div>}</aside></div> : <div className="empty-list"><span className="empty-list-mark"><Icon name="status" size={22} /></span><h2>No repository selected</h2><p>Connect a repository or choose one from your workspace to see its status.</p><button className="secondary-button" onClick={onBrowse}>Browse repositories <Icon name="arrow" size={15} /></button></div>}
    </div>
  );
}

function App() {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepository, setSelectedRepository] = useState(null);
  const [activeView, setActiveView] = useState('ask');
  const [apiOnline, setApiOnline] = useState(false);
  const [loadingRepositories, setLoadingRepositories] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [messagesByRepo, setMessagesByRepo] = useState({});
  const [lastOperation, setLastOperation] = useState(null);
  const [notice, setNotice] = useState('');

  const selectRepository = useCallback((repo) => {
    if (selectedRepository?.id !== repo.id) setLastOperation(null);
    setSelectedRepository(repo);
    setError('');
    setNotice('');
    try { sessionStorage.setItem(SESSION_REPOSITORY_KEY, String(repo.id)); } catch { /* Session persistence is optional. */ }
  }, [selectedRepository?.id]);

  const refreshRepository = useCallback(async (id) => {
    const repo = await api.repository(id);
    setSelectedRepository(repo);
    setRepositories((current) => [repo, ...current.filter((item) => item.id !== repo.id)]);
    return repo;
  }, []);

  useEffect(() => {
    let active = true;
    api.health().then(() => { if (active) setApiOnline(true); }).catch(() => { if (active) setApiOnline(false); });
    api.repositories().then((items) => {
      if (!active) return;
      const list = Array.isArray(items) ? items : [];
      setRepositories(list);
      let savedId = null;
      try { savedId = sessionStorage.getItem(SESSION_REPOSITORY_KEY); } catch { /* Session persistence is optional. */ }
      const saved = list.find((item) => String(item.id) === savedId);
      const next = saved || list[0] || null;
      setSelectedRepository(next);
      if (next) {
        try { sessionStorage.setItem(SESSION_REPOSITORY_KEY, String(next.id)); } catch { /* Session persistence is optional. */ }
      }
    }).catch((reason) => {
      if (active) setError(reason.message);
    }).finally(() => { if (active) setLoadingRepositories(false); });
    return () => { active = false; };
  }, []);

  const messages = useMemo(
    () => selectedRepository ? (messagesByRepo[selectedRepository.id] || []) : [],
    [messagesByRepo, selectedRepository],
  );

  const handleIngest = async (event) => {
    event.preventDefault();
    if (!sourceUrl.trim() || busy) return;
    setBusy('ingest'); setError(''); setNotice(''); setLastOperation(null);
    try {
      const result = await api.ingest(sourceUrl.trim());
      const repo = result.repository;
      setSelectedRepository(repo);
      setRepositories((current) => [repo, ...current.filter((item) => item.id !== repo.id)]);
      try { sessionStorage.setItem(SESSION_REPOSITORY_KEY, String(repo.id)); } catch { /* Session persistence is optional. */ }
      setLastOperation(result);
      setSourceUrl('');
      setActiveView('ask');
      const indexed = result.indexing?.indexed_chunks;
      setNotice(indexed != null ? `Repository connected. ${indexed} chunks were indexed.` : 'Repository connected.');
      setApiOnline(true);
    } catch (reason) {
      if (reason.status === 409 && reason.detail?.repository_id) {
        try {
          const repo = await api.repository(reason.detail.repository_id);
          selectRepository(repo);
          setActiveView('ask');
          setNotice('This repository is already registered. It is selected in your workspace.');
          return;
        } catch { /* Fall through to the original conflict message. */ }
      }
      setError(reason.message);
      setApiOnline(reason.status ? true : false);
    } finally { setBusy(''); }
  };

  const handleIndex = async () => {
    if (!selectedRepository || busy) return;
    setBusy('index'); setError(''); setNotice('');
    try {
      const result = await api.index(selectedRepository.id);
      const repo = result.repository;
      setSelectedRepository(repo);
      setRepositories((current) => [repo, ...current.filter((item) => item.id !== repo.id)]);
      setLastOperation(result);
      setNotice(result.indexing?.indexed_chunks != null ? `${result.indexing.indexed_chunks} chunks indexed.` : 'Indexing completed.');
    } catch (reason) {
      setError(reason.message);
      if (reason.status) {
        try { await refreshRepository(selectedRepository.id); } catch { /* Keep the last known repository state. */ }
      } else setApiOnline(false);
    } finally { setBusy(''); }
  };

  const handleAsk = async (question) => {
    if (!selectedRepository || busy) return;
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const repoId = selectedRepository.id;
    setMessagesByRepo((current) => ({
      ...current,
      [repoId]: [...(current[repoId] || []), { id, question, pending: true }],
    }));
    setBusy('ask'); setError(''); setNotice('');
    try {
      const result = await api.ask(repoId, question);
      setMessagesByRepo((current) => ({
        ...current,
        [repoId]: (current[repoId] || []).map((message) => message.id === id
          ? { ...message, pending: false, answer: result.answer, sources: result.sources || [] }
          : message),
      }));
      setApiOnline(true);
    } catch (reason) {
      setMessagesByRepo((current) => ({
        ...current,
        [repoId]: (current[repoId] || []).filter((message) => message.id !== id),
      }));
      setError(reason.message);
      setApiOnline(reason.status ? true : false);
    } finally { setBusy(''); }
  };

  const connectRepository = () => {
    setActiveView('ask');
    setSelectedRepository(null);
    setError(''); setNotice('');
    try { sessionStorage.removeItem(SESSION_REPOSITORY_KEY); } catch { /* Session persistence is optional. */ }
    window.setTimeout(() => document.getElementById('repository-url')?.focus(), 0);
  };

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} setActiveView={(view) => { setActiveView(view); setError(''); setNotice(''); }} repository={selectedRepository} repositories={repositories} selectRepository={(repo) => { selectRepository(repo); setActiveView('ask'); }} apiOnline={apiOnline} />
      <main className="main-area">
        <Topbar repository={selectedRepository} apiOnline={apiOnline} setActiveView={setActiveView} />
        <div className={`workspace ${!selectedRepository && activeView === 'ask' ? 'workspace-welcome' : ''}`}>
          {notice && <div className="notice-banner" role="status"><span><Icon name="check" size={16} /></span>{notice}<button onClick={() => setNotice('')} aria-label="Dismiss notice">×</button></div>}
          {activeView === 'ask' && selectedRepository && <ChatWorkspace key={selectedRepository.id} repository={selectedRepository} messages={messages} onAsk={handleAsk} busy={busy === 'ask'} error={error} dismissError={() => setError('')} />}
          {activeView === 'ask' && !selectedRepository && <EmptyWorkspace sourceUrl={sourceUrl} setSourceUrl={setSourceUrl} onIngest={handleIngest} busy={busy === 'ingest'} error={error} dismissError={() => setError('')} />}
          {activeView === 'repositories' && <RepositoryList repositories={repositories} selectedRepository={selectedRepository} selectRepository={(repo) => { selectRepository(repo); setActiveView('ask'); }} onConnect={connectRepository} loading={loadingRepositories} />}
          {activeView === 'status' && <StatusPage repository={selectedRepository} lastOperation={lastOperation} onIndex={handleIndex} busy={busy === 'index'} error={error} dismissError={() => setError('')} onBrowse={() => setActiveView('repositories')} apiOnline={apiOnline} />}
          <footer className="workspace-footer"><span>REPOLENS AI</span><span>Grounded in your source, built for understanding.</span></footer>
        </div>
      </main>
    </div>
  );
}

export default App;
