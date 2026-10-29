import React, { useState, useEffect } from 'react';
import { BrandLogo } from './components/BrandLogo';
import { AuthView } from './components/AuthView';
import { SupportWorkspace } from './components/SupportWorkspace';
import { BenchmarksView } from './components/BenchmarksView';
import { OperationsView } from './components/OperationsView';
import { SettingsDrawer } from './components/SettingsDrawer';
import {
  INITIAL_SESSIONS,
  INITIAL_TRACES,
  ConversationSession,
  TraceLogEntry,
  apiClient,
} from './services/apiClient';

type ActiveTab = 'workspace' | 'benchmarks' | 'operations';

export function App() {
  // Initialize with a valid in-memory JWT token so the default Support Workspace is immediately live,
  // while supporting full Sign Out -> Authentication View -> Sign In JWT flow.
  const [jwtToken, setJwtToken] = useState<string | null>(() => {
    const initialToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlbmctb3BzQHRlY2htYXJ0LmludGVybmFsIn0.tm_v14';
    apiClient.setToken(initialToken);
    return initialToken;
  });

  const [userProfile, setUserProfile] = useState({
    name: 'Engineering Ops',
    email: 'eng-ops@techmart.internal',
    role: 'Tier-3 Lead Eng',
    initials: 'EO',
  });

  const [activeTab, setActiveTab] = useState<ActiveTab>('workspace');
  const [workspaceSubMode, setWorkspaceSubMode] = useState<'chat' | 'overview'>('chat');
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [sessions, setSessions] = useState<ConversationSession[]>(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>(INITIAL_SESSIONS[0].id);
  const [traces, setTraces] = useState<TraceLogEntry[]>(INITIAL_TRACES);

  const [activeRouter, setActiveRouter] = useState<string>('TF-IDF + Logistic Regression');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [strictGuardrails, setStrictGuardrails] = useState<boolean>(true);
  const [themeMode, setThemeMode] = useState<'light' | 'dark' | 'system'>('light');

  const [docsModalOpen, setDocsModalOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [patchDeployedToast, setPatchDeployedToast] = useState(false);

  // Sync URL hash if present
  useEffect(() => {
    const handleHash = () => {
      const h = window.location.hash.replace('#', '');
      if (h === 'login' || h === 'auth') {
        apiClient.setToken(null);
        setJwtToken(null);
      } else if (h === 'benchmarks') {
        setActiveTab('benchmarks');
      } else if (h === 'operations') {
        setActiveTab('operations');
      } else if (h === 'settings') {
        setSettingsOpen(true);
      } else if (h === 'overview') {
        setActiveTab('workspace');
        setWorkspaceSubMode('overview');
      } else if (h === 'workspace') {
        setActiveTab('workspace');
        setWorkspaceSubMode('chat');
      }
    };
    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  // Periodic background trace telemetry when autoRefresh (10s) is active
  useEffect(() => {
    if (!autoRefresh || !jwtToken) return;
    const interval = setInterval(() => {
      const now = new Date();
      const preciseTime = `${now.toTimeString().split(' ')[0]}.${String(
        now.getMilliseconds()
      ).padStart(3, '0')}`;
      const shortId = Math.random().toString(16).substring(2, 6);
      const sampleEndpoints = [
        {
          ep: '/v1/chat/completions',
          router: 'TF-IDF + Logistic' as const,
          spec: 'Returns Specialist',
          lat: 168 + Math.floor(Math.random() * 40),
          code: 200 as const,
          text: '200 OK',
        },
        {
          ep: '/v1/chat/completions',
          router: 'LLM Structured Output' as const,
          spec: 'Billing Support & Escrow',
          lat: 315 + Math.floor(Math.random() * 55),
          code: 200 as const,
          text: '200 OK',
        },
      ];
      const pick = sampleEndpoints[Math.floor(Math.random() * sampleEndpoints.length)];
      setTraces((prev) => [
        {
          id: `tr-auto-${Date.now()}`,
          timestamp: preciseTime,
          traceId: `req_98a${shortId}`,
          endpoint: pick.ep,
          routerUsed: pick.router,
          specialist: pick.spec,
          latencyMs: pick.lat,
          statusCode: pick.code,
          statusText: pick.text,
          clientIp: '10.240.12.8',
          payloadPreview: JSON.stringify({
            heartbeat: 'auto_refresh_10s',
            router: pick.router,
            specialist: pick.spec,
            status: pick.code,
          }),
        },
        ...prev.slice(0, 49),
      ]);
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, jwtToken]);

  const handleSignOut = () => {
    apiClient.setToken(null);
    setJwtToken(null);
    setSettingsOpen(false);
  };

  const handleAuthenticated = (payload: {
    token: string;
    user: { name: string; email: string; role: string; initials: string };
  }) => {
    apiClient.setToken(payload.token);
    setJwtToken(payload.token);
    setUserProfile(payload.user);
    if (window.location.hash === '#login' || window.location.hash === '#auth') {
      window.history.replaceState(null, '', '#workspace');
    }
  };

  const handleDeployPatch = () => {
    setPatchDeployedToast(true);
    setTimeout(() => setPatchDeployedToast(false), 2500);
  };

  const handleExportTelemetry = () => {
    const blob = new Blob([JSON.stringify(traces, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'techmart_gateway_traces_v1.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Render Authentication View when signed out
  if (!jwtToken) {
    return <AuthView sessionExpiredNotice={true} onAuthenticated={handleAuthenticated} />;
  }

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  return (
    <div
      className={`h-screen w-full overflow-hidden flex bg-background text-on-surface antialiased ${
        themeMode === 'dark' ? 'invert hue-rotate-180' : ''
      }`}
    >
      {/* ======================================================== */}
      {/* MASTER NAVIGATION SHELL: Fixed Left Sidebar              */}
      {/* ======================================================== */}
      <aside className="fixed top-0 bottom-0 left-0 w-60 h-screen flex flex-col justify-between p-4 z-40 bg-surface-container-lowest border-r border-outline-variant select-none">
        {/* Sidebar Header & Primary Navigation */}
        <div className="flex flex-col gap-5">
          {/* Brand & Tagline */}
          <div className="flex items-center gap-3 px-1 py-1">
            <BrandLogo className="w-8 h-8" />
            <div className="flex flex-col min-w-0">
              <span className="text-[15px] font-bold text-on-surface truncate leading-tight tracking-tight">
                TechMart Support AI
              </span>
              <span className="text-[11px] text-on-surface-variant truncate">
                Intelligent Support. Grounded Answers.
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav aria-label="Main Navigation" className="flex flex-col gap-1">
            {/* Tab 1: Support Workspace */}
            <button
              type="button"
              onClick={() => {
                setActiveTab('workspace');
                setSettingsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] transition-all duration-150 cursor-pointer whitespace-nowrap ${
                activeTab === 'workspace' && !settingsOpen
                  ? 'text-primary bg-surface-container-low font-semibold'
                  : 'text-on-surface-variant font-normal hover:text-on-surface hover:bg-surface-container-low'
              }`}
            >
              <span
                className={`material-symbols-outlined ${
                  activeTab === 'workspace' && !settingsOpen
                    ? 'text-primary material-symbols-filled'
                    : ''
                }`}
              >
                support_agent
              </span>
              <span>Support Workspace</span>
            </button>

            {/* Tab 2: RAG & Router Benchmarks */}
            <button
              type="button"
              onClick={() => {
                setActiveTab('benchmarks');
                setSettingsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] transition-all duration-150 cursor-pointer whitespace-nowrap ${
                activeTab === 'benchmarks' && !settingsOpen
                  ? 'text-primary bg-surface-container-low font-semibold'
                  : 'text-on-surface-variant font-normal hover:text-on-surface hover:bg-surface-container-low'
              }`}
            >
              <span
                className={`material-symbols-outlined ${
                  activeTab === 'benchmarks' && !settingsOpen
                    ? 'text-primary material-symbols-filled'
                    : ''
                }`}
              >
                query_stats
              </span>
              <span className="truncate">RAG &amp; Router Benchmarks</span>
            </button>

            {/* Tab 3: Reliability & Operations */}
            <button
              type="button"
              onClick={() => {
                setActiveTab('operations');
                setSettingsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] transition-all duration-150 cursor-pointer whitespace-nowrap ${
                activeTab === 'operations' && !settingsOpen
                  ? 'text-primary bg-surface-container-low font-semibold'
                  : 'text-on-surface-variant font-normal hover:text-on-surface hover:bg-surface-container-low'
              }`}
            >
              <span
                className={`material-symbols-outlined ${
                  activeTab === 'operations' && !settingsOpen
                    ? 'text-primary material-symbols-filled'
                    : ''
                }`}
              >
                monitoring
              </span>
              <span className="truncate">Reliability &amp; Operations</span>
            </button>

            {/* Tab 4: Settings (Slide-over drawer) */}
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] transition-all duration-150 cursor-pointer whitespace-nowrap ${
                settingsOpen
                  ? 'text-primary bg-surface-container-low font-semibold'
                  : 'text-on-surface-variant font-normal hover:text-on-surface hover:bg-surface-container-low'
              }`}
            >
              <span
                className={`material-symbols-outlined ${
                  settingsOpen ? 'text-primary material-symbols-filled' : ''
                }`}
              >
                settings
              </span>
              <span>Settings</span>
            </button>
          </nav>
        </div>

        {/* Bottom User Profile & Deploy Action */}
        <div className="pt-3 border-t border-outline-variant/60 space-y-2.5">
          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-container-low transition-colors">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary flex items-center justify-center text-[13px] font-semibold shrink-0">
                {userProfile.initials}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] font-semibold text-on-surface truncate leading-tight">
                  {userProfile.name}
                </span>
                <span className="text-[11px] text-on-surface-variant truncate">
                  {userProfile.email}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="text-on-surface-variant hover:text-error p-1 rounded transition-colors cursor-pointer"
              title="Sign Out to Authentication Gateway"
            >
              <span className="material-symbols-outlined text-[18px]">logout</span>
            </button>
          </div>

          {activeTab === 'operations' && (
            <button
              type="button"
              onClick={handleDeployPatch}
              className="w-full h-9 px-3 rounded-lg bg-primary hover:bg-[#4338ca] text-on-primary text-[12px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors duration-150 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">bolt</span>
              <span>{patchDeployedToast ? 'Patch v1.4.13 Deployed' : 'Deploy Patch'}</span>
            </button>
          )}
        </div>
      </aside>

      {/* ======================================================== */}
      {/* RIGHT MAIN STAGE (Top Utility Bar + Active Tab Viewport) */}
      {/* ======================================================== */}
      <div className="pl-60 w-full flex flex-col h-screen overflow-hidden">
        {/* Top Utility Bar */}
        <header className="h-14 flex items-center justify-between px-6 w-full bg-surface-container-lowest border-b border-outline-variant shrink-0 z-30 select-none">
          {/* Left Breadcrumb Trail */}
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] min-w-0">
            <span className="text-on-surface-variant font-medium truncate">
              TechMart Support AI
            </span>
            <span className="text-outline-variant">/</span>
            {activeTab === 'workspace' && (
              <>
                <button
                  type="button"
                  onClick={() => setWorkspaceSubMode('overview')}
                  className="text-on-surface-variant hover:text-on-surface font-medium cursor-pointer"
                >
                  Workspace
                </button>
                <span className="text-outline-variant">/</span>
                <span className="text-on-surface font-semibold truncate">
                  {workspaceSubMode === 'overview'
                    ? 'Overview'
                    : `Active Session ${activeSession.sessionCode}`}
                </span>
              </>
            )}
            {activeTab === 'benchmarks' && (
              <>
                <span className="text-on-surface font-semibold truncate">
                  RAG &amp; Router Benchmarks
                </span>
                <span className="text-outline-variant">/</span>
                <span className="text-[11px] font-medium text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded border border-outline-variant">
                  Evaluation Suite v2.4
                </span>
              </>
            )}
            {activeTab === 'operations' && (
              <>
                <span className="text-on-surface-variant font-medium truncate">
                  Reliability &amp; Operations
                </span>
                <span className="text-outline-variant">/</span>
                <span className="text-on-surface font-semibold">Infra Telemetry</span>
              </>
            )}
          </nav>

          {/* Right Grouped Utilities */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Live System Operational Pill */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[12px] font-medium">
              <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
              <span>System Operational</span>
            </div>

            {/* Active /v1 Namespace Badge */}
            <span className="px-2 py-0.5 rounded bg-surface-container-low text-on-surface-variant font-mono text-[12px] font-semibold border border-outline-variant">
              /v1
            </span>

            {activeTab === 'operations' && (
              <div className="hidden lg:flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleExportTelemetry}
                  className="h-8 px-2.5 rounded-lg border border-outline-variant/60 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                    file_download
                  </span>
                  <span>Export Telemetry</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAutoRefresh((prev) => !prev)}
                  className="h-8 px-2.5 rounded-lg border border-outline-variant/60 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span
                    className={`material-symbols-outlined text-[16px] text-primary ${
                      autoRefresh ? 'animate-spin' : ''
                    }`}
                    style={{ animationDuration: '9s' }}
                  >
                    sync
                  </span>
                  <span>Auto-refresh ({autoRefresh ? '10s' : 'Off'})</span>
                </button>
              </div>
            )}

            <div className="h-4 w-px bg-outline-variant mx-0.5"></div>

            {/* Trailing Actions */}
            <button
              type="button"
              onClick={() => setDocsModalOpen(true)}
              className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer"
              title="Knowledge Base & /v1 API Documentation"
            >
              <span className="material-symbols-outlined">menu_book</span>
            </button>

            <div className="relative">
              <button
                type="button"
                onClick={() => setNotificationsOpen((prev) => !prev)}
                className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg transition-colors relative cursor-pointer"
                title="System Notifications"
              >
                <span className="material-symbols-outlined">notifications</span>
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full"></span>
              </button>

              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-lg p-3 z-50 space-y-2">
                  <div className="flex items-center justify-between border-b border-outline-variant/50 pb-2">
                    <span className="text-[12px] font-semibold text-on-surface">
                      Gateway Telemetry Alerts
                    </span>
                    <button
                      type="button"
                      onClick={() => setNotificationsOpen(false)}
                      className="text-[11px] text-primary hover:underline cursor-pointer"
                    >
                      Dismiss
                    </button>
                  </div>
                  <div className="text-[12px] text-on-surface-variant space-y-1.5">
                    <div className="p-2 rounded bg-surface-container-low">
                      <span className="font-semibold text-on-surface block">
                        FAISS Index KB-v2.4 Synced
                      </span>
                      <span>78,450 vectors warm-cached in us-east-1 (14.2ms p99).</span>
                    </div>
                    <div className="p-2 rounded bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E]">
                      <span className="font-semibold block">Ticket #ESC-4029 Dispatched</span>
                      <span>Autonomous boundary guardrail triggered on #sess-8941.</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={handleSignOut}
              className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-outline-variant/70 hover:bg-surface-container-low text-[12px] font-medium text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
              title="View Authentication Login Screen"
            >
              <span className="material-symbols-outlined text-[15px]">lock</span>
              <span>Auth Screen</span>
            </button>
          </div>
        </header>

        {/* Active View Content */}
        {activeTab === 'workspace' && (
          <SupportWorkspace
            sessions={sessions}
            activeSessionId={activeSessionId}
            activeRouter={activeRouter}
            strictGuardrails={strictGuardrails}
            workspaceSubMode={workspaceSubMode}
            onSelectSession={setActiveSessionId}
            onUpdateSessions={setSessions}
            onAppendTraceLog={(log) => setTraces((prev) => [log, ...prev])}
            onToggleSubMode={setWorkspaceSubMode}
            onNavigateTab={setActiveTab}
          />
        )}

        {activeTab === 'benchmarks' && (
          <BenchmarksView
            activeRouter={activeRouter}
            onSelectActiveRouter={(routerName) => setActiveRouter(routerName)}
          />
        )}

        {activeTab === 'operations' && (
          <OperationsView
            traces={traces}
            onAppendTrace={(log) => setTraces((prev) => [log, ...prev])}
          />
        )}
      </div>

      {/* Slide-over Settings Drawer */}
      <SettingsDrawer
        isOpen={settingsOpen}
        activeRouter={activeRouter}
        autoRefresh={autoRefresh}
        strictGuardrails={strictGuardrails}
        themeMode={themeMode}
        onClose={() => setSettingsOpen(false)}
        onNavigateToBenchmarks={() => setActiveTab('benchmarks')}
        onToggleAutoRefresh={setAutoRefresh}
        onToggleStrictGuardrails={setStrictGuardrails}
        onChangeThemeMode={setThemeMode}
        onSignOut={handleSignOut}
      />

      {/* API Docs & Knowledge Base Modal */}
      {docsModalOpen && (
        <div className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-xl w-full p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant pb-3">
              <h3 className="text-[16px] font-semibold text-on-surface">
                TechMart Knowledge Base &amp; /v1 API Adapter
              </h3>
              <button
                type="button"
                onClick={() => setDocsModalOpen(false)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="space-y-2 text-[13px] text-on-surface-variant">
              <p>
                Active client adapter targets <code className="font-mono text-primary">/v1</code>{' '}
                endpoints with automatic deterministic fallback when offline:
              </p>
              <ul className="space-y-1.5 font-mono text-[12px] bg-surface-container-low p-3 rounded-lg border border-outline-variant/50 text-on-surface">
                <li>• POST /v1/auth/login — JWT session authentication</li>
                <li>• POST /v1/chat — Semantic routing &amp; FAISS grounded generation</li>
                <li>• GET /v1/health — Gateway, FAISS &amp; MongoDB health telemetry</li>
                <li>• GET /v1/evaluation/summary — Retrieval &amp; router benchmark suite</li>
              </ul>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setDocsModalOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-primary-container text-on-primary text-[13px] font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
