import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import { getSessionQuestions, submitAnswer, completeScreening } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast, Spinner } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";
import type { QuestionPublic } from "../../api/types";
import { ThinkScene, FormScene, RestScene } from "../../components/Illustrations";

const ADVANCE_DELAY_MS = 450;

function encouragement(answered: number, total: number) {
  if (answered >= total) return "Semua sudah terjawab. Tekan Selesai untuk melihat hasilnya.";
  const pct = answered / total;
  if (pct < 0.25) return "Pilih jawaban yang paling menggambarkan dirimu.";
  if (pct < 0.5) return "Bagus, lanjut pelan-pelan ya.";
  if (pct < 0.75) return "Sudah lebih dari separuh, kamu hebat.";
  return "Sedikit lagi selesai.";
}

export default function Screening() {
  const { sessionId } = useScreening();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [questions, setQuestions] = useState<QuestionPublic[] | null>(null);
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<"next" | "prev">("next");
  const [answers, setAnswers] = useState<Record<string, string>>({}); // question_id -> option_id
  const [completing, setCompleting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelAdvance = () => {
    if (advanceTimer.current) { clearTimeout(advanceTimer.current); advanceTimer.current = null; }
  };
  useEffect(() => cancelAdvance, []);

  useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const qs = await getSessionQuestions(sessionId);
        if (qs.length === 0) {
          setLoadError("Belum ada pertanyaan yang tersedia untuk jabatanmu. Silakan hubungi admin.");
          return;
        }
        setQuestions(qs);
        // restore saved answers (e.g. after a browser refresh) so progress isn't lost
        const restored: Record<string, string> = {};
        qs.forEach((q) => { if (q.answered_option_id) restored[q.id] = q.answered_option_id; });
        setAnswers(restored);
        const firstUnanswered = qs.findIndex((q) => !q.answered_option_id);
        setIndex(firstUnanswered >= 0 ? firstUnanswered : 0);
      } catch (err) {
        setLoadError(getErrorMessage(err));
      }
    })();
  }, [sessionId]);

  const total = questions?.length ?? 0;

  const goTo = useCallback((next: number) => {
    if (next < 0 || next >= total) return;
    cancelAdvance();
    setDirection(next >= index ? "next" : "prev");
    setIndex(next);
  }, [total, index]);

  const selectOption = useCallback(async (optionId: string) => {
    if (!sessionId || !questions) return;
    const q = questions[index];
    const previous = answers[q.id];
    const wasPending = advanceTimer.current !== null;
    cancelAdvance();
    setAnswers((prev) => ({ ...prev, [q.id]: optionId }));
    try {
      await submitAnswer(sessionId, q.id, optionId);
    } catch (err) {
      // revert so the screen never shows an answer the server doesn't have
      setAnswers((prev) => {
        const next = { ...prev };
        if (previous) next[q.id] = previous; else delete next[q.id];
        return next;
      });
      showToast(`Jawaban belum tersimpan. ${getErrorMessage(err)}`, "error");
      return;
    }
    // Move on automatically after a first answer; changing an answer later stays put.
    const isLast = index === questions.length - 1;
    if (!isLast && (!previous || wasPending)) {
      advanceTimer.current = setTimeout(() => {
        advanceTimer.current = null;
        setDirection("next");
        setIndex((cur) => Math.min(cur + 1, questions.length - 1));
      }, ADVANCE_DELAY_MS);
    }
  }, [sessionId, questions, index, answers, showToast]);

  // Keyboard: A-D pick an option, arrows move between questions.
  useEffect(() => {
    if (!questions) return;
    const q = questions[index];
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      const opt = q.options.find((o) => o.option_code === e.key.toUpperCase());
      if (opt) { e.preventDefault(); void selectOption(opt.id); }
      else if (e.key === "ArrowRight" && answers[q.id]) goTo(index + 1);
      else if (e.key === "ArrowLeft") goTo(index - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [questions, index, answers, selectOption, goTo]);

  if (!sessionId) return <Navigate to="/beranda" replace />;

  if (loadError) {
    return (
      <FlowLayout>
        <div className="empty-state">
          <p>{loadError}</p>
          <button className="btn btn-secondary" onClick={() => navigate("/beranda")}>Kembali ke beranda</button>
        </div>
      </FlowLayout>
    );
  }

  if (!questions) {
    return <FlowLayout><Spinner label="Menyiapkan pertanyaanmu..." /></FlowLayout>;
  }

  const current = questions[index];
  const answeredCount = questions.filter((q) => answers[q.id]).length;
  const allAnswered = answeredCount === total;
  const isLast = index === total - 1;
  const pct = Math.round((answeredCount / total) * 100);

  const handleFinish = async () => {
    const firstMissing = questions.findIndex((q) => !answers[q.id]);
    if (firstMissing >= 0) {
      showToast(`Masih ada ${total - answeredCount} pertanyaan yang belum kamu jawab`, "error");
      goTo(firstMissing);
      return;
    }
    setCompleting(true);
    try {
      await completeScreening(sessionId);
      navigate("/hasil");
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setCompleting(false);
    }
  };

  return (
    <FlowLayout>
      <div className="q-progress q-head">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="meter-row">
            <span>Pertanyaan {index + 1} dari {total}</span>
            <strong>{answeredCount} terjawab</strong>
          </div>
          <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
          <p className="q-cheer" aria-live="polite">{encouragement(answeredCount, total)}</p>
        </div>
        <div className="spot" aria-hidden="true">
          {pct >= 75 ? <RestScene /> : pct >= 35 ? <FormScene /> : <ThinkScene />}
        </div>
      </div>

      <div className="q-dots" role="tablist" aria-label="Daftar pertanyaan">
        {questions.map((q, i) => (
          <button
            key={q.id} type="button" role="tab" aria-selected={i === index}
            aria-label={`Pertanyaan ${i + 1}${answers[q.id] ? ", sudah dijawab" : ""}`}
            className={`q-dot ${answers[q.id] ? "answered" : ""} ${i === index ? "current" : ""}`}
            onClick={() => goTo(i)}
          />
        ))}
      </div>

      <div key={current.id} className={`q-body q-enter-${direction}`}>
        <h1 className="q-text-big">{current.question_text}</h1>

        <div className="option-list" role="radiogroup" aria-label="Pilihan jawaban">
          {current.options.map((opt) => {
            const selected = answers[current.id] === opt.id;
            return (
              <label key={opt.id} className={`option-item ${selected ? "selected" : ""}`}>
                <input type="radio" name={`q-${current.id}`} checked={selected} onChange={() => void selectOption(opt.id)} />
                <span className="option-badge">{opt.option_code}</span>
                <span className="option-label">{opt.option_text}</span>
                <svg className="option-check" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M5 12.5l4.5 4.5L19 7.5" />
                </svg>
              </label>
            );
          })}
        </div>
      </div>

      <div className="btn-row nav-row">
        <button className="btn btn-secondary" disabled={index === 0} onClick={() => goTo(index - 1)}>Sebelumnya</button>
        {isLast ? (
          <button className={`btn btn-primary ${allAnswered ? "btn-pulse" : ""}`} onClick={handleFinish} disabled={completing}>
            {completing ? "Sebentar ya..." : "Selesai"}
          </button>
        ) : (
          <button className="btn btn-primary" disabled={!answers[current.id]} onClick={() => goTo(index + 1)}>Berikutnya</button>
        )}
      </div>
      <p className="key-hint">Tip: tekan huruf A sampai D untuk memilih, panah kiri/kanan untuk pindah.</p>
    </FlowLayout>
  );
}
