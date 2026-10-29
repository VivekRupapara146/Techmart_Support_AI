import React, { useState, useEffect } from 'react';

interface SettingsDrawerProps {
  isOpen: boolean;
  activeRouter: string;
  autoRefresh: boolean;
  strictGuardrails: boolean;
  themeMode: 'light' | 'dark' | 'system';
  onClose: () => void;
  onNavigateToBenchmarks: () => void;
  onToggleAutoRefresh: (val: boolean) => void;
  onToggleStrictGuardrails: (val: boolean) => void;
  onChangeThemeMode: (mode: 'light' | 'dark' | 'system') => void;
  onSignOut: () => void;
}

export const SettingsDrawer: React.FC<SettingsDrawerProps> = ({
  isOpen,
  activeRouter,
  autoRefresh,
  strictGuardrails,
  themeMode,
  onClose,
  onNavigateToBenchmarks,
  onToggleAutoRefresh,
  onToggleStrictGuardrails,
  onChangeThemeMode,
  onSignOut,
}) => {
  const [tokenCopied, setTokenCopied] = useState(false);
  const [showSwaggerModal, setShowSwaggerModal] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopyToken = () => {
    navigator.clipboard?.writeText('tm_live_98a7df1c4b8e20194857a6f31');
    setTokenCopied(true);
    setTimeout(() => setTokenCopied(false), 1800);
  };

  return (
    <>
      {/* Accessible Backdrop Overlay */}
      <div
        aria-label="Dismiss drawer"
        onClick={onClose}
        className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-40 transition-opacity duration-200"
      ></div>

      {/* Slide-over Drawer (Right Side, 460px) */}
      <aside
        aria-labelledby="drawer-title"
        aria-modal="true"
        role="dialog"
        className="fixed top-0 right-0 h-full w-[460px] max-w-full bg-surface-container-lowest shadow-2xl z-50 flex flex-col border-l border-outline-variant/40 transition-transform duration-200 ease-out"
      >
        {/* Drawer Header */}
        <div className="px-6 py-5 border-b border-outline-variant/30 bg-surface-container-lowest flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-surface-container-low text-primary border border-outline-variant/30 mt-0.5">
              <span className="material-symbols-outlined text-[22px]">tune</span>
            </div>
            <div>
              <h2 className="text-[16px] font-semibold text-on-surface" id="drawer-title">
                Settings &amp; Configuration
              </h2>
              <p className="text-[13px] text-on-surface-variant mt-0.5">
                Environment, routing policies, and session preferences.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded border border-outline-variant/40 bg-surface-container-low text-outline">
              ESC
            </span>
            <button
              aria-label="Close drawer"
              onClick={onClose}
              className="p-1 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container-low transition-colors cursor-pointer"
              type="button"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>
        </div>

        {/* Drawer Body: Scrollable Sections */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-7 custom-scrollbar">
          {/* SECTION 1: Active Router Configuration */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <h3 className="text-[11px] text-outline uppercase tracking-wider font-semibold">
                ROUTER ARCHITECTURE
              </h3>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onNavigateToBenchmarks();
                }}
                className="text-[11px] text-primary font-semibold hover:underline cursor-pointer"
              >
                Benchmarks →
              </button>
            </div>

            <div className="rounded-lg border border-outline-variant/40 bg-surface p-4 shadow-xs">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[14px] text-on-surface font-semibold">{activeRouter}</p>
                  <p className="text-[13px] text-on-surface-variant mt-0.5">
                    Dual-stage deterministic intent classifier
                  </p>
                </div>
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-semibold shrink-0">
                  <span>Active Production</span>
                </div>
              </div>

              {/* Monospace Specs Matrix */}
              <div className="mt-4 pt-3 border-t border-outline-variant/30 grid grid-cols-2 gap-3 text-[13px] tabular-nums">
                <div className="bg-surface-container-lowest p-2.5 rounded border border-outline-variant/20">
                  <span className="text-[11px] font-semibold text-outline block">Avg Latency</span>
                  <span className="font-mono text-on-surface font-semibold text-[14px]">
                    {activeRouter.includes('LLM')
                      ? '320ms avg'
                      : activeRouter.includes('Rule')
                      ? '4ms avg'
                      : '42ms avg'}
                  </span>
                </div>
                <div className="bg-surface-container-lowest p-2.5 rounded border border-outline-variant/20">
                  <span className="text-[11px] font-semibold text-outline block">
                    Macro-F1 Score
                  </span>
                  <span className="font-mono text-on-surface font-semibold text-[14px]">
                    {activeRouter.includes('LLM')
                      ? '0.958'
                      : activeRouter.includes('Rule')
                      ? '0.762'
                      : '0.941'}
                  </span>
                </div>
                <div className="bg-surface-container-lowest p-2.5 rounded border border-outline-variant/20">
                  <span className="text-[11px] font-semibold text-outline block">
                    Inference Cost
                  </span>
                  <span className="font-mono text-emerald-700 font-semibold text-[14px]">
                    {activeRouter.includes('LLM') ? '$0.35 / 1k' : '$0.00 / 1k'}
                  </span>
                </div>
                <div className="bg-surface-container-lowest p-2.5 rounded border border-outline-variant/20">
                  <span className="text-[11px] font-semibold text-outline block">
                    Model Checkpoint
                  </span>
                  <span className="font-mono text-primary truncate block text-[13px] font-medium">
                    tfidf_router_v2.bin
                  </span>
                </div>
              </div>

              <div className="mt-3.5 p-2.5 bg-surface-container-low rounded border border-outline-variant/40">
                <p className="text-[12px] text-on-surface-variant">
                  <strong className="font-semibold text-on-surface">Live Routing Note:</strong>{' '}
                  Router strategies can be hot-swapped in the RAG &amp; Router Benchmarks suite.
                </p>
              </div>
            </div>
          </div>

          {/* SECTION 2: API Namespace & Gateway Documentation */}
          <div>
            <h3 className="text-[11px] text-outline uppercase tracking-wider font-semibold mb-2.5">
              API NAMESPACE &amp; GATEWAY
            </h3>
            <div className="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 space-y-3.5 shadow-xs">
              <button
                type="button"
                onClick={() => setShowSwaggerModal(true)}
                className="w-full text-left flex items-center justify-between p-3 rounded-lg border border-outline-variant/30 bg-surface hover:bg-surface-container-low transition-colors group cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-primary text-[20px]">api</span>
                  <div>
                    <p className="text-[14px] font-semibold text-on-surface group-hover:text-primary transition-colors">
                      /v1/docs OpenAPI &amp; Swagger UI
                    </p>
                    <p className="text-[11px] text-outline">
                      Interactive contract schemas &amp; endpoints
                    </p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors text-[18px]">
                  open_in_new
                </span>
              </button>

              {/* Cluster Endpoint */}
              <div>
                <label className="text-[11px] text-on-surface-variant font-semibold block mb-1">
                  Current Cluster Endpoint
                </label>
                <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-surface border border-outline-variant/30 font-mono text-[13px] text-on-surface">
                  <span className="truncate">https://gateway.techmart.internal/v1</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-outline-variant/30 text-on-surface-variant font-sans font-semibold uppercase">
                    mTLS
                  </span>
                </div>
              </div>

              {/* Live Token Preview */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[11px] text-on-surface-variant font-semibold">
                    Production Access Token
                  </label>
                  <button
                    type="button"
                    onClick={handleCopyToken}
                    className="text-[11px] font-semibold text-primary hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[14px]">
                      {tokenCopied ? 'check' : 'content_copy'}
                    </span>{' '}
                    {tokenCopied ? 'Copied!' : 'Copy Token'}
                  </button>
                </div>
                <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-surface border border-outline-variant/30 font-mono text-[13px] text-on-surface-variant">
                  <span>tm_live_********************</span>
                  <span className="material-symbols-outlined text-outline text-[18px]">key</span>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 3: Appearance & Workspace Preferences */}
          <div>
            <h3 className="text-[11px] text-outline uppercase tracking-wider font-semibold mb-2.5">
              APPEARANCE &amp; WORKSPACE PREFERENCES
            </h3>
            <div className="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 space-y-4 shadow-xs">
              <div>
                <span className="text-[11px] text-on-surface-variant font-semibold block mb-2">
                  Theme Mode
                </span>
                <div className="grid grid-cols-3 gap-1.5 p-1 rounded-lg bg-surface border border-outline-variant/30">
                  {(
                    [
                      { id: 'light', label: 'Light (Selected)', icon: 'light_mode' },
                      { id: 'dark', label: 'Dark (Beta)', icon: 'dark_mode' },
                      { id: 'system', label: 'System Sync', icon: 'devices' },
                    ] as const
                  ).map((opt) => {
                    const isSelected = themeMode === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => onChangeThemeMode(opt.id)}
                        className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-[12px] transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-surface-container-lowest border border-outline-variant/30 text-on-surface shadow-xs font-semibold'
                            : 'text-on-surface-variant hover:text-on-surface font-medium'
                        }`}
                      >
                        <span
                          className={`material-symbols-outlined text-[16px] ${
                            isSelected ? 'text-primary material-symbols-filled' : ''
                          }`}
                        >
                          {opt.icon}
                        </span>
                        <span className="truncate">
                          {opt.id === 'light'
                            ? isSelected
                              ? 'Light (Selected)'
                              : 'Light'
                            : opt.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="h-px bg-outline-variant/20"></div>

              {/* Toggle: Real-time Telemetry Auto-refresh */}
              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <span className="text-[14px] font-semibold text-on-surface block">
                    Real-time Telemetry Auto-refresh (10s)
                  </span>
                  <span className="text-[13px] text-outline">
                    Poll cluster metrics and vector dispatch latency
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    checked={autoRefresh}
                    onChange={(e) => onToggleAutoRefresh(e.target.checked)}
                    className="sr-only peer"
                    type="checkbox"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-container"></div>
                </label>
              </div>

              {/* Toggle: Strict Groundedness Guardrail Blocking */}
              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <span className="text-[14px] font-semibold text-on-surface block">
                    Strict Groundedness Guardrail Blocking
                  </span>
                  <span className="text-[13px] text-outline">
                    Halt auto-resolution when confidence &lt; 0.90
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    checked={strictGuardrails}
                    onChange={(e) => onToggleStrictGuardrails(e.target.checked)}
                    className="sr-only peer"
                    type="checkbox"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-container"></div>
                </label>
              </div>
            </div>
          </div>

          {/* SECTION 4: Session Security & Danger Zone */}
          <div>
            <h3 className="text-[11px] text-outline uppercase tracking-wider font-semibold mb-2.5">
              SESSION SECURITY &amp; DANGER ZONE
            </h3>
            <div className="rounded-lg border border-red-200 bg-red-50/40 p-4 space-y-4">
              <div className="space-y-1.5 text-[13px] tabular-nums">
                <div className="flex items-center justify-between">
                  <span className="text-outline">Client IP:</span>
                  <span className="font-mono text-on-surface font-medium">10.240.12.8</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-outline">Authentication:</span>
                  <span className="text-on-surface font-medium inline-flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px] text-emerald-600">
                      verified
                    </span>{' '}
                    Okta SSO (MFA active)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-outline">TTL / Token Expiry:</span>
                  <span className="font-mono text-on-surface font-semibold">4h 22m remaining</span>
                </div>
              </div>

              <button
                type="button"
                onClick={onSignOut}
                className="w-full flex items-center justify-center gap-2 h-10 px-4 rounded-lg bg-white border border-red-300 text-red-700 hover:bg-red-50 hover:border-red-400 text-[14px] font-semibold shadow-xs transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px] text-red-600">logout</span>
                <span>Revoke Session &amp; Sign Out</span>
              </button>
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="px-6 py-3.5 bg-surface-container-low border-t border-outline-variant/30 flex items-center justify-between text-[11px] font-semibold text-outline">
          <span>TechMart AI Core v3.14.0-patch4</span>
          <span className="text-emerald-700">Node US-East-1d</span>
        </div>
      </aside>

      {/* OpenAPI /v1/docs Modal */}
      {showSwaggerModal && (
        <div className="fixed inset-0 bg-[#0F172A]/50 backdrop-blur-[2px] z-[60] flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant pb-3">
              <div>
                <h3 className="text-[16px] font-semibold text-on-surface">
                  TechMart Support AI — FastAPI /v1 OpenAPI Specification
                </h3>
                <p className="text-[12px] text-on-surface-variant font-mono">
                  Base URL: https://gateway.techmart.internal/v1 · OpenAPI 3.1.0
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowSwaggerModal(false)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-2.5 text-[12px] font-mono">
              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/50 flex items-center justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded bg-primary text-white font-semibold mr-2">
                    POST
                  </span>
                  <span className="text-on-surface font-semibold">/v1/auth/login</span>
                </div>
                <span className="text-on-surface-variant font-sans">
                  Issue corporate JWT bearer session token
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/50 flex items-center justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded bg-primary text-white font-semibold mr-2">
                    POST
                  </span>
                  <span className="text-on-surface font-semibold">/v1/chat</span>
                </div>
                <span className="text-on-surface-variant font-sans">
                  Execute semantic router + FAISS RAG synthesis
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/50 flex items-center justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded bg-emerald-700 text-white font-semibold mr-2">
                    GET
                  </span>
                  <span className="text-on-surface font-semibold">/v1/health</span>
                </div>
                <span className="text-on-surface-variant font-sans">
                  FastAPI, FAISS index, and MongoDB cluster probe
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/50 flex items-center justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded bg-emerald-700 text-white font-semibold mr-2">
                    GET
                  </span>
                  <span className="text-on-surface font-semibold">/v1/evaluation/summary</span>
                </div>
                <span className="text-on-surface-variant font-sans">
                  Retrieve Hit@K, MRR@5, and router benchmark metrics
                </span>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowSwaggerModal(false)}
                className="px-4 py-1.5 rounded-lg bg-primary-container text-on-primary text-[13px] font-semibold"
              >
                Close Contract Viewer
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
