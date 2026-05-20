import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { usePersistedState } from "../hooks/usePersistedState.js";
import CognitiveFacetCard from "../components/analytics/CognitiveFacetCard.jsx";
import DateFilter, { daysForFilter } from "../components/analytics/DateFilter.jsx";
import ActiveUsersTable from "../components/analytics/ActiveUsersTable.jsx";
import UserProfileCard from "../components/analytics/UserProfileCard.jsx";
import PlatformOverviewCard from "../components/analytics/PlatformOverviewCard.jsx";
import StrategyPerformancePanel from "../components/analytics/StrategyPerformancePanel.jsx";
import CustomerHealthSection from "../components/analytics/CustomerHealthSection.jsx";
import InfoHint from "../components/analytics/InfoHint.jsx";
import RagQualityPanel from "../components/quality/RagQualityPanel.jsx";
import "../styles/app-shell.css";
import "../styles/analytics.css";
import "../styles/quality.css";

/**
 * AnalyticsPage — cognitive facets + admin outreach view.
 *
 * Date window applies to:
 *   • Trending topics    (server-side `days` param)
 *   • Active customers   (server-side `days` param)
 * Cognitive facets and per-user interests are cumulative — the window doesn't
 * change them but they're shown for the inspected user as context.
 */
export default function AnalyticsPage() {
  // Single source of truth for the user search input:
  //   "" (empty)  → GLOBAL view — facets aggregate across all users; per-user
  //                 sections (profile / topic interest / offers) show a
  //                 "select a user" empty state.
  //   "foo"       → user-specific view — accepts either a raw user_id or a
  //                 hashed identifier (u_<hex>).
  const [inspectUser, setU] = usePersistedState("ape.user_id", "");
  const [windowId, setWindowId] = usePersistedState("ape.analytics.window", "30d");
  const [domain, setDomain] = usePersistedState("ape.analytics.domain", "");
  const [activeTab, setActiveTab] = usePersistedState("ape.analytics.tab", "overview");

  // Domains for the scope selector. "" = all domains aggregated. Keep in sync
  // with the RAG domains served by the backend.
  const DOMAIN_OPTIONS = [
    { id: "",        label: "All domains" },
    { id: "cricket", label: "Cricket" },
    { id: "it",      label: "IT" },
    { id: "movies",  label: "Movies" },
    { id: "travel",  label: "Travel" },
  ];
  const [lastRefresh, setLastRefresh] = useState(null);
  const [lastRecompute, setLastRecompute] = useState(null);

  // ── Tab navigation — splits the analytics page into focused views so
  //    admins don't have to scroll through everything to find one thing.
  const TABS = [
    { id: "overview",  label: "Overview"  },
    { id: "customers", label: "Customers" },
    { id: "cognition", label: "Cognition" },
    { id: "content",   label: "Content"   },
    { id: "health",    label: "Health"    },
  ];

  const hasUser = Boolean(inspectUser && inspectUser.trim());

  // Per-section data + error state
  const [profile, setProfile]       = useState(null);
  const [profileErr, setProfileErr] = useState(null);

  const [facets, setFacets]         = useState([]);
  const [facetsErr, setFacetsErr]   = useState(null);
  const [facetsLoad, setFacetsLoad] = useState(false);

  const [trends, setTrends]         = useState([]);
  const [trendsErr, setTrendsErr]   = useState(null);

  const [interests, setI]           = useState([]);
  const [interestsErr, setIErr]     = useState(null);

  const [offers, setOff]            = useState([]);
  const [offersErr, setOffErr]      = useState(null);

  const [activeUsers, setActive]    = useState([]);
  const [activeErr, setActiveErr]   = useState(null);

  const [platform, setPlatform]     = useState(null);
  const [platformErr, setPlatErr]   = useState(null);

  const [stratPerf, setStratPerf]   = useState(null);
  const [stratErr, setStratErr]     = useState(null);

  // Time series — daily activity for the trend charts
  const [platformSeries, setPlatformSeries] = useState([]);
  const [topicsSeries, setTopicsSeries]     = useState([]);
  const [userSeries, setUserSeries]         = useState([]);

  const [globalLoading, setGlobalLoading] = useState(false);

  // Ref to the cognitive-facets section so the "Inspect" button can scroll to it
  const facetsSectionRef = useRef(null);

  // Reload the user-scoped sections (profile + facets + interests + offers)
  // when the inspected user changes. The active-users list and trends are
  // window-driven and don't depend on this.
  async function reloadUserScopedSections() {
    await Promise.all([loadProfile(), loadFacets(), loadInterests(), loadOffers()]);
  }

  // Apply the current input value: refresh per-user sections + facets.
  function applyUser(value) {
    setU(value);
    setTimeout(() => {
      reloadUserScopedSections().then(() => {
        if (value && facetsSectionRef.current) {
          facetsSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    }, 0);
  }

  // Called from the Inspect button on the active-users table — sets the
  // search input to the user_id_hash (endpoints accept either raw or hash form).
  function inspectByHash(userHash) { if (userHash) applyUser(userHash); }

  // Clear the input → switch to global view (no user filter).
  function clearUser() { applyUser(""); }

  async function loadProfile() {
    setProfileErr(null);
    if (!hasUser) { setProfile(null); return; }
    try {
      const p = await api.userProfile(inspectUser.trim(), domain);
      setProfile(p);
    } catch (e) {
      setProfileErr(e.message);
      setProfile(null);
    }
  }

  async function loadFacets() {
    setFacetsLoad(true);
    setFacetsErr(null);
    try {
      // Empty input → global view (min 2 pulls per cell to filter noise).
      // Non-empty input → that user's cells (min 1 to show everything).
      const userArg = hasUser ? inspectUser.trim() : "";
      const minInter = hasUser ? 1 : 2;
      const f = await api.cognitiveFacets(userArg, minInter, domain);
      setFacets(Array.isArray(f) ? f : []);
    } catch (e) {
      setFacetsErr(e.message);
      setFacets([]);
    } finally {
      setFacetsLoad(false);
    }
  }

  async function loadTrends() {
    setTrendsErr(null);
    try {
      const days = Math.max(1, daysForFilter(windowId));
      const t = await api.trends(days, 30, false, domain);
      setTrends(Array.isArray(t) ? t : []);
    } catch (e) {
      setTrendsErr(e.message);
      setTrends([]);
    }
  }

  async function loadInterests() {
    setIErr(null);
    if (!hasUser) { setI([]); return; }
    try {
      const i = await api.userInterests(inspectUser.trim(), 10);
      setI(Array.isArray(i) ? i : []);
    } catch (e) {
      setIErr(e.message);
      setI([]);
    }
  }

  async function loadOffers() {
    setOffErr(null);
    if (!hasUser) { setOff([]); return; }
    try {
      const o = await api.userOffers(inspectUser.trim());
      setOff(Array.isArray(o) ? o : []);
    } catch (e) {
      setOffErr(e.message);
      setOff([]);
    }
  }

  async function loadActiveUsers() {
    setActiveErr(null);
    try {
      const days = daysForFilter(windowId);
      const a = await api.activeUsers(days, 0, 100, domain);
      setActive(Array.isArray(a) ? a : []);
    } catch (e) {
      setActiveErr(e.message);
      setActive([]);
    }
  }

  async function loadPlatform() {
    setPlatErr(null);
    try {
      const days = daysForFilter(windowId);
      const p = await api.platformOverview(days, 8, domain);
      setPlatform(p);
    } catch (e) {
      setPlatErr(e.message);
      setPlatform(null);
    }
  }

  async function loadStrategyPerf() {
    setStratErr(null);
    try {
      const userArg = hasUser ? inspectUser.trim() : "";
      const sp = await api.strategyPerformance(userArg, 3, domain);
      setStratPerf(sp);
    } catch (e) {
      setStratErr(e.message);
      setStratPerf(null);
    }
  }

  // Time-series loaders — separate from the main aggregates so a slow
  // aggregation pipeline can't block the headline numbers from rendering.
  async function loadPlatformSeries() {
    try {
      const days = daysForFilter(windowId);
      const s = await api.platformTimeseries(days, domain);
      setPlatformSeries(Array.isArray(s) ? s : []);
    } catch { setPlatformSeries([]); }
  }
  async function loadTopicsSeries() {
    try {
      const days = daysForFilter(windowId);
      const s = await api.topicsTimeseries(days, 5, domain);
      setTopicsSeries(Array.isArray(s) ? s : []);
    } catch { setTopicsSeries([]); }
  }
  async function loadUserSeries() {
    if (!hasUser) { setUserSeries([]); return; }
    try {
      const days = daysForFilter(windowId);
      const s = await api.userTimeseries(inspectUser.trim(), days, domain);
      setUserSeries(Array.isArray(s) ? s : []);
    } catch { setUserSeries([]); }
  }

  // Load all sections. By default this is READ-ONLY — we just fetch the
  // already-computed aggregates from Mongo. Passing { recompute: true } also
  // triggers /analytics/recompute first, which rebuilds the user_topic_interest
  // and topic_trend_daily collections from raw turn_records (slow + heavy).
  // The admin opts into recompute by clicking the "Recompute now" button.
  async function refresh(opts = {}) {
    const recompute = !!opts.recompute;
    setGlobalLoading(true);
    try {
      if (recompute) {
        try {
          await api.recomputeAnalytics(30);
          setLastRecompute(new Date());
        } catch (e) { /* shown per-section */ }
      }
      await Promise.all([
        loadProfile(),
        loadFacets(),
        loadTrends(),
        loadInterests(),
        loadOffers(),
        loadActiveUsers(),
        loadPlatform(),
        loadStrategyPerf(),
        loadPlatformSeries(),
        loadTopicsSeries(),
        loadUserSeries(),
      ]);
      setLastRefresh(new Date());
    } finally {
      setGlobalLoading(false);
    }
  }

  // Initial load — READ-ONLY. Show whatever was last computed; admin
  // can hit "Recompute now" if the data feels stale.
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  // Re-load only the window-driven sections when the date filter changes.
  // (Cognitive facets / interests / offers are cumulative — they intentionally
  // ignore the window. The header on the facets section labels this explicitly
  // so the admin knows the cards aren't broken when they don't change.)
  useEffect(() => {
    loadTrends();
    loadActiveUsers();
    loadPlatform();
    loadPlatformSeries();   // trend chart: daily turns across platform
    loadTopicsSeries();     // trend chart: per-topic daily counts
    loadUserSeries();       // trend chart: per-user daily activity (USER mode)
    // eslint-disable-next-line
  }, [windowId]);

  // Re-load the domain-scoped sections when the domain selector changes.
  // (platform overview, cognitive facets, active customers, and the per-user
  // profile all accept a domain filter; trends/time-series are cross-domain.)
  useEffect(() => {
    loadPlatform();
    loadActiveUsers();
    loadFacets();
    loadProfile();
    loadTrends();
    loadPlatformSeries();
    loadTopicsSeries();
    loadUserSeries();
    loadStrategyPerf();
    // eslint-disable-next-line
  }, [domain]);

  // Re-load the per-user sections (and facets, which switches between
  // global/user mode) whenever the search input changes. Debounced via the
  // input's "Apply" / Enter so we don't fire on every keystroke.
  // (Wired in the input handler below.)

  // Summary numbers
  const totalActivityInWindow = trends.reduce((s, t) => s + (t.total_turns || 0), 0);
  const highCount = facets.filter((f) => f.confidence_tier === "HIGH").length;
  const modCount  = facets.filter((f) => f.confidence_tier === "MODERATE").length;
  const readyCount = activeUsers.filter((u) => u.contact_ready).length;

  const windowLabel = ({
    today: "today",
    "7d":  "last 7 days",
    "30d": "last 30 days",
    "90d": "last 90 days",
    all:   "all-time",
  })[windowId] || windowId;

  return (
    <div className="app-page analytics-body">
      <header className="app-header">

        {/* Row 1: brand + tabs + external nav (single line) */}
        <div className="app-header-row">
          <div className="app-brand">
            <span className="app-brand-name">APE</span>
            <span className="app-brand-dot">/</span>
            <span className="app-brand-page">Analytics</span>
          </div>

          <nav className="app-tabs" aria-label="Analytics sections">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`app-tab ${activeTab === t.id ? "active" : ""}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          <div className="app-actions">
            <Link to="/"      className="app-link">Chat</Link>
            <Link to="/admin" className="app-link">Admin</Link>
            <button
              className="btn-text"
              onClick={() => refresh()}
              disabled={globalLoading}
              title="Re-read aggregates from MongoDB"
            >
              {globalLoading ? "Loading" : "Reload"}
            </button>
            <button
              className="btn-text btn-text-emphasis"
              onClick={() => refresh({ recompute: true })}
              disabled={globalLoading}
              title="Rebuild aggregates from raw turn records"
            >
              Recompute
            </button>
          </div>
        </div>

        {/* Row 2: toolbar — date window + user search + freshness */}
        <div className="app-header-row analytics-toolbar">
          <DateFilter
            value={windowId}
            onChange={(id) => setWindowId(id)}
          />
          <label className="domain-filter" title="Scope all panels to one domain">
            <span className="domain-filter-label">Domain</span>
            <select
              className="domain-filter-select"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            >
              {DOMAIN_OPTIONS.map((d) => (
                <option key={d.id || "all"} value={d.id}>{d.label}</option>
              ))}
            </select>
          </label>
          <UserSearchInput
            value={inspectUser}
            onApply={applyUser}
            onClear={clearUser}
            currentName={profile?.display_name}
            hasUser={hasUser}
            suggestions={activeUsers}
          />
          <span className="analytics-meta">
            {lastRefresh && (
              <span className="last-refresh" title="When aggregates were last fetched">
                {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
            {lastRecompute && (
              <span className="last-recompute" title="When aggregates were last rebuilt">
                · rebuilt {lastRecompute.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </span>
        </div>
      </header>

      <main className="app-main analytics-main">

      {/* ════════════════ OVERVIEW TAB ════════════════ */}
      {activeTab === "overview" && (<>
        {/* Summary tiles */}
        <section className="summary-row">
          <Card
            label={hasUser ? "Cognitive facets (this user)" : "Cognitive facets (all users)"}
            value={facets.length}
            sub={`${highCount} high · ${modCount} moderate`}
            info={<>
              One facet per <strong>(intent, topic)</strong> bandit cell.
              {hasUser
                ? <> This count is for the inspected user only.</>
                : <> This count is aggregated across all users — each facet shows how many distinct users contributed.</>}
              <br/><strong>HIGH</strong> = ≥10 interactions and confidence ≥75.
              <strong> MODERATE</strong> = ≥4 and ≥50. Otherwise LOW.
            </>}
          />
          <Card
            label={`Trending topics (${windowLabel})`}
            value={trends.length}
            sub={`${totalActivityInWindow} turns in window`}
            info={<>
              Top topics by <code>trend_score</code> in the selected window.
              Score = 0.4·volume + 0.3·growth/3 + 0.2·user-density + 0.1·avg_reward.
            </>}
          />
          <Card
            label={`Active customers (${windowLabel})`}
            value={activeUsers.length}
            sub={`${readyCount} contact-ready`}
            accent
            info={<>
              Users with any activity in this window.
              <strong> Contact-ready</strong> = interest_score ≥ 0.7
              AND compliance_eligible AND NOT do_not_contact.
            </>}
          />
          {hasUser ? (
            <Card
              label="Eligible outreach"
              value={offers.filter((o) => o.eligible).length}
              sub={`of ${offers.length} active for this user`}
              info={<>
                Outreach actions where this user passes the three-way gate
                (score ≥ threshold · compliance ok · not DNC).
              </>}
            />
          ) : (
            <Card
              label="Outreach (global)"
              value={platform?.outreach_summary?.eligible_matches ?? 0}
              sub={
                platform?.outreach_summary
                  ? `${platform.outreach_summary.users_with_any_match} users qualify · ${platform.outreach_summary.active_policies} active actions`
                  : "computing…"
              }
              info={<>
                Total <strong>user × outreach</strong> matches across every active user
                in the window — counts how many actionable outreach opportunities exist
                right now. Each match passes all three gates. Sub shows how many distinct
                users qualify for at least one action and how many policies are active.
              </>}
            />
          )}
        </section>

        {/* ===== Platform overview (macro across all users) ===== */}
        {platformErr ? (
          <ErrorBanner endpoint="/analytics/platform-overview" message={platformErr} />
        ) : platform ? (
          <PlatformOverviewCard
            data={platform}
            windowLabel={windowLabel}
            platformDailySeries={platformSeries}
            topicsDailySeries={topicsSeries}
          />
        ) : (
          <div className="empty-state">Loading platform overview…</div>
        )}

        {/* Per-strategy bandit performance for the selected domain scope */}
        <StrategyPerformancePanel
          data={stratPerf}
          error={stratErr}
          domainLabel={(DOMAIN_OPTIONS.find((d) => d.id === domain) || {}).label}
        />
      </>)}

      {/* ════════════════ CONTENT TAB ════════════════ */}
      {activeTab === "content" && (
        <section className="section section-content-quality">
          <div className="section-head">
            <h2>
              Content quality by topic
              <InfoHint width={320}>
                Topics ranked by weighted failure rate from <code>content_correction</code>
                {" "}(×1.0) and <code>reask_same_question</code> (×0.5). Tiers: CRITICAL ≥ 25%,
                HIGH ≥ 12%, MEDIUM ≥ 5%.
              </InfoHint>
            </h2>
          </div>

          <div className="content-quality-stack">
            <RagQualityPanel notify={() => {}} daysOverride={Math.max(1, daysForFilter(windowId))} />
          </div>
        </section>
      )}

      {/* ════════════════ HEALTH TAB ════════════════ */}
      {activeTab === "health" && (
        <CustomerHealthSection windowLabel={windowLabel} days={Math.max(1, daysForFilter(windowId))} />
      )}

      {/* ════════════════ CUSTOMERS TAB ════════════════ */}
      {activeTab === "customers" && (<>
        {/* ===== Active customers (admin outreach) ===== */}
        <section className="section section-outreach">
          <div className="section-head">
            <div>
              <h2>
                Active customers <span className="window-tag">{windowLabel}</span>
                <InfoHint width={340}>
                  One row per user with any activity in the selected window.
                  The <strong>Contact-ready</strong> badge fires only when all three
                  gates pass: <code>interest_score ≥ 0.7</code>, <code>compliance_eligible = true</code>,
                  and <code>do_not_contact = false</code>. Click <strong>Inspect →</strong> on any row
                  to load that user's full profile and facet cards.
                </InfoHint>
              </h2>
              <p className="section-sub">
                Users with any activity in the selected window, ranked by their strongest
                <code> interest_score</code>. The <strong>Contact-ready</strong> badge fires at
                <code> interest_score ≥ 0.7</code>. Outreach decisions must still pass downstream
                consent / compliance.
              </p>
            </div>
          </div>
          {activeErr ? (
            <ErrorBanner endpoint="/analytics/active-users" message={activeErr} />
          ) : (
            <ActiveUsersTable
              rows={activeUsers}
              windowLabel={windowLabel}
              activeHash={inspectUser}
              onInspect={inspectByHash}
            />
          )}
        </section>

        {/* ===== User Cognitive Profile (only when a user is selected) ===== */}
        <section ref={facetsSectionRef}>
          {!hasUser ? (
            <div className="section section-pick-user">
              <div className="pick-user-inner">
                <div className="pick-user-eyebrow">User Cognitive Profile</div>
                <div className="pick-user-headline">Select a user to see their 12-facet profile</div>
                <div className="pick-user-sub">
                  Search at the top, click <strong>Inspect →</strong> on any row in
                  Active customers below, or paste a <code>u_&lt;hash&gt;</code>.
                </div>
              </div>
            </div>
          ) : profileErr ? (
            <ErrorBanner endpoint="/analytics/user-profile" message={profileErr} />
          ) : profile ? (
            <UserProfileCard
              profile={profile}
              userLabel={inspectUser}
              dailyActivity={userSeries}
            />
          ) : (
            <div className="empty-state">Loading cognitive profile…</div>
          )}
        </section>
      </>)}

      {/* ════════════════ COGNITION TAB ════════════════ */}
      {activeTab === "cognition" && (<>
        {/* ===== Cognitive Facets per (intent, topic) ===== */}
        <section className="section section-hero">
          <div className="section-head">
            <div>
              <h2>
                Cognitive facets{" "}
                {hasUser
                  ? <span className="user-pill">{profile?.display_name || inspectUser}</span>
                  : <span className="window-tag">all users</span>}
                <span className="cumulative-tag" title="The bandit learns over time — these cards don't get reset by the date window. Use 'Recompute now' to refresh.">
                  cumulative · window does not apply
                </span>
                <InfoHint width={400}>
                  Per-<code>(intent, topic)</code> bandit cells.
                  The runtime uses <strong>UCB</strong> — selection is
                  <code> argmax(avg_reward + c·√(2·ln N / count))</code>, no α/β involved.
                  The Beta(α,β) <em>curves</em> on each card are a <strong>visualization-only</strong> projection:
                  <code> α = round(count·(avg+1)/2)</code>, <code>β = count − α + 1</code>. Peak position
                  reflects avg_reward; width reflects pull count (more pulls → narrower → more confident).
                  Confidence score blends <strong>volume</strong> (40%),
                  <strong> leader-vs-runner gap</strong> (30%), and <strong>leader strength</strong> (30%).
                </InfoHint>
              </h2>
              <p className="section-sub">
                Each card is a <code>(intent, topic)</code> cell.{" "}
                {hasUser
                  ? "Score circle combines volume, leader-vs-runner gap, and leader strength for this user."
                  : "Bandit state aggregated across every user — each card shows how many users contributed."}
              </p>
            </div>
            {facetsLoad && <span className="loading-tag">Loading…</span>}
          </div>

          {facetsErr ? (
            <ErrorBanner endpoint="/analytics/cognitive-facets" message={facetsErr} />
          ) : facets.length === 0 ? (
            <div className="empty-state">
              {hasUser
                ? <>No cognitive facets yet for <code>{inspectUser}</code>. Send a few <code>/turn</code> requests and rate the responses, then click <strong>Recompute now</strong>.</>
                : <>No facets across the user base yet. The bandit_state collection is empty or has fewer than 2 pulls per cell.</>}
            </div>
          ) : (
            <div className="facet-grid">
              {facets.map((f) => (
                <CognitiveFacetCard
                  key={`${f.domain}#${f.intent}#${f.topic}`}
                  facet={f}
                  onInspectUser={inspectByHash}
                />
              ))}
            </div>
          )}
        </section>
      </>)}

      {/* ════════════════ OVERVIEW TAB (continued — trending topics table) ════════════════ */}
      {activeTab === "overview" && (
        /* ===== Topic trends ===== */
        <section className="section">
          <div className="section-head">
            <h2>
              Trending topics <span className="window-tag">{windowLabel}</span>
              <InfoHint width={340}>
                Top topics by <code>trend_score</code> in the window.
                Formula: <code>0.4·normalized_volume + 0.3·growth/3 + 0.2·user_density + 0.1·avg_reward</code>.
                Growth compares today's volume to the prior 7-day average — values &gt;1× mean accelerating attention.
              </InfoHint>
            </h2>
          </div>
          <p className="section-sub">
            Top topics by <code>trend_score</code> = 0.4×normalized_volume + 0.3×growth/3 + 0.2×density + 0.1×avg_reward.
          </p>
          {trendsErr ? (
            <ErrorBanner endpoint="/analytics/trends" message={trendsErr} />
          ) : trends.length === 0 ? (
            <div className="empty-state">No topic trends in this window.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Date</th>
                  <th className="num">Turns</th>
                  <th className="num">Users</th>
                  <th className="num">Avg reward</th>
                  <th className="num">Growth</th>
                  <th className="num">Trend</th>
                </tr>
              </thead>
              <tbody>
                {trends.map((t) => (
                  <tr key={`${t.date}#${t.domain}#${t.topic}`}>
                    <td><span className="topic-chip">{t.topic}</span></td>
                    <td>{t.date}{t.is_today && <small className="today-tag">● today</small>}</td>
                    <td className="num">{t.total_turns}</td>
                    <td className="num">{t.unique_users}</td>
                    <td className={`num ${rewardClass(t.avg_reward)}`}>{fmt(t.avg_reward)}</td>
                    <td className="num">{fmt(t.growth_ratio)}x</td>
                    <td className="num"><strong>{fmt(t.trend_score)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* ════════════════ CUSTOMERS TAB (continued — per-user detail sections) ════════════════ */}
      {activeTab === "customers" && hasUser && (<>
        {/* ===== User interests (per-user only) ===== */}
        <section className="section">
          <div className="section-head">
            <h2>
              Topic interest for <code className="user-pill">{profile?.display_name || inspectUser}</code>
              <span className="cumulative-tag" title="Interest scores are computed from all historical activity, with recency built in via exp-decay. The window selector doesn't apply.">
                cumulative · window does not apply
              </span>
              <InfoHint width={340}>
                Per-topic interest score for this user, with the four contributing sub-scores visible.
                <strong> Frequency</strong> = how often vs their top topic.
                <strong> Recency</strong> = exp(-days_since_last/7).
                <strong> Engagement</strong> = avg reward.
                <strong> Followup</strong> = 7d/30d ratio.
                Composite = 0.40·F + 0.25·R + 0.25·E + 0.10·U.
              </InfoHint>
            </h2>
          </div>
          <p className="section-sub">
            <code>interest_score</code> = 0.40×frequency + 0.25×recency + 0.25×engagement + 0.10×followup_depth.
          </p>
          {interestsErr ? (
            <ErrorBanner endpoint="/analytics/user-interests" message={interestsErr} />
          ) : interests.length === 0 ? (
            <div className="empty-state">No interest data for this user yet.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th className="num">7d</th>
                  <th className="num">30d</th>
                  <th className="num">Freq</th>
                  <th className="num">Recency</th>
                  <th className="num">Engage</th>
                  <th className="num">Followup</th>
                  <th className="num">Interest</th>
                </tr>
              </thead>
              <tbody>
                {interests.map((u) => (
                  <tr key={`${u.domain}#${u.topic}`}>
                    <td><span className="topic-chip">{u.topic}</span></td>
                    <td className="num">{u.count_7d}</td>
                    <td className="num">{u.count_30d}</td>
                    <td className="num">{fmt(u.frequency_score)}</td>
                    <td className="num">{fmt(u.recency_score)}</td>
                    <td className={`num ${rewardClass(u.engagement_score)}`}>{fmt(u.engagement_score)}</td>
                    <td className="num">{fmt(u.followup_depth_score)}</td>
                    <td className="num">
                      <strong>{fmt(u.interest_score)}</strong>
                      <ScoreBar value={u.interest_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* ===== Recommended outreach (per-user only) ===== */}
        <section className="section">
          <div className="section-head">
            <h2>
              Recommended outreach
              <InfoHint width={360}>
                Next-best actions for this user. Each row's <strong>User score</strong> is the
                interest_score reweighted by that outreach action's per-action weights (set
                in Admin → Outreach). <strong>Eligible</strong> requires all three gates to pass:
                score ≥ threshold, compliance_eligible, and not do_not_contact. The score
                breakdown under the number shows each component's contribution.
              </InfoHint>
            </h2>
          </div>
          <p className="section-sub">
            Next-best actions for <code className="user-pill">{profile?.display_name || inspectUser}</code> —
            picked from active outreach rows based on this user's interest scores and the
            three-way eligibility gate (score · compliance · do-not-contact).
          </p>
          {offersErr ? (
            <ErrorBanner endpoint={`/analytics/offers/${inspectUser}`} message={offersErr} />
          ) : offers.length === 0 ? (
            <div className="empty-state">
              No outreach actions defined yet. Add one via <strong>Admin → Outreach</strong>.
            </div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Outreach</th>
                  <th>Topic</th>
                  <th className="num">User score</th>
                  <th className="num">Threshold</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {offers.map((o) => (
                  <tr key={o.offer_type + o.topic}>
                    <td>
                      <strong>{o.offer_type}</strong>
                      {o.description && <div className="offer-desc">{o.description}</div>}
                    </td>
                    <td><span className="topic-chip">{o.topic}</span></td>
                    <td className={`num ${rewardClass(o.interest_score)}`}>
                      <strong>{fmt(o.interest_score)}</strong>
                      {o.score_breakdown && <ScoreBreakdown breakdown={o.score_breakdown} weights={o.weights} />}
                    </td>
                    <td className="num">{fmt(o.min_interest_score)}</td>
                    <td>
                      {o.eligible
                        ? <span className="eligible-yes">● Eligible</span>
                        : <span className="eligible-no">○ Not eligible</span>}
                    </td>
                    <td className="offer-reason">{o.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </>)}

      {/* ════════════════ CUSTOMERS TAB — empty state when no user picked ════════════════ */}
      {activeTab === "customers" && !hasUser && (
        <section className="section section-pick-user">
          <div className="pick-user-inner">
            <div className="pick-user-eyebrow">Customers</div>
            <div className="pick-user-headline">Click "Inspect" on a user above for their detail view</div>
            <div className="pick-user-sub">
              The Active customers table at the top is global; per-user
              profile / topic interest / outreach matches appear here once
              you pick someone.
            </div>
          </div>
        </section>
      )}

        {/* ===== Privacy footer ===== */}
        <section className="section privacy-section">
          <h2>Privacy</h2>
          <p className="section-sub" style={{ marginBottom: 0 }}>
            Raw queries are <strong>never stored</strong> in the analytics layer — only normalized
            topic, intent, timestamps, signals, and rewards. <code>user_id</code> is hashed to
            <code> user_id_hash</code> before persistence; the Active-customers list surfaces hashes
            so they can be matched against your CRM. The "Contact-ready" badge is a candidate
            filter only — outreach should still pass your full compliance pipeline
            (do_not_contact, jurisdictional rules, etc.).
          </p>
        </section>
      </main>
    </div>
  );
}

// ---------- Helpers ----------

function Card({ label, value, sub, accent = false, info = null }) {
  return (
    <div className={`summary-card ${accent ? "accent" : ""}`}>
      <div className="label">
        {label}
        {info && <InfoHint width={300}>{info}</InfoHint>}
      </div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

function ErrorBanner({ endpoint, message }) {
  return (
    <div className="error-banner">
      <strong>Failed to load</strong> <code>{endpoint}</code>
      <div className="error-detail">{message}</div>
    </div>
  );
}

function ScoreBar({ value }) {
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  return (
    <div className="score-bar-wrap">
      <div
        className="score-bar-fill"
        style={{
          width: `${v * 100}%`,
          background: v >= 0.8 ? "#5fd0a4" : v >= 0.5 ? "#7aa6ff" : "#8e94a8",
        }}
      />
    </div>
  );
}

function rewardClass(v) {
  if (v == null || Number(v) === 0) return "zero";
  const x = Number(v);
  if (x >= 0.7) return "pos";
  if (x <= 0.3) return "neg";
  return "";
}

function fmt(v) {
  if (v == null) return "—";
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return Number.isInteger(x) ? x.toString() : x.toFixed(2);
}

function shortHash(h) {
  if (!h) return "";
  return h.length > 14 ? `${h.slice(0, 14)}…` : h;
}

/**
 * UserSearchInput — single source of truth for who's being inspected.
 *   Empty → global view. Typed → that user. Enter or "Apply" commits.
 *   "×" button clears back to global.
 *
 * AUTOCOMPLETE: as the admin types, matching users from the active-customers
 * roster appear as a dropdown. Match strategy:
 *   - case-insensitive substring on display_name
 *   - prefix match on user_id_hash
 *   - top topic shown as a hint
 * Keyboard: ↑ ↓ to move, Enter to select, Esc to close, click anywhere outside to dismiss.
 */
function UserSearchInput({ value, onApply, onClear, currentName, hasUser, suggestions = [] }) {
  const [draft, setDraft]       = useState(value || "");
  const [open, setOpen]         = useState(false);
  const [highlight, setHighlight] = useState(0);
  const wrapRef = useRef(null);

  // Keep local draft in sync if the parent changes inspectUser via "Inspect →"
  useEffect(() => { setDraft(value || ""); }, [value]);

  // Click outside → close dropdown
  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  // Filtered matches — only when the user is typing something
  const matches = useMemo(() => {
    const q = draft.trim().toLowerCase();
    if (!q) return [];
    const seen = new Set();
    const out = [];
    for (const u of suggestions) {
      const name = (u.display_name || "").toLowerCase();
      const hash = (u.user_id_hash || "").toLowerCase();
      const matchName = name.includes(q);
      const matchHash = hash.startsWith(q) || hash.includes(q.replace(/^u_/, ""));
      if (matchName || matchHash) {
        const key = u.user_id_hash || u.display_name;
        if (!seen.has(key)) {
          seen.add(key);
          out.push(u);
          if (out.length >= 8) break;
        }
      }
    }
    return out;
  }, [draft, suggestions]);

  const dirty = draft.trim() !== (value || "").trim();
  const showDropdown = open && matches.length > 0 && dirty;

  // Reset highlight when the matches list changes
  useEffect(() => { setHighlight(0); }, [matches.length]);

  function pick(user) {
    onApply(user.user_id_hash);
    setOpen(false);
  }

  function commit() {
    if (showDropdown && matches[highlight]) {
      pick(matches[highlight]);
    } else {
      onApply(draft.trim());
      setOpen(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "ArrowDown" && showDropdown) {
      e.preventDefault();
      setHighlight((h) => (h + 1) % matches.length);
    } else if (e.key === "ArrowUp" && showDropdown) {
      e.preventDefault();
      setHighlight((h) => (h - 1 + matches.length) % matches.length);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className={`user-search ${hasUser ? "has-user" : "is-global"}`} ref={wrapRef}>
      <span className="user-search-icon" aria-hidden>🔍</span>
      <input
        type="text"
        className="user-search-input"
        value={draft}
        onChange={(e) => { setDraft(e.target.value); setOpen(true); }}
        onFocus={() => { if (draft.trim()) setOpen(true); }}
        placeholder={hasUser ? "" : "Type a name (e.g. Alex) · or leave blank for all users"}
        onKeyDown={onKeyDown}
        autoComplete="off"
        spellCheck={false}
      />
      {currentName && hasUser && !dirty && (
        <span className="user-search-name">{currentName}</span>
      )}
      {dirty && (
        <button className="user-search-apply" onClick={commit}>Apply</button>
      )}
      {hasUser && !dirty && (
        <button className="user-search-clear" onClick={onClear} title="Switch back to all-users view">
          ×
        </button>
      )}
      <span className="user-search-scope">
        {hasUser ? "single user" : "all users"}
      </span>

      {showDropdown && (
        <ul className="user-search-dropdown" role="listbox">
          {matches.map((u, i) => (
            <li
              key={u.user_id_hash}
              role="option"
              aria-selected={i === highlight}
              className={`user-search-option ${i === highlight ? "active" : ""}`}
              onMouseEnter={() => setHighlight(i)}
              onMouseDown={(e) => { e.preventDefault(); pick(u); }}
            >
              <span className="opt-name">{u.display_name || shortHash(u.user_id_hash)}</span>
              <code className="opt-hash">{shortHash(u.user_id_hash)}</code>
              {u.top_topic && (
                <span className="opt-topic">top: {u.top_topic}</span>
              )}
              {u.contact_ready && (
                <span className="opt-ready" title="Contact-ready in current window">●</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Inline breakdown of an outreach action's interest_score into its four components. */
function ScoreBreakdown({ breakdown, weights }) {
  if (!breakdown) return null;
  const parts = [
    { key: "frequency",  label: "freq",   contrib: breakdown.frequency,  weight: weights?.frequency },
    { key: "recency",    label: "rec",    contrib: breakdown.recency,    weight: weights?.recency },
    { key: "engagement", label: "eng",    contrib: breakdown.engagement, weight: weights?.engagement },
    { key: "followup",   label: "foll",   contrib: breakdown.followup,   weight: weights?.followup },
  ];
  return (
    <div
      className="score-breakdown"
      title={parts.map((p) => `${p.label}: ${(p.contrib).toFixed(3)} (weight ${Math.round((p.weight || 0) * 100)}%)`).join("\n")}
    >
      {parts.map((p) => (
        <span key={p.key} className="bd-part">
          {p.label} <strong>{p.contrib.toFixed(2)}</strong>
        </span>
      ))}
    </div>
  );
}
