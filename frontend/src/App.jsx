import { useEffect, useRef, useState } from "react";
import AuthForm from "./components/AuthForm";
import {
  clearSession,
  getConversation,
  getCurrentUser,
  hasSession,
  listConversations,
  sendQuestion,
} from "./services/api";

function Sources({ sources = [] }) {
  return sources.map((source) => (
    <details className="source-card mt-3" key={source.id}>
      <summary>
        [{source.id}] Section {source.section_number}
      </summary>
      <p className="small text-secondary mt-2">
        {source.source_file} · Section pages{" "}
        {source.section_page_start}–{source.section_page_end}
      </p>
      {source.passages.map((passage, index) => (
        <p className="passage" key={index}>{passage}</p>
      ))}
    </details>
  ));
}

function ChatWorkspace({ user, onLogout }) {
  const [history, setHistory] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    let ignore = false;

    listConversations()
      .then((data) => {
        if (!ignore) {
          setHistory(data.results);
          setHasMore(Boolean(data.next));
        }
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      })
      .finally(() => {
        if (!ignore) setBusy(false);
      });

    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function showError(err) {
    if (err.status === 401) {
      onLogout();
      return;
    }
    setError(err.message || "Could not reach the server.");
  }

  async function openConversation(id) {
    if (busy) return;
    setBusy(true);
    setError("");

    try {
      const conversation = await getConversation(id);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
      setQuestion("");
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function loadMore() {
    if (busy) return;
    setBusy(true);
    setError("");

    try {
      const data = await listConversations(page + 1);
      setHistory((current) => [...current, ...data.results]);
      setPage((current) => current + 1);
      setHasMore(Boolean(data.next));
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  function newConversation() {
    setConversationId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const query = question.trim();

    if (!query || busy) return;
    setBusy(true);
    setError("");

    try {
      const result = await sendQuestion(query, conversationId);

      setConversationId(result.conversation_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: query,
          sources: [],
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.answer,
          sources: result.sources,
        },
      ]);
      setQuestion("");

      // Refresh the sidebar after the answer has been saved.
      try {
        const data = await listConversations();
        setHistory(data.results);
        setPage(1);
        setHasMore(Boolean(data.next));
      } catch {
        setError("Answer saved, but the sidebar could not refresh. Reload the page.");
      }
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="app-header">
        <div className="container-fluid px-4 d-flex justify-content-between align-items-center gap-3">
          <div>
            <h1 className="h4 mb-1">ADVOCHAT</h1>
            <h4 className="h4 mb-1">Advocate Assistant</h4>
            <span className="small text-secondary">Signed in as {user.username}</span>
          </div>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={onLogout}
            disabled={busy}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="container-fluid p-3 p-lg-4">
        <div className="row g-4">
          <aside className="col-md-4 col-lg-3">
            <div className="history-panel">
              <button
                className="btn btn-primary w-100 mb-3"
                onClick={newConversation}
                disabled={busy}
              >
                + New conversation
              </button>

              <h2 className="h6 text-secondary">Saved conversations</h2>

              {!history.length && !busy && (
                <p className="small text-secondary">Your chats will appear here.</p>
              )}

              <div className="list-group">
                {history.map((conversation) => (
                  <button
                    key={conversation.id}
                    className={`list-group-item list-group-item-action ${
                      conversationId === conversation.id ? "active" : ""
                    }`}
                    onClick={() => openConversation(conversation.id)}
                    disabled={busy}
                    aria-current={conversationId === conversation.id ? "true" : undefined}
                  >
                    <div className="history-title">{conversation.title}</div>
                    <small>
                      {new Date(conversation.updated_at).toLocaleDateString()}
                    </small>
                  </button>
                ))}
              </div>

              {hasMore && (
                <button
                  className="btn btn-outline-secondary btn-sm mt-3 w-100"
                  onClick={loadMore}
                  disabled={busy}
                >
                  Load more
                </button>
              )}
            </div>
          </aside>

          <main className="col-md-8 col-lg-9">
            <div className="chat-content mx-auto">
              <div className="alert alert-warning small">
                Historical IPC development sample. Not verified current law
                or professional legal advice.
              </div>

              {error && (
                <div className="alert alert-danger message-text" role="alert">
                  {error}
                </div>
              )}

              <section className="conversation" aria-label="Conversation" aria-busy={busy}>
                {!messages.length && !busy && (
                  <div className="empty-state">
                    <div className="eyebrow">ASK IN YOUR OWN WORDS</div>
                    <h2 className="h3 mt-2">Start with a situation.</h2>
                    <p className="text-secondary">
                      Your questions, answers, and source references will be saved.
                    </p>
                  </div>
                )}

                {messages.map((message) => (
                  <article
                    className={`message message-${message.role}`}
                    key={message.id}
                  >
                    <div className="message-label">
                      {message.role === "user" ? "You" : "Advocate Assistant"}
                    </div>
                    <div className="message-text">{message.content}</div>
                    {message.role === "assistant" && (
                      <Sources sources={message.sources} />
                    )}
                  </article>
                ))}

                {busy && (
                  <div className="p-3 text-secondary" role="status">
                    <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                    Please wait…
                  </div>
                )}
                <div ref={bottomRef} />
              </section>

              <form className="composer" onSubmit={handleSubmit}>
                <label htmlFor="question" className="form-label fw-semibold">
                  Your question
                </label>
                <textarea
                  id="question"
                  className="form-control"
                  rows={3}
                  maxLength={1000}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  disabled={busy}
                  placeholder="Describe your situation…"
                  required
                />
                <div className="d-flex justify-content-between align-items-center gap-3 mt-3">
                  <small className="text-secondary">
                    Ask a question or follow up on the recent discussion.
                  </small>
                  <button
                    className="btn btn-primary px-4"
                    disabled={busy || !question.trim()}
                  >
                    Send
                  </button>
                </div>
              </form>
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [startupError, setStartupError] = useState("");

  useEffect(() => {
    let ignore = false;

    async function restoreSession() {
      try {
        if (hasSession()) {
          const currentUser = await getCurrentUser();
          if (!ignore) setUser(currentUser);
        }
      } catch (err) {
        if (err.status === 401) clearSession();
        if (!ignore) setStartupError(err.message);
      } finally {
        if (!ignore) setChecking(false);
      }
    }

    restoreSession();
    return () => { ignore = true; };
  }, []);

  function logout() {
    clearSession();
    setUser(null);
    setStartupError("");
  }

  if (checking) {
    return <p className="text-center p-5" role="status">Loading your account…</p>;
  }

  if (!user) {
    return (
      <>
        {startupError && (
          <div className="alert alert-warning m-3" role="alert">
            {startupError}
          </div>
        )}
        <AuthForm onLogin={(account) => {
          setStartupError("");
          setUser(account);
        }} />
      </>
    );
  }

  return <ChatWorkspace key={user.id} user={user} onLogout={logout} />;
}