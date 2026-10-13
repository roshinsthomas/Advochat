import { useState } from "react";
import { getCurrentUser, login, register } from "../services/api";

export default function AuthForm({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;

    const fields = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError("");

    try {
      if (mode === "register") {
        await register(fields);
      }

      await login(fields.username, fields.password);
      onLogin(await getCurrentUser());
    } catch (err) {
      setError(err.message || "Could not connect to the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container py-5">
      <div className="auth-card card border-0 shadow-sm mx-auto">
        <div className="card-body p-4">
          <h1 className="h3">Advocate Assistant</h1>
          <p className="text-secondary">
            {mode === "login"
              ? "Sign in to access your saved conversations."
              : "Create an account to save your conversations."}
          </p>

          {error && (
            <div className="alert alert-danger message-text" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <fieldset disabled={busy}>
              <label htmlFor="username" className="form-label">
                Username
              </label>
              <input
                id="username"
                name="username"
                className="form-control mb-3"
                autoComplete="username"
                maxLength={150}
                required
              />

              {mode === "register" && (
                <>
                  <label htmlFor="email" className="form-label">Email</label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    className="form-control mb-3"
                    autoComplete="email"
                    required
                  />
                </>
              )}

              <label htmlFor="password" className="form-label">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                className="form-control mb-3"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                maxLength={128}
                required
              />

              {mode === "register" && (
                <>
                  <label htmlFor="password_confirm" className="form-label">
                    Confirm password
                  </label>
                  <input
                    id="password_confirm"
                    name="password_confirm"
                    type="password"
                    className="form-control mb-3"
                    autoComplete="new-password"
                    maxLength={128}
                    required
                  />
                </>
              )}

              <button className="btn btn-primary w-100" type="submit">
                {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
              </button>

              <button
                className="btn btn-link w-100 mt-2"
                type="button"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
              >
                {mode === "login"
                  ? "Need an account? Register"
                  : "Already registered? Sign in"}
              </button>
            </fieldset>
          </form>
        </div>
      </div>
    </main>
  );
}