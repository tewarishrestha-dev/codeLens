import { useState } from "react";
import { API_URL, fetchJson } from "../api";

// Renders an evidence-aware answer: paragraphs are preserved, bullet lists
// are grouped, and [file:line] citations become clickable links.
function AnswerBody({ answer, onOpenFile }) {
  if (!answer) return null;

  const paragraphs = answer.split(/\n\n+/);

  return (
    <div className="answer-body">
      {paragraphs.map((paragraph, i) => {
        const isBullet = paragraph.startsWith("- ");

        if (isBullet) {
          const items = paragraph
            .split("\n")
            .filter((line) => line.trim())
            .map((line) => line.replace(/^-\s*/, ""));

          return (
            <ul key={i} className="answer-list">
              {items.map((item, j) => (
                <li key={j}>
                  <CitationText text={item} onOpenFile={onOpenFile} />
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p key={i}>
            <CitationText text={paragraph} onOpenFile={onOpenFile} />
          </p>
        );
      })}
    </div>
  );
}

// Splits text on [file:line] citations and renders each as a clickable chip.
function CitationText({ text, onOpenFile }) {
  const parts = text.split(/(\[[^\]\n]+:\d+\])/g);

  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/^\[([^\]\n]+):(\d+)\]$/);

        if (match) {
          const [, file, line] = match;

          return (
            <button
              key={i}
              className="citation-chip"
              onClick={() => onOpenFile(file, Number(line))}
              title={`Open ${file}:${line}`}
            >
              {file}:{line}
            </button>
          );
        }

        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export function AskPage({ result, aiStatus, onOpenFile }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [context, setContext] = useState([]);
  const [asking, setAsking] = useState(false);
  const [summary, setSummary] = useState("");
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState("");

  async function askCodebase() {
    if (!question.trim() || !result) return;

    setAsking(true);
    setAnswer("");
    setContext([]);
    setError("");
    aiStatus("thinking", "Reading the code…");

    try {
      const data = await fetchJson(
        `${API_URL}/repository/${result.repository_id}/ask?question=${encodeURIComponent(question)}`
      );

      setAnswer(data.answer);
      setContext(data.context || []);

      const files = data.context?.length ?? 0;
      aiStatus(
        "success",
        files === 0
          ? "Answered — no strong evidence found."
          : `Grounded in ${files} source file${files === 1 ? "" : "s"}.`
      );
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Ask failed.");
    } finally {
      setAsking(false);
    }
  }

  async function summarizeCodebase() {
    if (!result) return;

    setSummarizing(true);
    setSummary("");
    setError("");
    aiStatus("thinking", "Summarizing project…");

    try {
      const data = await fetchJson(
        `${API_URL}/repository/${result.repository_id}/summary`
      );

      setSummary(data.summary);
      aiStatus("success", "Summary ready.");
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Summary failed.");
    } finally {
      setSummarizing(false);
    }
  }

  if (!result) {
    return (
      <div className="page ask-page">
        <div className="empty-state">
          <p>No repository loaded.</p>
          <p className="empty-hint">Analyze one from the Command Center first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page ask-page">
      <div className="page-header">
        <p className="page-kicker">
          <span className="kicker-index">04</span> Grounded Q&amp;A
        </p>
        <h2>Ask CodeLens</h2>
        <p>
          Questions about <strong>{result.name}</strong> are answered from
          retrieved source only. Unsupported claims are demoted, not asserted.
        </p>
      </div>

      <div className="ask-controls">
        <input
          placeholder="Ask about this codebase…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && askCodebase()}
        />
        <button onClick={askCodebase} disabled={asking || !question.trim()}>
          {asking ? "Asking…" : "Ask"}
        </button>
        <button onClick={summarizeCodebase} disabled={summarizing}>
          {summarizing ? "Analyzing…" : "Summarize Project"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {answer && (
        <div className="codebase-answer">
          <strong>CodeLens:</strong>
          <AnswerBody answer={answer} onOpenFile={onOpenFile} />
        </div>
      )}

      {summary && (
        <div className="codebase-answer">
          <strong>Project Summary:</strong>
          <AnswerBody answer={summary} onOpenFile={onOpenFile} />
        </div>
      )}

      {context.length > 0 && (
        <div className="evidence-panel">
          <h4>Source Evidence</h4>
          <p className="evidence-hint">
            Files retrieved to ground this answer. Click to open.
          </p>
          <ul>
            {context.map((item) => (
              <li
                key={item.file}
                onClick={() => onOpenFile(item.file)}
                style={{ cursor: "pointer" }}
              >
                <strong>{item.file}</strong>
                {item.matches?.length > 0 && (
                  <span className="evidence-matches">
                    {" "}
                    — {item.matches.length} match
                    {item.matches.length > 1 ? "es" : ""}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
