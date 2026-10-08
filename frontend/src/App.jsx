import React, {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  LayoutGrid,
  Files,
  MessageCircle,
  User,
  Upload,
  ArrowRight,
  ChevronRight,
  Check,
  Shield,
  Search,
  X,
  Trash2,
  RefreshCw,
  Send,
  Lock,
  LogOut,
  BookOpen,
  Plus,
  Info,
  Copy,
  Eye,
  Leaf,
  Activity,
} from "lucide-react";
import { createPortalStore } from "./store.mjs";
import {
  TYPES,
  dateLabel,
  filterRecords,
  formatBytes,
  recordTitle,
} from "./lib/utils.mjs";

export const SUGGESTIONS = [
  {
    icon: "records",
    label: "My medications",
    question: "What medications were prescribed in my records?",
  },
  {
    icon: "pulse",
    label: "My lab results",
    question: "What was my latest HbA1c value?",
  },
  {
    icon: "book",
    label: "A visit summary",
    question: "Summarize my most recent clinical note.",
  },
];
const SYMBOLS = {
  grid: LayoutGrid,
  records: Files,
  chat: MessageCircle,
  user: User,
  upload: Upload,
  arrow: ArrowRight,
  chevron: ChevronRight,
  check: Check,
  shield: Shield,
  search: Search,
  close: X,
  trash: Trash2,
  refresh: RefreshCw,
  send: Send,
  lock: Lock,
  logout: LogOut,
  book: BookOpen,
  plus: Plus,
  info: Info,
  copy: Copy,
  eye: Eye,
  leaf: Leaf,
  pulse: Activity,
};
export function Icon({ name, ...props }) {
  const Component = SYMBOLS[name] || Info;
  return (
    <Component
      className="icon"
      aria-hidden="true"
      strokeWidth={1.6}
      {...props}
    />
  );
}
export function Brand() {
  return (
    <>
      <span className="brand-mark" aria-hidden="true">
        c<span />
      </span>
      <span className="brand-name">
        clarity<span className="brand-dot">.</span>
      </span>
    </>
  );
}
export function Notice({ error }) {
  return error ? (
    <div className="notice" role="alert">
      <Icon name="info" />
      <div>
        <p>{error.message || String(error)}</p>
        {error.requestId && <small>Support reference: {error.requestId}</small>}
      </div>
    </div>
  ) : null;
}
function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}
function Connection({ health, full = false }) {
  return (
    <span className={`connection ${health === false ? "offline" : ""}`}>
      <i />
      {health === null
        ? "Checking service"
        : health
          ? full
            ? "Connected to your records service"
            : "Connected"
          : "Service unavailable"}
    </span>
  );
}
function TypeOptions({ blank = "All record types" }) {
  return (
    <>
      <option value="">{blank}</option>
      {Object.entries(TYPES).map(([value, label]) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </>
  );
}
export function StatusBadge({ status }) {
  const labels = {
    completed: "Ready",
    processing: "Processing",
    uploaded: "Uploaded",
    failed: "Needs attention",
  };
  return (
    <span
      className={`status-badge ${Object.hasOwn(labels, status) ? status : "uploaded"}`}
    >
      <span />
      {labels[status] || "Unknown"}
    </span>
  );
}
function Header({ eyebrow, title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1 tabIndex={-1}>{title}</h1>
        <p className="muted">{subtitle}</p>
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

export function Auth({ state, actions }) {
  const [showPassword, setShowPassword] = useState(false),
    register = state.authMode === "register";
  function submit(event) {
    event.preventDefault();
    const form = event.currentTarget,
      values = new FormData(form);
    const credentials = {
      name: String(values.get("name") || ""),
      email: String(values.get("email")),
      password: String(values.get("password")),
    };
    form.elements.password.value = "";
    actions.authenticate(credentials);
  }
  return (
    <div className="auth-layout">
      <section className="auth-story" aria-label="About Clarity">
        <a className="brand" href="#" aria-label="Clarity home">
          <Brand />
        </a>
        <div className="auth-story-copy">
          <span className="eyebrow light">YOUR HEALTH, IN CONTEXT</span>
          <h1>
            A little less searching.
            <br />A little more clarity.
          </h1>
          <p>
            Your medical records, brought together.
            <br />
            Answers that start with your own story.
          </p>
        </div>
        <div className="record-art" aria-hidden="true">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-spark">✳</div>
          <div className="art-card card-back">
            <span className="art-icon">
              <Icon name="pulse" />
            </span>
            <div className="art-line long" />
            <div className="art-line" />
            <div className="art-chart">
              {[1, 2, 3, 4, 5].map((i) => (
                <span key={i} />
              ))}
            </div>
          </div>
          <div className="art-card card-front">
            <span className="art-icon">
              <Icon name="records" />
            </span>
            <div className="art-line long" />
            <div className="art-line" />
            <div className="art-line medium" />
            <div className="art-check">
              <Icon name="check" />
            </div>
          </div>
          <div className="art-label">
            <Icon name="leaf" /> A clearer view of your care
          </div>
        </div>
        <div className="auth-story-footer">
          <Icon name="shield" />
          <span>Answers grounded in your uploaded records.</span>
        </div>
      </section>
      <main id="main" tabIndex={-1} className="auth-main">
        <div className="auth-mobile-brand brand">
          <Brand />
        </div>
        <div className="auth-card">
          <span className="eyebrow">WELCOME TO YOUR PERSONAL HEALTH SPACE</span>
          <h2>{register ? "Start your story." : "Welcome back."}</h2>
          <p className="muted auth-subtitle">
            {register
              ? "Keep your records together, and make sense of them."
              : "Sign in to pick up where you left off."}
          </p>
          <div className="auth-tabs" role="group" aria-label="Account action">
            <button
              type="button"
              onClick={() => actions.authMode("login")}
              className={!register ? "active" : ""}
              aria-pressed={!register}
              disabled={state.authBusy}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => actions.authMode("register")}
              className={register ? "active" : ""}
              aria-pressed={register}
              disabled={state.authBusy}
            >
              Create account
            </button>
          </div>
          <Notice error={state.authError} />
          <form
            id="auth-form"
            aria-label={register ? "Create account" : "Sign in"}
            onSubmit={submit}
            key={state.authMode}
          >
            {register && (
              <>
                <label htmlFor="auth-name">Full name</label>
                <input
                  id="auth-name"
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={120}
                  placeholder="Your name"
                  disabled={state.authBusy}
                />
              </>
            )}
            <label htmlFor="auth-email">Email address</label>
            <input
              id="auth-email"
              name="email"
              type="email"
              autoComplete="username"
              required
              maxLength={254}
              placeholder="you@example.com"
              value={state.authEmail}
              onChange={(e) => actions.set("authEmail", e.target.value)}
              disabled={state.authBusy}
            />
            <label htmlFor="auth-password">Password</label>
            <div className="password-field">
              <input
                id="auth-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 12 : 1}
                maxLength={128}
                placeholder={
                  register ? "Create a password" : "Enter your password"
                }
                disabled={state.authBusy}
              />
              <button
                type="button"
                className="icon-button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                <Icon name="eye" />
              </button>
            </div>
            {register && (
              <p className="field-help">Use at least 12 characters.</p>
            )}
            <button
              className="button primary auth-submit"
              type="submit"
              disabled={state.authBusy}
            >
              {state.authBusy ? (
                <>
                  <Spinner /> Please wait…
                </>
              ) : (
                <>
                  {register ? "Create your account" : "Sign in"}
                  <Icon name="arrow" />
                </>
              )}
            </button>
          </form>
          <p className="auth-footnote">
            <Icon name="lock" /> Your records are accessible through your
            patient account.
          </p>
        </div>
        <div className="auth-bottom">
          <span>Clarity · Your health, in context</span>
          <Connection health={state.health} />
        </div>
      </main>
    </div>
  );
}

function EmptyRecords({ actions, compact = false }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      <span className="empty-icon">
        <Icon name="records" />
      </span>
      <h3>Your story starts with a record.</h3>
      <p>
        Add a prescription, lab report, or visit note.
        <br />
        Then ask Clarity to help you find what matters.
      </p>
      <button
        type="button"
        className="button primary"
        onClick={() => actions.navigate("documents")}
      >
        <Icon name="plus" />
        Add your first record
      </button>
    </div>
  );
}
export function RecordList({ state, actions, recent = false }) {
  const records = recent
    ? filterRecords(state.documents, {}, state.filenames).slice(0, 4)
    : filterRecords(state.documents, state.filters, state.filenames);
  if (!state.docsLoaded && state.docsBusy)
    return (
      <div className="record-loading" role="status">
        <Spinner />
        Loading your records…
      </div>
    );
  if (state.docsError)
    return (
      <>
        <Notice error={state.docsError} />
        <button className="button secondary" onClick={actions.loadDocs}>
          Try again
        </button>
      </>
    );
  if (!state.documents.length)
    return <EmptyRecords actions={actions} compact={recent} />;
  if (!records.length)
    return (
      <div className="empty-state compact">
        <span className="empty-icon">
          <Icon name="search" />
        </span>
        <h3>No matching records.</h3>
        <p>Try a different search or clear your filters.</p>
        <button className="button secondary" onClick={actions.resetFilters}>
          Clear filters
        </button>
      </div>
    );
  return (
    <div className="table-scroll">
      <table className="records-table">
        <thead>
          <tr>
            <th scope="col">Record</th>
            <th scope="col">Record date</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.document_id}>
              <td>
                <div className="record-cell">
                  <span
                    className={`file-icon ${record.document_type === "lab_report" ? "lab" : ""}`}
                  >
                    <Icon
                      name={
                        record.document_type === "lab_report"
                          ? "pulse"
                          : "records"
                      }
                    />
                  </span>
                  <div>
                    <button
                      type="button"
                      className="record-title"
                      onClick={() => actions.showRecord(record.document_id)}
                    >
                      {recordTitle(record, state.filenames)}
                    </button>
                    <span>
                      {TYPES[record.document_type] || "Medical record"} <b>·</b>{" "}
                      Added {dateLabel(record.created_at)}
                    </span>
                  </div>
                </div>
              </td>
              <td className="record-date">
                {dateLabel(record.document_date, "Not provided")}
              </td>
              <td>
                <StatusBadge status={record.processing_status} />
              </td>
              <td className="row-actions">
                <button
                  className="icon-button"
                  onClick={() => actions.showRecord(record.document_id)}
                  aria-label={`View details for ${recordTitle(record, state.filenames)}`}
                >
                  <Icon name="chevron" />
                </button>
                {!recent && (
                  <button
                    className="icon-button danger-subtle"
                    onClick={() => actions.confirmDelete(record.document_id)}
                    aria-label={`Delete ${recordTitle(record, state.filenames)}`}
                  >
                    <Icon name="trash" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Suggestions({ actions, chat = false }) {
  return (
    <div className={chat ? "chat-suggestions" : "suggestion-list"}>
      {SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          type="button"
          onClick={() => actions.ask(s.question)}
        >
          <Icon name={s.icon} />
          <span>{s.label}</span>
          <Icon name="arrow" />
        </button>
      ))}
    </div>
  );
}
function Overview({ state, actions }) {
  const ready = state.documents.filter(
      (d) => d.processing_status === "completed",
    ).length,
    attention = state.documents.filter(
      (d) => d.processing_status === "failed",
    ).length;
  return (
    <>
      <Header
        eyebrow="A LITTLE MORE CLARITY, EVERY DAY"
        title={`Hello, ${state.patient.name.split(/\s+/)[0]}.`}
        subtitle="Welcome to a calmer place for your medical records."
      />
      <section className="overview-hero">
        <div>
          <span className="pill light-pill">
            <Icon name="leaf" /> YOUR HEALTH, IN CONTEXT
          </span>
          <h2>
            Bring your records together.
            <br />
            Find the answers within.
          </h2>
          <p>
            From a lab result to a note from your last visit,
            <br />
            make your health story a little easier to follow.
          </p>
          <div className="hero-actions">
            <button
              className="button dark"
              onClick={() => actions.navigate(ready ? "chat" : "documents")}
            >
              <Icon name={ready ? "chat" : "upload"} />
              {ready ? "Ask about my records" : "Add my first record"}
              <Icon name="arrow" />
            </button>
            {ready ? (
              <a className="text-link" href="#documents">
                View my records
              </a>
            ) : (
              <span className="hero-file-hint">PDF, TXT &amp; DOCX</span>
            )}
          </div>
        </div>
        <div className="hero-illustration" aria-hidden="true">
          <span className="hero-circle" />
          <div className="hero-note">
            <div className="hero-note-head">
              <span>
                <Icon name="records" />
              </span>
              <div className="art-line" />
            </div>
            <div className="art-line long" />
            <div className="art-line medium" />
            <div className="art-line long" />
            <div className="note-ready">
              <Icon name="check" /> A clearer picture
            </div>
          </div>
          <div className="hero-mini">
            <Icon name="chat" /> Answers in your records
          </div>
          <span className="hero-star">✳</span>
        </div>
      </section>
      <section className="stats-row" aria-label="Your record summary">
        {[
          {
            icon: "records",
            label: "Records together",
            value: state.docsLoaded ? state.documents.length : "—",
          },
          {
            icon: "check",
            label: "Ready to ask about",
            value: state.docsLoaded ? ready : "—",
          },
          {
            icon: attention ? "info" : "shield",
            label: attention ? "Need attention" : "Your records stay yours",
            value: attention || "Personal by design",
          },
        ].map((stat, i) => (
          <div className="stat" key={stat.label}>
            <span className="stat-icon">
              <Icon name={stat.icon} />
            </span>
            <div>
              <span>{stat.label}</span>
              <strong className={i === 2 ? "stat-note" : ""}>
                {stat.value}
              </strong>
            </div>
          </div>
        ))}
      </section>
      <div className="overview-bottom">
        <section className="panel recent-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">YOUR HEALTH LIBRARY</span>
              <h2>Recent records</h2>
            </div>
            <a href="#documents" className="text-link">
              View all <Icon name="arrow" />
            </a>
          </div>
          <RecordList state={state} actions={actions} recent />
        </section>
        <section className="panel question-panel">
          <span className="question-icon">
            <Icon name="chat" />
          </span>
          <span className="eyebrow">A GOOD PLACE TO START</span>
          <h2>What's on your mind?</h2>
          <p className="muted">
            Ask a question about something in your records.
          </p>
          <Suggestions actions={actions} />
          <div className="grounded-note">
            <Icon name="book" />
            <span>Every answer starts with your uploaded records.</span>
          </div>
        </section>
      </div>
    </>
  );
}
function Documents({ state, actions }) {
  const input = useRef(null),
    [dragging, setDragging] = useState(false);
  function drop(e) {
    e.preventDefault();
    setDragging(false);
    if (state.uploadBusy) return;
    const files = e.dataTransfer.files;
    files.length === 1 ? actions.setFile(files[0]) : actions.rejectFiles();
  }
  return (
    <>
      <Header
        eyebrow="YOUR HEALTH LIBRARY"
        title="My records"
        subtitle="Keep the details of your care in one place."
      >
        <button
          className="button secondary"
          onClick={actions.loadDocs}
          disabled={state.docsBusy}
        >
          <Icon name="refresh" />
          Refresh
        </button>
      </Header>
      <section className="panel upload-panel" aria-labelledby="upload-title">
        <div className="upload-intro">
          <span className="section-icon">
            <Icon name="upload" />
          </span>
          <div>
            <h2 id="upload-title">Add a medical record</h2>
            <p className="muted">
              A prescription, a report, or a note from your visit.
            </p>
          </div>
        </div>
        <form
          id="upload-form"
          onSubmit={(e) => {
            e.preventDefault();
            actions.upload();
          }}
        >
          <div className="upload-grid">
            <div>
              <button
                type="button"
                id="dropzone"
                className={`dropzone ${dragging ? "dragging" : ""}`}
                onClick={() => input.current.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={drop}
                disabled={state.uploadBusy || !state.config}
                aria-describedby="upload-guide"
              >
                <Icon name={state.file ? "records" : "upload"} />
                <strong>
                  {state.file ? state.file.name : "Drop a file here, or browse"}
                </strong>
                <span>
                  {state.file
                    ? formatBytes(state.file.size)
                    : "Choose one record at a time"}
                </span>
              </button>
              <input
                ref={input}
                id="file-input"
                className="sr-only"
                type="file"
                accept=".pdf,.txt,.docx"
                aria-label="Choose medical record"
                disabled={state.uploadBusy}
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) actions.setFile(file);
                  e.target.value = "";
                }}
              />
              <p id="upload-guide" className="field-help">
                PDF, TXT, or DOCX ·{" "}
                {state.config
                  ? `Up to ${state.config.max_upload_size_mb} MB`
                  : "Loading upload settings…"}
              </p>
              {state.file && !state.uploadBusy && (
                <button
                  type="button"
                  className="text-link small-link"
                  onClick={actions.removeFile}
                >
                  Remove selected file
                </button>
              )}
            </div>
            <div className="upload-fields">
              <label htmlFor="upload-type">
                Record type <span className="optional">optional</span>
              </label>
              <select
                id="upload-type"
                value={state.uploadType}
                onChange={(e) => actions.set("uploadType", e.target.value)}
                disabled={state.uploadBusy}
              >
                <TypeOptions blank="Detect from record" />
              </select>
              <label htmlFor="upload-date">
                Record date <span className="optional">optional</span>
              </label>
              <input
                type="date"
                id="upload-date"
                value={state.uploadDate}
                onChange={(e) => actions.set("uploadDate", e.target.value)}
                disabled={state.uploadBusy}
              />
              <p className="field-help">
                The date on your report or prescription.
              </p>
            </div>
          </div>
          <Notice error={state.uploadError} />
          <div className="upload-bottom">
            <span>
              <Icon name="shield" />
              Records are prepared before they're used for answers.
            </span>
            <button
              type="submit"
              className="button primary"
              disabled={state.uploadBusy || !state.config || !state.file}
            >
              {state.uploadBusy ? (
                <>
                  <Spinner />
                  Preparing your record…
                </>
              ) : (
                <>
                  <Icon name="plus" />
                  Add record
                </>
              )}
            </button>
          </div>
          {state.uploadBusy && (
            <p className="processing-note" role="status">
              Uploading and preparing your record. This can take a little while.
            </p>
          )}
        </form>
      </section>
      <section className="panel library-panel">
        <div className="panel-heading">
          <div>
            <h2>
              Your records{" "}
              <span className="count-label">{state.documents.length}</span>
            </h2>
            <p className="muted">
              Only records in your patient account appear here.
            </p>
          </div>
        </div>
        <div className="record-filters">
          <div className="search-field">
            <Icon name="search" />
            <input
              id="record-search"
              type="search"
              placeholder="Search your records"
              aria-label="Search your records"
              value={state.filters.search}
              onChange={(e) => actions.filter("search", e.target.value)}
            />
          </div>
          <select
            id="record-type-filter"
            aria-label="Filter by record type"
            value={state.filters.type}
            onChange={(e) => actions.filter("type", e.target.value)}
          >
            <TypeOptions />
          </select>
          <select
            id="record-status-filter"
            aria-label="Filter by processing status"
            value={state.filters.status}
            onChange={(e) => actions.filter("status", e.target.value)}
          >
            <option value="">All statuses</option>
            {Object.entries({
              completed: "Ready",
              processing: "Processing",
              uploaded: "Uploaded",
              failed: "Needs attention",
            }).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div id="document-list">
          <RecordList state={state} actions={actions} />
        </div>
      </section>
    </>
  );
}
export function Message({ message, actions }) {
  const pending = message.status === "pending",
    failed = message.status === "error";
  return (
    <article className="chat-turn">
      <div className="user-message">
        <span className="message-label">YOU</span>
        <p>{message.question}</p>
      </div>
      <div className="assistant-message">
        <span className="assistant-avatar">c</span>
        <div className="assistant-content">
          <div className="assistant-name">
            Clarity{" "}
            <span>
              {pending
                ? "Looking through your records"
                : failed
                  ? "Couldn't answer yet"
                  : message.result.status === "answered"
                    ? "Grounded in your records"
                    : "Not found in your records"}
            </span>
          </div>
          {pending ? (
            <div className="pending-answer" role="status">
              <span className="thinking-dots">
                <i />
                <i />
                <i />
              </span>
              <span>Finding an answer in your records…</span>
            </div>
          ) : failed ? (
            <>
              <Notice error={message.error} />
              <button
                className="button secondary small"
                onClick={() => actions.retry(message.id)}
              >
                <Icon name="refresh" />
                Retry question
              </button>
            </>
          ) : (
            <>
              <p className="answer-text">{message.result.answer}</p>
              {message.result.sources.length ? (
                <div className="answer-sources">
                  <span>FROM YOUR RECORDS</span>
                  <div>
                    {message.result.sources.map((source, i) => (
                      <button
                        key={`${source.document_id}-${i}`}
                        type="button"
                        className="source-chip"
                        onClick={() => actions.showRecord(source.document_id)}
                      >
                        <Icon name="records" />
                        <span>
                          {TYPES[source.document_type] || "Medical record"}
                          {source.document_date
                            ? ` · ${dateLabel(source.document_date)}`
                            : ""}
                        </span>
                        <Icon name="chevron" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="answer-help">
                  Try another question, or add a record that contains the
                  missing information.
                </p>
              )}
              <div className="answer-footer">
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => actions.copy(message.id)}
                  aria-label="Copy answer"
                >
                  <Icon name="copy" />
                </button>
                <details className="response-details">
                  <summary>Response details</summary>
                  <p>
                    Received in {(message.elapsed / 1000).toFixed(1)} seconds
                  </p>
                  <p>
                    Reference: <code>{message.result.request_id}</code>
                  </p>
                </details>
              </div>
            </>
          )}
        </div>
      </div>
    </article>
  );
}
function Chat({ state, actions }) {
  const ready = state.documents.filter(
      (r) => r.processing_status === "completed",
    ).length,
    scroll = useRef(null),
    question = useRef(null);
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [state.messages.length, state.chatBusy]);
  useEffect(() => {
    if (!state.chatBusy && ready)
      question.current?.focus({ preventScroll: true });
  }, [state.chatBusy, ready]);
  return (
    <>
      <Header
        eyebrow="YOUR RECORD ASSISTANT"
        title="A question, a little clarity."
        subtitle="Answers based on your medical records, with sources you can check."
      >
        {!!state.messages.length && (
          <button className="button secondary" onClick={actions.clearChat}>
            Clear conversation
          </button>
        )}
      </Header>
      <section className="panel chat-panel">
        <div className="chat-toolbar">
          <span>
            <Icon name="book" />
            Answer from
          </span>
          <select
            id="chat-type"
            aria-label="Choose record type for your question"
            value={state.chatType}
            onChange={(e) => actions.set("chatType", e.target.value)}
            disabled={state.chatBusy}
          >
            <TypeOptions blank="All my records" />
          </select>
          <span className="chat-record-count">
            {ready} ready {ready === 1 ? "record" : "records"}
          </span>
        </div>
        <div
          ref={scroll}
          id="chat-messages"
          className="chat-messages"
          aria-live="polite"
          aria-relevant="additions text"
        >
          {state.messages.length ? (
            state.messages.map((message) => (
              <Message key={message.id} message={message} actions={actions} />
            ))
          ) : (
            <div className="chat-welcome">
              <span className="welcome-symbol">
                <Icon name="chat" />
              </span>
              <span className="eyebrow">
                YOUR STORY IS A GOOD STARTING POINT
              </span>
              <h2>Let's look at your records.</h2>
              <p>
                {ready
                  ? "Ask about a result, a prescription, or a detail from your last visit."
                  : "Add a record first. Then ask about a result, a prescription, or a visit."}
              </p>
              <Suggestions actions={actions} chat />
              {!ready && (
                <button
                  className="button primary"
                  onClick={() => actions.navigate("documents")}
                >
                  Add a medical record
                </button>
              )}
            </div>
          )}
        </div>
        <form
          id="chat-form"
          className="chat-composer"
          onSubmit={(e) => {
            e.preventDefault();
            actions.ask();
          }}
        >
          <label className="sr-only" htmlFor="question">
            Ask a question about your records
          </label>
          <div className="composer-box">
            <textarea
              ref={question}
              id="question"
              rows={2}
              maxLength={state.config?.question_max_length || 2000}
              placeholder={
                ready
                  ? "What would you like to understand about your records?"
                  : "Add a readable record to get started."
              }
              disabled={!ready || state.chatBusy}
              value={state.draft}
              onChange={(e) => actions.set("draft", e.target.value)}
            />
            <button
              type="submit"
              className="send-button"
              aria-label="Send question"
              disabled={!ready || state.chatBusy || !state.draft.trim()}
            >
              {state.chatBusy ? <Spinner /> : <Icon name="send" />}
            </button>
          </div>
          <div className="composer-footer">
            <span>
              <Icon name="shield" />
              Record information, not medical advice.
            </span>
            <span id="question-count">
              {state.draft.length} / {state.config?.question_max_length || 2000}
            </span>
          </div>
        </form>
      </section>
    </>
  );
}
function Account({ state, actions }) {
  return (
    <>
      <Header
        eyebrow="YOUR PERSONAL SPACE"
        title="My account"
        subtitle="A place for your details and your records."
      />
      <div className="account-grid">
        <section className="panel profile-panel">
          <div className="panel-heading">
            <h2>Patient profile</h2>
            <span className="pill">
              <Icon name="check" />
              Signed in
            </span>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Name</dt>
              <dd>{state.patient.name}</dd>
            </div>
            <div>
              <dt>Email address</dt>
              <dd>{state.patient.email}</dd>
            </div>
            <div>
              <dt>Account</dt>
              <dd>Patient</dd>
            </div>
          </dl>
          <div className="account-signout">
            <p className="muted">
              Signing out clears this tab's records and conversation.
            </p>
            <button
              className="button secondary"
              onClick={() => actions.logout()}
            >
              <Icon name="logout" />
              Sign out
            </button>
          </div>
        </section>
        <section className="panel service-panel">
          <span className="section-icon">
            <Icon name="pulse" />
          </span>
          <h2>Service connection</h2>
          <p className="muted">
            Check whether your records service is available.
          </p>
          <Connection health={state.health} full />
          <button className="button secondary" onClick={actions.bootstrap}>
            <Icon name="refresh" />
            Check connection
          </button>
        </section>
        <section className="panel how-panel">
          <span className="eyebrow">HOW CLARITY WORKS</span>
          <h2>Your records are the starting point.</h2>
          <div className="how-steps">
            {[
              {
                title: "Bring a record",
                text: "Add a readable PDF, TXT, or DOCX from your care.",
              },
              {
                title: "Ask your question",
                text: "Find a detail, review a result, or summarize a note.",
              },
              {
                title: "Check the source",
                text: "Answers link to the records they use. Missing information is clearly identified.",
              },
            ].map((step, i) => (
              <div key={step.title}>
                <span>0{i + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            ))}
          </div>
          <div className="grounded-note">
            <Icon name="shield" />
            <span>
              Direct identifiers are masked before records are used for answers.
              Clinical information remains sensitive and belongs in your patient
              account.
            </span>
          </div>
        </section>
      </div>
    </>
  );
}

export function RecordDetail({ record, state, actions }) {
  return (
    <>
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">YOUR RECORD</span>
          <h2 id="record-dialog-title">
            {recordTitle(record, state.filenames)}
          </h2>
        </div>
        <button
          className="icon-button"
          onClick={actions.closeDialog}
          aria-label="Close record details"
        >
          <Icon name="close" />
        </button>
      </div>
      <div className="dialog-body">
        <StatusBadge status={record.processing_status} />
        <dl className="detail-list">
          <div>
            <dt>Record type</dt>
            <dd>{TYPES[record.document_type] || "Medical record"}</dd>
          </div>
          <div>
            <dt>Record date</dt>
            <dd>{dateLabel(record.document_date, "Not provided")}</dd>
          </div>
          <div>
            <dt>Added to your records</dt>
            <dd>{dateLabel(record.created_at)}</dd>
          </div>
          <div>
            <dt>Stored file</dt>
            <dd className="file-reference">{record.filename}</dd>
          </div>
        </dl>
        {record.processing_status === "failed" ? (
          <div className="notice" role="status">
            This record could not be prepared. Delete it and try uploading a
            readable file again.
          </div>
        ) : (
          <p className="muted">
            {record.processing_status === "completed"
              ? "Ready to use when you ask about your records."
              : "This record is still being prepared. Refresh your library to check its status."}
          </p>
        )}
      </div>
      <div className="dialog-actions">
        <button
          className="button danger-outline"
          onClick={() => actions.confirmDelete(record.document_id)}
        >
          <Icon name="trash" />
          Delete record
        </button>
        {record.processing_status === "completed" ? (
          <button
            className="button primary"
            onClick={() => actions.askRecordType(record.document_type)}
          >
            Ask about this record type
            <Icon name="arrow" />
          </button>
        ) : (
          <button className="button secondary" onClick={actions.closeDialog}>
            Close
          </button>
        )}
      </div>
    </>
  );
}
function Modal({ state, actions }) {
  const ref = useRef(null),
    dialog = state.dialog;
  useEffect(() => {
    if (dialog && !ref.current.open) ref.current.showModal();
  }, [dialog]);
  if (!dialog) return null;
  const deleting = dialog.kind === "delete";
  return (
    <dialog
      ref={ref}
      id={deleting ? "delete-dialog" : "record-dialog"}
      aria-labelledby={deleting ? "delete-dialog-title" : "record-dialog-title"}
      onCancel={(e) => {
        e.preventDefault();
        if (!state.deleteBusy) actions.closeDialog();
      }}
    >
      {deleting ? (
        <>
          <div className="dialog-body">
            <span className="eyebrow">REMOVE A RECORD</span>
            <h2 id="delete-dialog-title">Delete this record?</h2>
            <p>
              This removes its saved content and clears this tab's conversation.
              This cannot be undone.
            </p>
            <Notice error={state.deleteError} />
          </div>
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={state.deleteBusy}
              onClick={actions.closeDialog}
            >
              Keep record
            </button>
            <button
              className="button danger"
              disabled={state.deleteBusy}
              onClick={actions.deleteRecord}
            >
              {state.deleteBusy ? "Deleting…" : "Delete record"}
            </button>
          </div>
        </>
      ) : dialog.record ? (
        <RecordDetail record={dialog.record} state={state} actions={actions} />
      ) : (
        <div className="dialog-body">
          <h2 id="record-dialog-title">
            {dialog.loading ? "Loading record…" : "Record unavailable"}
          </h2>
          <Notice error={dialog.error} />
          <button className="button secondary" onClick={actions.closeDialog}>
            Close
          </button>
        </div>
      )}
    </dialog>
  );
}
export function Shell({ state, actions }) {
  const views = {
      overview: ["grid", "Overview"],
      documents: ["records", "My records"],
      chat: ["chat", "Record assistant"],
      account: ["user", "My account"],
    },
    initials = state.patient.name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((n) => n[0])
      .join("")
      .toUpperCase();
  const Page =
    { overview: Overview, documents: Documents, chat: Chat, account: Account }[
      state.view
    ] || Overview;
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Clarity overview">
          <Brand />
        </a>
        <span className="sidebar-caption">YOUR PERSONAL SPACE</span>
        <nav className="main-nav" aria-label="Main navigation">
          {Object.entries(views).map(([view, [icon, label]]) => (
            <a
              key={view}
              href={`#${view}`}
              className={`nav-link ${state.view === view ? "active" : ""}`}
              aria-current={state.view === view ? "page" : undefined}
            >
              <Icon name={icon} />
              <span>{label}</span>
              {view === "documents" && state.documents.length > 0 && (
                <span className="nav-count">{state.documents.length}</span>
              )}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="note-icon">
            <Icon name="leaf" />
          </span>
          <h3>A place for your story.</h3>
          <p>
            Your records. Your questions.
            <br />
            One calmer place to begin.
          </p>
          <a href="#account" className="text-link">
            How Clarity works
            <Icon name="arrow" />
          </a>
        </div>
        <div className="sidebar-profile">
          <span className="avatar">{initials}</span>
          <div>
            <strong>{state.patient.name}</strong>
            <span>Patient account</span>
          </div>
          <button
            className="icon-button"
            onClick={() => actions.logout()}
            aria-label="Sign out"
          >
            <Icon name="logout" />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">
            Your space <span>/</span>
            <strong>{views[state.view][1]}</strong>
          </span>
          <div className="topbar-right">
            <Connection health={state.health} />
            <span className="avatar small">{initials}</span>
          </div>
        </header>
        <main
          id="main"
          tabIndex={-1}
          className={`main-content ${state.view === "chat" ? "chat-page" : ""}`}
        >
          <Page state={state} actions={actions} />
        </main>
        <footer className="workspace-footer">
          <span>Made for a clearer view of your care.</span>
          <span>
            <Icon name="lock" />
            Your personal records space
          </span>
        </footer>
      </div>
    </div>
  );
}

const portal = createPortalStore();
export default function App() {
  const state = useSyncExternalStore(portal.subscribe, portal.getSnapshot),
    actions = portal.actions;
  useEffect(() => portal.start(), []);
  useEffect(() => {
    document.querySelector(".page-header h1")?.focus({ preventScroll: true });
  }, [state.view, !!state.patient]);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      {state.patient ? (
        <Shell state={state} actions={actions} />
      ) : (
        <Auth state={state} actions={actions} />
      )}
      <Modal state={state} actions={actions} />
      <div id="toast" role="status" aria-live="polite" hidden={!state.toast}>
        {state.toast}
      </div>
    </>
  );
}
