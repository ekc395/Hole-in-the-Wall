import { useEffect, useRef, useState } from "react";

type SearchResult = {
  id: string;
  name: string;
  city: string | null;
  address: string | null;
  category_primary: string;
  categories: string[];
  rating: number;
  review_count: number;
  summary_text: string;
  matched_terms: string[];
};

const defaultQuery = "ramen";
const defaultCity = "Seattle";

function Icon({
  name,
  size = 20,
  strokeWidth = 1.8,
}: {
  name: "search" | "heart" | "map" | "arrow" | "close" | "spark" | "clock" | "pin" | "chevron";
  size?: number;
  strokeWidth?: number;
}) {
  const paths = {
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    heart: (
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" />
    ),
    map: (
      <>
        <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
        <path d="M9 3v15M15 6v15" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m13 6 6 6-6 6" />
      </>
    ),
    close: (
      <>
        <path d="m6 6 12 12M18 6 6 18" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 1.2 4.3a5 5 0 0 0 3.5 3.5L21 12l-4.3 1.2a5 5 0 0 0-3.5 3.5L12 21l-1.2-4.3a5 5 0 0 0-3.5-3.5L3 12l4.3-1.2a5 5 0 0 0 3.5-3.5Z" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    pin: (
      <>
        <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

const cityOptions = ["Seattle", "Bellevue", "Redmond", "Shoreline", "Lynnwood", "Bothell", "Kirkland", "Renton", "Kent", "Tukwila", "Edmonds", "Federal Way", "Anywhere"];

export default function App() {
  const [query, setQuery] = useState(defaultQuery);
  const [city, setCity] = useState(defaultCity);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [saved, setSaved] = useState<string[]>([]);
  const requestRef = useRef<AbortController | null>(null);
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const [dataMode, setDataMode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.body.style.overflow = selected ? "hidden" : "";
    if (selected) dialogRef.current?.showModal();
    return () => {
      document.body.style.overflow = "";
    };
  }, [selected]);

  const loadResults = async (nextQuery = query, nextCity = city) => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        q: nextQuery,
        limit: "20",
      });

      if (nextCity && nextCity !== "Anywhere") {
        params.set("city", nextCity);
      }

      const response = await fetch(`/api/search?${params.toString()}`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = await response.json();
      setResults(payload.results ?? []);
      setDataMode(payload.data_status?.mode ?? null);
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error(err);
      setError("Unable to load restaurants from the backend right now.");
      setResults([]);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    void loadResults(defaultQuery, defaultCity);
    return () => requestRef.current?.abort();
  }, []);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void loadResults();
  };

  const toggleSave = (id: string) => {
    setSaved((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };


  return (
    <div className="min-h-screen bg-[#f4f1e9] text-[#24362b]">
      <header className="border-b border-[#294f3b]/10 bg-[#f4f1e9]/90 backdrop-blur-md">
        <div className="mx-auto flex h-20 max-w-[1240px] items-center justify-between px-5 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-[14px] bg-[#294f3b] text-[#f0e4ca]">
              <Icon name="spark" size={20} />
            </span>
            <span className="font-display text-[22px] font-semibold tracking-[-0.04em]">
              Hole In the Wall
            </span>
          </div>

          <nav className="hidden items-center gap-8 text-sm font-medium md:flex">
            <a className="border-b border-[#294f3b] py-2" href="#discover">
              Discover
            </a>
            <button
              className="py-2 text-[#516458] transition hover:text-[#24362b]"
              onClick={() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth" })}
            >
              Results
            </button>
            <a className="py-2 text-[#516458] transition hover:text-[#24362b]" href="#about">
              About
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section id="discover" className="relative overflow-hidden px-5 pb-12 pt-14 lg:px-8 lg:pb-20 lg:pt-20">
          <div className="leaf leaf-one" />
          <div className="leaf leaf-two" />

          <div className="relative mx-auto max-w-[1100px] text-center">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#71866f]/25 bg-[#e6ebdf] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.19em] text-[#466149]">
              <Icon name="spark" size={14} /> Your next favorite table
            </p>

            <h1 className="font-display mx-auto max-w-[800px] text-[48px] font-semibold leading-[0.98] tracking-[-0.055em] text-[#1f382a] sm:text-[64px] lg:text-[78px]">
              Good food, found <span className="italic text-[#90775b]">your way.</span>
            </h1>

            <p className="mx-auto mt-6 max-w-[560px] text-base leading-7 text-[#5d6c62] sm:text-lg">
              Search the Seattle-area business data from the notebooks and discover what matches your craving.
            </p>

            <div className="mt-10 rounded-[30px] border border-[#294f3b]/10 bg-[#fffdf8] p-5 text-left shadow-[0_24px_70px_rgba(42,61,48,0.12)] lg:p-8">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="flex flex-col gap-4 lg:flex-row">
                  <label className="relative flex-1">
                    <span className="sr-only">Search for food</span>
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#5d6c62]">
                      <Icon name="search" size={18} />
                    </span>
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      className="w-full rounded-full border border-[#294f3b]/15 bg-[#f6f5ef] py-3.5 pl-12 pr-4 text-base text-[#24362b] outline-none transition focus:border-[#294f3b]"
                      placeholder="Search for ramen, pizza, sushi, coffee..."
                    />
                  </label>

                  <label className="min-w-[180px]">
                    <span className="sr-only">Choose city</span>
                    <select
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                      className="w-full rounded-full border border-[#294f3b]/15 bg-[#f6f5ef] px-4 py-3.5 text-base text-[#24362b] outline-none transition focus:border-[#294f3b]"
                    >
                      {cityOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </label>

                  <button
                    type="submit"
                    className="flex items-center justify-center gap-2 rounded-full bg-[#294f3b] px-7 py-3.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(41,79,59,0.2)] transition hover:-translate-y-0.5 hover:bg-[#1f3e2e]"
                  >
                    <Icon name="search" size={17} /> Find my spot
                  </button>
                </div>
              </form>
            </div>
          </div>
        </section>

        <section id="results" className="bg-[#dde5d8] px-5 py-16 lg:px-8 lg:py-20">
          <div className="mx-auto max-w-[1240px]">
            <div className="mb-9 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
              <div>
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[#6e765e]">
                  {loading ? "Searching" : "Results"}
                </p>
                <h2 className="font-display text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
                  {results.length} {results.length === 1 ? "place" : "places"} worth a visit
                </h2>
              </div>

              <button
                className="flex items-center gap-2 self-start rounded-full border border-[#294f3b]/20 bg-[#edf1e8] px-5 py-3 text-sm font-semibold transition hover:bg-white sm:self-auto"
                onClick={() => void loadResults(query, city)}
              >
                <Icon name="map" size={17} /> Refresh results
              </button>
            </div>

            {dataMode === "metadata" && (
              <p role="status" className="mb-6 rounded-2xl bg-[#edf1e8] p-4 text-sm text-[#53615d]">
                Searching restaurant names and categories. Review search will be available after the review data is exported from the notebooks.
              </p>
            )}
            {dataMode === "reviews" && (
              <p className="mb-6 text-sm text-[#53615d]">Searching names, categories, and a sample of up to 10,000 reviews.</p>
            )}
            {error && (
              <div className="mb-6 rounded-[24px] border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
                {error}
              </div>
            )}

            {loading ? (
              <div className="rounded-[28px] border border-dashed border-[#294f3b]/25 bg-[#edf1e8] px-6 py-16 text-center">
                <p className="font-display text-3xl font-semibold">Loading matches…</p>
              </div>
            ) : results.length ? (
              <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {results.map((restaurant, index) => (
                  <article
                    key={restaurant.id}
                    className={`restaurant-card group ${index === 0 ? "md:col-span-2 lg:col-span-1" : ""}`}
                  >
                    <div className="relative min-h-[120px] rounded-[22px] bg-[#e6ebdf] px-5 py-6">
                      {index === 0 && (
                        <span className="absolute left-4 top-4 rounded-full bg-[#f3ead8] px-3.5 py-2 text-[10px] font-bold uppercase tracking-[0.15em] text-[#654f37]">
                          Best match
                        </span>
                      )}

                      <button
                        className={`save-button ${saved.includes(restaurant.id) ? "saved" : ""}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleSave(restaurant.id);
                        }}
                        aria-label={`${saved.includes(restaurant.id) ? "Remove" : "Save"} ${restaurant.name}`}
                      >
                        <Icon name="heart" size={19} />
                      </button>

                      <div className="pt-5">
                        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#6e765e]">
                          {restaurant.category_primary || "Restaurant"}
                        </p>
                        <h3 className="mt-2 font-display text-[27px] font-semibold leading-tight tracking-[-0.035em]">
                          {restaurant.name}
                        </h3>
                      </div>
                    </div>

                    <div className="px-1 pb-1 pt-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="mt-1.5 text-sm text-[#637066]">
                            {restaurant.city || "Unknown city"} · {restaurant.address || "Address unavailable"}
                          </p>
                        </div>
                        <span className="flex shrink-0 items-center gap-1 rounded-full bg-[#edf1e8] px-2.5 py-1.5 text-sm font-bold">
                          <span className="text-[#8b734f]">★</span> {restaurant.rating.toFixed(1)}
                        </span>
                      </div>

                      <div className="mt-5 flex flex-wrap gap-2">
                        {restaurant.matched_terms.length ? (
                          restaurant.matched_terms.slice(0, 4).map((term) => (
                            <span key={`${restaurant.id}-${term}`} className="match-tag matched">
                              <Icon name="spark" size={12} />
                              {term}
                            </span>
                          ))
                        ) : (
                          <span className="match-tag">Local favorite</span>
                        )}
                      </div>

                      <div className="mt-4 rounded-[18px] bg-[#edf1e8] p-3 text-sm text-[#53615d]">
                        <strong className="text-[#24362b]">{restaurant.review_count}</strong> reviews ·
                        {" "}
                        {restaurant.summary_text || "No matching review excerpt available."}
                      </div>

                      <button onClick={() => setSelected(restaurant)} className="mt-6 flex w-full items-center justify-between border-t border-[#294f3b]/10 pt-4 text-sm font-semibold">
                        View restaurant{" "}
                        <span className="grid h-8 w-8 place-items-center rounded-full bg-[#e5eadf] transition group-hover:translate-x-1">
                          <Icon name="arrow" size={16} />
                        </span>
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-[28px] border border-dashed border-[#294f3b]/25 bg-[#edf1e8] px-6 py-16 text-center">
                <h3 className="font-display text-3xl font-semibold">No matches yet.</h3>
                <p className="mx-auto mt-3 max-w-md text-[#627066]">
                  Try another search term or switch city to surface more relevant businesses.
                </p>
              </div>
            )}
          </div>
        </section>

        <section id="about" className="bg-[#294f3b] px-5 py-14 text-[#f0eadf] lg:px-8">
          <div className="mx-auto flex max-w-[1240px] flex-col items-start justify-between gap-8 md:flex-row md:items-end">
            <div>
              <span className="font-display text-2xl font-semibold">Hole In the Wall</span>
              <p className="mt-3 max-w-md text-sm leading-6 text-[#c8d4ca]">
                Search the notebook-backed business and review data for local places worth trying.
              </p>
            </div>
            <p className="text-xs text-[#aebdaf]">Seattle-area restaurants, discovered your way.</p>
          </div>
        </section>
      </main>

      {selected && (
        <dialog
          ref={dialogRef}
          onCancel={() => setSelected(null)}
          className="fixed inset-0 z-50 m-0 h-full max-h-none w-full max-w-none items-end justify-center bg-transparent p-0 open:flex sm:items-center sm:p-5"
          aria-modal="true"
          aria-label={`${selected.name} details`}
          onMouseDown={() => setSelected(null)}
        >
          <div
            className="detail-modal relative max-h-[94vh] w-full max-w-[900px] overflow-y-auto rounded-t-[32px] bg-[#f9f6ee] shadow-2xl sm:rounded-[32px]"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              className="absolute right-4 top-4 z-10 grid h-11 w-11 place-items-center rounded-full bg-[#f9f6ee]/90 shadow-md backdrop-blur transition hover:rotate-6"
              onClick={() => setSelected(null)}
              autoFocus
              aria-label="Close details"
            >
              <Icon name="close" size={20} />
            </button>

            <div className="p-6 sm:p-9 md:p-10">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#84705a]">
                Seattle-area match
              </p>

              <h2 className="font-display mt-3 text-4xl font-semibold tracking-[-0.045em] sm:text-5xl">
                {selected.name}
              </h2>

              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-[#667269]">
                <span className="font-bold text-[#294f3b]">★ {selected.rating.toFixed(1)}</span>
                <span>({selected.review_count} reviews)</span>
                <span>·</span>
                <span>{selected.category_primary}</span>
              </div>

              <div className="my-7 h-px bg-[#294f3b]/10" />

              <div className="space-y-4 text-sm">
                <div className="flex gap-3">
                  <span className="mt-0.5 text-[#71866f]">
                    <Icon name="pin" size={18} />
                  </span>
                  <div>
                    <p className="font-semibold">{selected.address || "Address unavailable"}</p>
                    <p className="mt-0.5 text-[#758078]">{selected.city || "Unknown city"}</p>
                  </div>
                </div>
              </div>

              <div className="mt-8 rounded-[22px] bg-[#e6ebdf] p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.17em] text-[#6d795f]">
                  Why it matched
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selected.matched_terms.length ? (
                    selected.matched_terms.map((term) => (
                      <span key={`${selected.id}-detail-${term}`} className="match-tag matched">
                        <Icon name="spark" size={12} />
                        {term}
                      </span>
                    ))
                  ) : (
                    <span className="match-tag">High ranking local result</span>
                  )}
                </div>
              </div>

              <p className="mt-6 text-[15px] leading-7 text-[#526158]">
                {selected.summary_text || "No matching review excerpt available."}
              </p>

              <div className="mt-8 flex gap-3">
                <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${selected.name} ${selected.address || selected.city || ''}`)}`} target="_blank" rel="noreferrer" className="flex flex-1 items-center justify-center gap-2 rounded-full bg-[#294f3b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#1e3c2c]">
                  <Icon name="map" size={17} /> Open in Maps
                </a>
                <button
                  className={`grid h-12 w-12 place-items-center rounded-full border border-[#294f3b]/20 transition ${saved.includes(selected.id) ? "bg-[#b9cbb3] text-[#294f3b]" : "hover:bg-[#e6ebdf]"}`}
                  onClick={() => toggleSave(selected.id)}
                  aria-label="Save restaurant"
                >
                  <Icon name="heart" size={19} />
                </button>
              </div>
            </div>
          </div>
        </dialog>
      )}
    </div>
  );
}
