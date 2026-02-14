import { useCallback, useState } from "react";

type Health = { status: string };
type Years = { years: string[] };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [years, setYears] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const h = await fetch("/api/v1/health").then((r) => r.json() as Promise<Health>);
    const y = await fetch("/api/v1/meta/years").then((r) => r.json() as Promise<Years>);
    setHealth(h);
    setYears(y.years);
  }, []);

  const onClick = useCallback(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  return (
    <div className="page">
      <header className="header">
        <div className="title">EXIOBASE Explorer</div>
        <button className="button" onClick={onClick}>
          API testen
        </button>
      </header>

      <main className="main">
        <section className="card">
          <div className="cardTitle">Backend</div>
          <div className="row">
            <div className="label">Health</div>
            <div className="value">{health ? health.status : "—"}</div>
          </div>
          <div className="row">
            <div className="label">Years</div>
            <div className="value">{years.length ? years.join(", ") : "—"}</div>
          </div>
          {error ? <div className="error">{error}</div> : null}
        </section>
      </main>
    </div>
  );
}

