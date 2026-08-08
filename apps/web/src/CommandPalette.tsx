import { type KeyboardEvent as ReactKeyboardEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { globalSearch, type SearchResult } from "./api/search";

export default function CommandPalette() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const clean = query.trim();
    setSelected(0);
    if (!clean) {
      setResults([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      globalSearch(clean)
        .then((items) => { if (!cancelled) setResults(items); })
        .catch((cause: unknown) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Search failed"); })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, 120);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, open]);

  function choose(result: SearchResult) {
    setOpen(false);
    setQuery("");
    setResults([]);
    navigate(result.href);
  }

  function onInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelected((value) => Math.min(value + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelected((value) => Math.max(value - 1, 0));
    } else if (event.key === "Enter" && results[selected]) {
      event.preventDefault();
      choose(results[selected]);
    }
  }

  return (
    <>
      <button className="command-palette-trigger" type="button" onClick={() => setOpen(true)}>
        Search <kbd>Ctrl K</kbd>
      </button>

      {open && (
        <div className="command-palette-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
          <section className="command-palette" role="dialog" aria-modal="true" aria-label="Search AgentDesk" onMouseDown={(event) => event.stopPropagation()}>
            <div className="command-palette-input-row">
              <span>⌕</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={onInputKeyDown}
                placeholder="Search tickets, projects, repositories…"
                aria-label="Search AgentDesk"
              />
              <kbd>Esc</kbd>
            </div>

            <div className="command-palette-results">
              {!query.trim() && <div className="command-palette-empty">Try a ticket key like <strong>AD-17</strong> or search by title.</div>}
              {loading && <div className="command-palette-empty">Searching…</div>}
              {error && <div className="command-palette-error">{error}</div>}
              {!loading && query.trim() && !error && results.length === 0 && <div className="command-palette-empty">No matches.</div>}
              {results.map((result, index) => (
                <button
                  type="button"
                  className={`command-result${index === selected ? " selected" : ""}`}
                  key={`${result.kind}-${result.id}`}
                  onMouseEnter={() => setSelected(index)}
                  onClick={() => choose(result)}
                >
                  <span className="command-result-kind">{result.kind}</span>
                  <span className="command-result-copy">
                    <strong>{result.label}</strong>
                    <small>{result.subtitle}{result.archived ? " · archived" : ""}</small>
                  </span>
                  {index === selected && <span className="command-enter">↵</span>}
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
