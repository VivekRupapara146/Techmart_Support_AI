import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  ConversationSession,
  ChatMessage,
  PipelineStep,
  apiClient,
  stripDangerousTags,
  TraceLogEntry,
} from '../services/apiClient';

interface SupportWorkspaceProps {
  sessions: ConversationSession[];
  activeSessionId: string;
  activeRouter: string;
  strictGuardrails: boolean;
  workspaceSubMode: 'chat' | 'overview';
  onSelectSession: (id: string) => void;
  onUpdateSessions: React.Dispatch<React.SetStateAction<ConversationSession[]>>;
  onAppendTraceLog: (log: TraceLogEntry) => void;
  onToggleSubMode: (mode: 'chat' | 'overview') => void;
  onNavigateTab: (tab: 'workspace' | 'benchmarks' | 'operations') => void;
}

export const SupportWorkspace: React.FC<SupportWorkspaceProps> = ({
  sessions,
  activeSessionId,
  activeRouter,
  strictGuardrails,
  workspaceSubMode,
  onSelectSession,
  onUpdateSessions,
  onAppendTraceLog,
  onToggleSubMode,
  onNavigateTab,
}) => {
  const [rawSearch, setRawSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<
    'All' | 'Billing' | 'Returns' | 'Technical'
  >('All');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activePipelineStep, setActivePipelineStep] = useState<number | null>(null);
  const [collapsedEvidenceIds, setCollapsedEvidenceIds] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Debounce search input (200ms) for performance optimization
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(rawSearch.trim().toLowerCase());
    }, 200);
    return () => clearTimeout(timer);
  }, [rawSearch]);

  // Cmd/Ctrl + K shortcut to focus session search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) || sessions[0],
    [sessions, activeSessionId]
  );

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages.length, activeSessionId]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const matchesCat =
        selectedCategory === 'All' ||
        s.category === selectedCategory ||
        (selectedCategory === 'Returns' && s.preview.toLowerCase().includes('return'));
      const matchesQuery =
        !debouncedSearch ||
        s.customerName.toLowerCase().includes(debouncedSearch) ||
        s.sessionCode.toLowerCase().includes(debouncedSearch) ||
        s.preview.toLowerCase().includes(debouncedSearch) ||
        s.category.toLowerCase().includes(debouncedSearch);
      return matchesCat && matchesQuery;
    });
  }, [sessions, selectedCategory, debouncedSearch]);

  // Virtualized list window calculation for high-volume conversation lists
  const ITEM_HEIGHT = 104;
  const VIEWPORT_HEIGHT = 640;
  const totalHeight = filteredSessions.length * ITEM_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - 2);
  const endIndex = Math.min(
    filteredSessions.length,
    Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ITEM_HEIGHT) + 3
  );
  const visibleSessions = filteredSessions.slice(startIndex, endIndex);

  const handleCreateNewConversation = () => {
    const nextNum = 8942 + sessions.length;
    const customerPool = [
      { name: 'Hannah Abbott', category: 'Returns' as const, channel: 'Web Widget' },
      { name: 'Victor Krum', category: 'Technical' as const, channel: 'API Support' },
      { name: 'Clara Oswald', category: 'Billing' as const, channel: 'Enterprise Portal' },
    ];
    const picked = customerPool[sessions.length % customerPool.length];
    const newId = `sess-${nextNum}`;
    const nowLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newSession: ConversationSession = {
      id: newId,
      sessionCode: `#sess-${nextNum}`,
      customerName: picked.name,
      category: picked.category,
      channel: picked.channel,
      relativeTime: 'Just now',
      preview: 'New customer support session initialized. Waiting for query...',
      active: true,
      messages: [
        {
          id: `msg-init-${Date.now()}`,
          role: 'assistant',
          author: 'TechMart Support AI',
          timestamp: nowLabel,
          specialist: 'Returns Specialist',
          groundedScore: 99.4,
          modelName: 'gpt-4o-grounded',
          content: `Hello ${picked.name}, I am connected to the TechMart Grounded Knowledge Base (KB-v2.4). How can I assist you with your order, RMA return, billing invoice, or hardware diagnostics today?`,
          evidence: [
            {
              id: 'KB-RET-104',
              section: '§4.2 Exceptions',
              similarity: 0.94,
              snippet:
                'Unopened hardware in intact factory shrink-wrap qualifies for an extended 45-day RMA exchange window...',
            },
          ],
        },
      ],
      latestTelemetry: activeSession.latestTelemetry,
    };

    onUpdateSessions((prev) => [
      newSession,
      ...prev.map((item) => ({ ...item, active: false })),
    ]);
    onSelectSession(newId);
    onToggleSubMode('chat');
  };

  const handleSendMessage = async (overrideText?: string, forceRefusal?: boolean) => {
    const rawText = overrideText !== undefined ? overrideText : inputPrompt;
    const sanitizedContent = stripDangerousTags(rawText.trim());
    if (!sanitizedContent || isSending) return;

    if (overrideText === undefined) {
      setInputPrompt('');
    }

    const nowLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg: ChatMessage = {
      id: `msg-u-${Date.now()}`,
      role: 'user',
      author: activeSession.customerName,
      timestamp: nowLabel,
      content: sanitizedContent,
    };

    // Append user message immediately
    onUpdateSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              relativeTime: 'Just now',
              preview: sanitizedContent,
              messages: [...s.messages, userMsg],
            }
          : s
      )
    );

    // Animate pipeline stages sequentially in right-hand telemetry panel
    setIsSending(true);
    setActivePipelineStep(1);
    await new Promise((r) => setTimeout(r, 130));
    setActivePipelineStep(2);
    await new Promise((r) => setTimeout(r, 150));
    setActivePipelineStep(3);
    await new Promise((r) => setTimeout(r, 140));
    setActivePipelineStep(4);

    try {
      const { reply, telemetry, traceLog } = await apiClient.sendChat({
        sessionId: activeSession.id,
        message: sanitizedContent,
        activeRouter,
        forceRefusal,
        cumulativeCostUsd: activeSession.latestTelemetry.cumulativeCostUsd,
      });

      await new Promise((r) => setTimeout(r, 160));

      onUpdateSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? {
                ...s,
                messages: [...s.messages, reply],
                latestTelemetry: telemetry,
              }
            : s
        )
      );
      onAppendTraceLog(traceLog);
    } finally {
      setIsSending(false);
      setActivePipelineStep(null);
    }
  };

  const toggleEvidenceAccordion = (msgId: string) => {
    setCollapsedEvidenceIds((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleCopyCitation = (msg: ChatMessage) => {
    const citationText = msg.evidence
      ? msg.evidence.map((e) => `[${e.id} · ${e.section}] "${e.snippet}"`).join('\n')
      : msg.content;
    navigator.clipboard?.writeText(citationText);
    setCopiedId(msg.id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleVote = (msgId: string, vote: 'up' | 'down') => {
    onUpdateSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              messages: s.messages.map((m) =>
                m.id === msgId
                  ? { ...m, helpfulVote: m.helpfulVote === vote ? null : vote }
                  : m
              ),
            }
          : s
      )
    );
  };

  const handleEscalateTicket = (msgId: string) => {
    onUpdateSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              humanTakeover: true,
              messages: s.messages.map((m) =>
                m.id === msgId ? { ...m, escalatedToHuman: true } : m
              ),
            }
          : s
      )
    );
  };

  const handleClearSession = () => {
    onUpdateSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              messages: s.messages.slice(0, 1),
            }
          : s
      )
    );
  };

  const handleExportSessionTrace = () => {
    const blob = new Blob([JSON.stringify(activeSession, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeSession.id}-trace-export.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Overview Canvas Mode (matches Screenshot 1: Support Workspace Overview)
  if (workspaceSubMode === 'overview') {
    return (
      <div className="flex-1 bg-surface overflow-y-auto p-8 flex flex-col gap-6 custom-scrollbar">
        {/* Stage Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-[24px] leading-[32px] font-semibold text-on-surface tracking-tight">
              Support Workspace
            </h1>
            <p className="text-[14px] leading-[22px] text-on-surface-variant">
              Real-time AI query resolution, grounding verification, and router observability.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onToggleSubMode('chat')}
              className="inline-flex items-center gap-2 h-9 px-3.5 bg-surface-container-lowest border border-outline-variant hover:border-outline text-on-surface rounded-lg text-[14px] font-medium shadow-xs hover:bg-surface-container-low transition-all"
              type="button"
            >
              <span className="material-symbols-outlined">forum</span>
              <span>Active Session Stream</span>
            </button>
            <button
              onClick={handleCreateNewConversation}
              className="inline-flex items-center gap-2 h-9 px-4 bg-primary hover:bg-primary-container text-on-primary rounded-lg text-[14px] font-medium shadow-xs transition-all duration-150 ease-in-out"
              type="button"
            >
              <span className="material-symbols-outlined">add</span>
              <span>New Session</span>
            </button>
          </div>
        </div>

        {/* Quick Metrics Ribbon (Bento Micro Tier) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-xs flex flex-col gap-1">
            <div className="flex items-center justify-between text-on-surface-variant text-[12px] font-medium">
              <span>RAG Grounding Accuracy</span>
              <span className="material-symbols-outlined text-tertiary">verified</span>
            </div>
            <div className="flex items-baseline gap-2 tabular-nums">
              <span className="text-[20px] leading-[28px] font-semibold text-on-surface">
                99.4%
              </span>
              <span className="text-[11px] font-semibold text-tertiary flex items-center">
                +0.3%
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant">
              Validated by 14k vector traces
            </span>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-xs flex flex-col gap-1">
            <div className="flex items-center justify-between text-on-surface-variant text-[12px] font-medium">
              <span>Semantic Router Latency</span>
              <span className="material-symbols-outlined text-secondary">speed</span>
            </div>
            <div className="flex items-baseline gap-2 tabular-nums">
              <span className="text-[20px] leading-[28px] font-semibold text-on-surface">
                42ms
              </span>
              <span className="text-[11px] font-semibold text-tertiary flex items-center">
                -4ms p95
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant">
              Embedding tier: bge-large-en
            </span>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-xs flex flex-col gap-1">
            <div className="flex items-center justify-between text-on-surface-variant text-[12px] font-medium">
              <span>Autonomous Resolution</span>
              <span className="material-symbols-outlined text-primary">smart_toy</span>
            </div>
            <div className="flex items-baseline gap-2 tabular-nums">
              <span className="text-[20px] leading-[28px] font-semibold text-on-surface">
                86.2%
              </span>
              <span className="text-[11px] text-on-surface-variant font-medium">
                zero escalations
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant">
              Across standard e-commerce tier
            </span>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-xs flex flex-col gap-1">
            <div className="flex items-center justify-between text-on-surface-variant text-[12px] font-medium">
              <span>Escalation Queues</span>
              <span className="material-symbols-outlined text-outline">alt_route</span>
            </div>
            <div className="flex items-baseline gap-2 tabular-nums">
              <span className="text-[20px] leading-[28px] font-semibold text-on-surface">
                3 Active
              </span>
              <span className="text-[11px] font-medium text-on-surface-variant">
                Tier-3 Engineers
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant">Median triage wait 1.2m</span>
          </div>
        </div>

        {/* Spacious Content Stage Container */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs p-10 flex-1 min-h-[420px] flex flex-col items-center justify-center text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(#c7c4d8_1px,transparent_1px)] [background-size:16px_16px] opacity-25 pointer-events-none"></div>

          <div className="relative z-10 max-w-lg flex flex-col items-center">
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-2xl bg-surface-container-low border border-primary/20 flex items-center justify-center text-primary relative">
                <span className="material-symbols-outlined text-[32px]">support_agent</span>
              </div>
            </div>
            <h2 className="text-[20px] leading-[28px] font-semibold text-on-surface tracking-tight mb-2">
              Workspace Canvas Ready
            </h2>
            <p className="text-[14px] text-on-surface-variant max-w-md mb-8">
              Select a module from the sidebar or initiate a support session to load child views
              and telemetry.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
              <button
                onClick={() => onToggleSubMode('chat')}
                className="group text-left p-3.5 bg-surface-bright border border-outline-variant rounded-lg hover:border-primary hover:bg-surface-container-low transition-all duration-150"
                type="button"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="material-symbols-outlined text-primary">forum</span>
                  <span className="material-symbols-outlined text-outline-variant text-[16px] group-hover:text-primary transition-colors">
                    arrow_forward
                  </span>
                </div>
                <h3 className="text-[14px] font-semibold text-on-surface mb-0.5">
                  Session Stream
                </h3>
                <p className="text-[11px] text-on-surface-variant">
                  Live dialogue &amp; customer intents
                </p>
              </button>

              <button
                onClick={() => onNavigateTab('benchmarks')}
                className="group text-left p-3.5 bg-surface-bright border border-outline-variant rounded-lg hover:border-primary hover:bg-surface-container-low transition-all duration-150"
                type="button"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="material-symbols-outlined text-primary">document_scanner</span>
                  <span className="material-symbols-outlined text-outline-variant text-[16px] group-hover:text-primary transition-colors">
                    arrow_forward
                  </span>
                </div>
                <h3 className="text-[14px] font-semibold text-on-surface mb-0.5">
                  RAG Inspector
                </h3>
                <p className="text-[11px] text-on-surface-variant">
                  Chunk attribution &amp; citation graph
                </p>
              </button>

              <button
                onClick={() => onNavigateTab('operations')}
                className="group text-left p-3.5 bg-surface-bright border border-outline-variant rounded-lg hover:border-primary hover:bg-surface-container-low transition-all duration-150"
                type="button"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="material-symbols-outlined text-primary">hub</span>
                  <span className="material-symbols-outlined text-outline-variant text-[16px] group-hover:text-primary transition-colors">
                    arrow_forward
                  </span>
                </div>
                <h3 className="text-[14px] font-semibold text-on-surface mb-0.5">Live Routing</h3>
                <p className="text-[11px] text-on-surface-variant">
                  Classifiers, thresholds &amp; latency
                </p>
              </button>
            </div>
          </div>

          <div className="mt-10 w-full max-w-xl text-left bg-surface border border-outline-variant rounded-lg p-4 shadow-xs flex items-start gap-3">
            <span className="material-symbols-outlined text-primary mt-0.5 shrink-0">
              shield_lock
            </span>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-semibold text-on-surface">
                  Deterministic Safety Anchor
                </span>
                <span className="text-[11px] px-1.5 py-0.5 rounded bg-surface-container text-primary font-mono font-semibold">
                  v1.4-strict
                </span>
              </div>
              <p className="text-[13px] text-on-surface-variant">
                Every generation requires direct passage grounding across authorized TechMart
                internal repositories. Hallucination guardrails active.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Default 3-Column Active Chat & Telemetry Workspace (Screenshot 4)
  const tel = activeSession.latestTelemetry;
  const totalDistMs = Math.max(1, tel.e2eLatencyMs);
  const s1Pct = Math.max(4, Math.round(((tel.steps[0]?.latencyMs || 14) / totalDistMs) * 100));
  const s2Pct = Math.max(8, Math.round(((tel.steps[1]?.latencyMs || 38) / totalDistMs) * 100));
  const s3Pct = Math.max(4, Math.round(((tel.steps[2]?.latencyMs || 12) / totalDistMs) * 100));
  const s4Pct = Math.max(10, 100 - s1Pct - s2Pct - s3Pct);

  return (
    <main className="flex-1 flex overflow-hidden bg-background">
      {/* ==================================================== */}
      {/* COLUMN 1: Conversation History (25% width / ~320px)   */}
      {/* ==================================================== */}
      <section className="w-1/4 min-w-[270px] max-w-[340px] h-full flex flex-col bg-surface-container-lowest border-r border-outline-variant shrink-0">
        {/* Top Action Bar & Search */}
        <div className="p-3.5 border-b border-outline-variant/70 flex flex-col gap-2.5">
          <button
            onClick={handleCreateNewConversation}
            className="w-full bg-primary-container hover:bg-primary text-on-primary text-[14px] font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-2 shadow-xs transition-colors cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            <span>New Conversation</span>
          </button>

          <div className="relative w-full">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-on-surface-variant text-[16px]">
              search
            </span>
            <input
              ref={searchInputRef}
              value={rawSearch}
              onChange={(e) => setRawSearch(e.target.value)}
              className="w-full pl-8 pr-11 py-1.5 bg-surface-container-lowest border border-outline-variant/80 rounded-lg text-[13px] text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/20 transition-all"
              placeholder="Search sessions..."
              type="text"
            />
            <kbd className="absolute right-2 top-1.5 px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant text-[10px] text-on-surface-variant font-mono font-medium">
              ⌘K
            </kbd>
          </div>

          {/* Interactive Filter Buttons */}
          <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar pt-1 pb-0.5">
            {(['All', 'Billing', 'Returns', 'Technical'] as const).map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold shrink-0 transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-primary-container text-on-primary shadow-xs'
                      : 'bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface border border-outline-variant/60'
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </div>

        {/* Virtualized Scrollable Thread List */}
        <div
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
          className="flex-1 overflow-y-auto custom-scrollbar relative"
        >
          {filteredSessions.length === 0 ? (
            <div className="p-6 text-center text-[13px] text-on-surface-variant">
              No sessions match &ldquo;{rawSearch}&rdquo; in {selectedCategory}.
            </div>
          ) : (
            <div style={{ height: `${totalHeight}px`, position: 'relative' }}>
              <div
                style={{
                  transform: `translateY(${startIndex * ITEM_HEIGHT}px)`,
                }}
                className="divide-y divide-outline-variant/40"
              >
                {visibleSessions.map((session) => {
                  const isCurrent = session.id === activeSession.id;
                  return (
                    <div
                      key={session.id}
                      onClick={() => onSelectSession(session.id)}
                      className={`p-3.5 cursor-pointer transition-colors relative ${
                        isCurrent
                          ? 'bg-surface-container-low/80 border-l-2 border-primary'
                          : 'hover:bg-surface-container-low/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className={`text-[14px] truncate ${
                            isCurrent
                              ? 'font-semibold text-on-surface'
                              : 'font-medium text-on-surface'
                          }`}
                        >
                          {session.customerName}
                        </span>
                        <span className="text-[11px] text-on-surface-variant shrink-0 tabular-nums">
                          {session.relativeTime}
                        </span>
                      </div>

                      <p className="text-[13px] text-on-surface-variant line-clamp-2 mb-2 leading-snug">
                        {session.preview}
                      </p>

                      <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                              session.category === 'Enterprise'
                                ? 'bg-surface-container text-primary border-primary/20'
                                : session.category === 'Billing'
                                ? 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]'
                                : 'bg-surface-container text-on-surface-variant border-outline-variant/60'
                            }`}
                          >
                            {session.category}
                          </span>
                          <span className="tabular-nums">{session.messages.length} msgs</span>
                        </div>
                        {isCurrent ? (
                          <span className="text-[11px] font-semibold text-tertiary">Active</span>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ==================================================== */}
      {/* COLUMN 2: Active Chat Canvas (50% width / center)     */}
      {/* ==================================================== */}
      <section className="w-1/2 flex-1 h-full flex flex-col bg-surface border-r border-outline-variant relative min-w-0">
        {/* Chat Canvas Header */}
        <div className="h-14 px-5 bg-surface-container-lowest border-b border-outline-variant flex items-center justify-between shrink-0 shadow-xs gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <h1 className="text-[15px] font-semibold text-on-surface truncate">
              {activeSession.sessionCode} · {activeSession.customerName}
            </h1>
            <span className="text-[12px] text-on-surface-variant hidden sm:inline">
              · {activeSession.category} · {activeSession.channel}
            </span>
          </div>

          {/* Header Actions */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => onToggleSubMode('overview')}
              className="px-2.5 py-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low text-[12px] font-medium rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
              title="Switch to Workspace Overview Canvas"
            >
              <span className="material-symbols-outlined text-[16px]">grid_view</span>
              <span className="hidden xl:inline">Overview</span>
            </button>
            <button
              type="button"
              onClick={handleClearSession}
              className="px-2.5 py-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low text-[12px] font-medium rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">delete_sweep</span>
              <span className="hidden lg:inline">Clear</span>
            </button>
            <button
              type="button"
              onClick={handleExportSessionTrace}
              className="px-2.5 py-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low text-[12px] font-medium rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">file_download</span>
              <span className="hidden lg:inline">Export Trace</span>
            </button>
            <button
              type="button"
              onClick={() =>
                onUpdateSessions((prev) =>
                  prev.map((s) =>
                    s.id === activeSession.id ? { ...s, humanTakeover: !s.humanTakeover } : s
                  )
                )
              }
              className={`px-3 py-1.5 border text-[12px] font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer whitespace-nowrap ${
                activeSession.humanTakeover
                  ? 'bg-amber-50 border-amber-300 text-amber-900'
                  : 'border-outline-variant hover:bg-surface-container-low text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-primary text-[16px]">
                person_add
              </span>
              <span>
                {activeSession.humanTakeover ? 'Human Agent Active' : 'Human Takeover'}
              </span>
            </button>
          </div>
        </div>

        {/* Scrollable Conversation Stream */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          {activeSession.messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="flex flex-col items-end">
                  <div className="bg-inverse-surface text-inverse-on-surface rounded-2xl rounded-tr-none px-4 py-3 max-w-lg shadow-xs">
                    <p className="text-[14px] leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                  </div>
                  <span className="text-[11px] text-on-surface-variant mt-1.5 mr-1 tabular-nums">
                    {msg.timestamp} · {msg.author}
                  </span>
                </div>
              );
            }

            // Assistant Uncertainty / Safe Refusal Fallback Card
            if (msg.isRefusal) {
              return (
                <div key={msg.id} className="flex flex-col items-start max-w-xl w-full">
                  <div className="w-full bg-[#FFFBEB]/70 rounded-xl border border-[#FDE68A] shadow-xs p-4">
                    {/* Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-[#FDE68A]/70">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-md bg-[#FEF3C7] text-[#92400E] flex items-center justify-center">
                          <span className="material-symbols-outlined text-[14px]">warning</span>
                        </div>
                        <span className="text-[14px] font-semibold text-[#92400E]">
                          Autonomous Boundary Alert
                        </span>
                        <span className="bg-[#FFFBEB] text-[#92400E] text-[11px] px-2 py-0.5 rounded-md font-medium border border-[#FDE68A]">
                          Threshold Triggered (&lt;75%)
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#92400E]">
                        Refusal &amp; Escalation
                      </span>
                    </div>

                    {/* Body */}
                    <p className="text-[14px] text-on-surface leading-relaxed mb-3">
                      {msg.content}
                    </p>

                    {/* Escalation Card */}
                    <div className="bg-surface-container-lowest rounded-lg border border-[#FDE68A] p-3 flex flex-col gap-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 text-on-surface text-[13px] font-semibold">
                          <span className="material-symbols-outlined text-[#D97706] text-[16px]">
                            confirmation_number
                          </span>
                          <span>
                            Ticket {msg.ticketId || '#ESC-4029'} dispatched to Returns Management
                            Queue
                          </span>
                        </div>
                        <span className="text-[11px] text-[#92400E] font-semibold">
                          {msg.slaText || 'Assigned SLA: < 15 mins'}
                        </span>
                      </div>
                      <div className="flex items-center justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => handleEscalateTicket(msg.id)}
                          className={`text-white text-[13px] font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer ${
                            msg.escalatedToHuman
                              ? 'bg-emerald-700'
                              : 'bg-[#D97706] hover:bg-[#B45309]'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[15px]">
                            {msg.escalatedToHuman ? 'check_circle' : 'support_agent'}
                          </span>
                          <span>
                            {msg.escalatedToHuman
                              ? 'Escalated to Tier-2 Supervisor'
                              : 'Escalate to Human Agent Now'}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                  <span className="text-[11px] text-on-surface-variant mt-1.5 ml-1 tabular-nums">
                    {msg.timestamp} · {msg.author}
                  </span>
                </div>
              );
            }

            // Standard Grounded Assistant Response Card
            const isExpanded = !collapsedEvidenceIds[msg.id];
            return (
              <div key={msg.id} className="flex flex-col items-start max-w-xl w-full">
                <div className="w-full bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs p-4">
                  {/* Meta Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-outline-variant/50">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-primary-container text-on-primary flex items-center justify-center">
                        <span className="material-symbols-outlined text-[14px]">smart_toy</span>
                      </div>
                      <span className="text-[14px] font-semibold text-on-surface">
                        {msg.author}
                      </span>
                      <span className="bg-[#EFF6FF] text-[#1E40AF] text-[11px] px-2 py-0.5 rounded-md font-medium border border-[#BFDBFE]">
                        Routed to: {msg.specialist || 'Returns Specialist'}
                      </span>
                    </div>

                    {/* Grounded Confidence Pill */}
                    <div className="flex items-center gap-1 text-[#065F46] text-[11px] font-semibold bg-[#ECFDF5] px-2 py-0.5 rounded-md border border-[#A7F3D0] tabular-nums">
                      <span className="material-symbols-outlined material-symbols-filled text-[14px] text-[#10B981]">
                        verified
                      </span>
                      <span>Grounded ({(msg.groundedScore ?? 99.4).toFixed(1)}%)</span>
                    </div>
                  </div>

                  {/* Answer Body */}
                  <div className="text-[14px] text-on-surface space-y-2.5 mb-4 leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>

                  {/* Interactive Expandable Accordion for Retrieved Evidence / Sources */}
                  {msg.evidence && msg.evidence.length > 0 && (
                    <div className="bg-surface-container-low rounded-lg border border-outline-variant/60 mb-3 overflow-hidden">
                      <button
                        type="button"
                        onClick={() => toggleEvidenceAccordion(msg.id)}
                        className="w-full px-3 py-2.5 flex items-center justify-between text-[12px] font-semibold text-on-surface hover:bg-surface-container transition-colors cursor-pointer"
                      >
                        <span className="flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-primary text-[15px]">
                            library_books
                          </span>
                          <span>Retrieved Evidence ({msg.evidence.length} chunks)</span>
                        </span>
                        <span className="flex items-center gap-2">
                          <span className="text-on-surface-variant font-mono text-[11px]">
                            Cosine Cos &gt; 0.88
                          </span>
                          <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                            {isExpanded ? 'expand_less' : 'expand_more'}
                          </span>
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="px-3 pb-3 space-y-2 text-[13px] border-t border-outline-variant/40 pt-2">
                          {msg.evidence.map((chunk) => (
                            <div
                              key={chunk.id}
                              className="bg-surface-container-lowest p-2.5 rounded border border-outline-variant/40"
                            >
                              <div className="flex items-center justify-between text-on-surface-variant font-mono text-[11px] mb-1 tabular-nums">
                                <span className="text-primary font-medium">
                                  [{chunk.id} · {chunk.section}]
                                </span>
                                <span className="text-[#065F46] font-semibold">
                                  Similarity: {chunk.similarity.toFixed(2)}
                                </span>
                              </div>
                              <p className="text-on-surface text-[12px] italic leading-relaxed">
                                &ldquo;{chunk.snippet}&rdquo;
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Footer Micro Actions */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleVote(msg.id, 'up')}
                        className={`p-1 rounded transition-colors cursor-pointer ${
                          msg.helpfulVote === 'up'
                            ? 'text-primary bg-surface-container'
                            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
                        }`}
                        title="Helpful"
                      >
                        <span className="material-symbols-outlined text-[15px]">thumb_up</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleVote(msg.id, 'down')}
                        className={`p-1 rounded transition-colors cursor-pointer ${
                          msg.helpfulVote === 'down'
                            ? 'text-error bg-error-container/40'
                            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
                        }`}
                        title="Not Helpful"
                      >
                        <span className="material-symbols-outlined text-[15px]">thumb_down</span>
                      </button>
                      <div className="h-3 w-px bg-outline-variant/60 mx-1"></div>
                      <button
                        type="button"
                        onClick={() => handleCopyCitation(msg)}
                        className="text-on-surface-variant hover:text-on-surface text-[11px] font-semibold flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-surface-container-low transition-colors cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[14px]">
                          {copiedId === msg.id ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedId === msg.id ? 'Copied Citation' : 'Copy Citation'}</span>
                      </button>
                    </div>
                    <span className="text-[11px] font-medium text-on-surface-variant font-mono">
                      Model: {msg.modelName || 'gpt-4o-grounded'}
                    </span>
                  </div>
                </div>
                <span className="text-[11px] text-on-surface-variant mt-1.5 ml-1 tabular-nums">
                  {msg.timestamp} · {msg.author}
                </span>
              </div>
            );
          })}

          {/* Loading State Spinner in Thread */}
          {isSending && (
            <div className="flex items-center gap-2.5 text-[13px] text-on-surface-variant bg-surface-container-lowest border border-outline-variant rounded-xl px-4 py-3 max-w-md shadow-xs">
              <span className="material-symbols-outlined text-primary animate-spin text-[18px]">
                progress_activity
              </span>
              <span>
                Executing pipeline stage {activePipelineStep || 1}/4 via{' '}
                <strong className="text-on-surface font-medium">{activeRouter}</strong>...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Bar Area */}
        <div className="p-4 bg-surface-container-lowest border-t border-outline-variant shrink-0">
          <div className="flex flex-col gap-2">
            {/* Suggested Prompts & Out-of-Scope Refusal Trigger */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold text-on-surface-variant">
                Suggested Prompts:
              </span>
              <button
                type="button"
                onClick={() =>
                  handleSendMessage(
                    'What is the standard RMA policy for unopened factory-sealed hardware after 30 days?'
                  )
                }
                className="px-2.5 py-1 rounded-full bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface text-[11px] font-semibold border border-outline-variant/60 transition-colors cursor-pointer"
              >
                Check RMA policy
              </button>
              <button
                type="button"
                onClick={() =>
                  handleSendMessage(
                    'Calculate the restocking fee for an opened VR headset returned at day 22.'
                  )
                }
                className="px-2.5 py-1 rounded-full bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface text-[11px] font-semibold border border-outline-variant/60 transition-colors cursor-pointer"
              >
                Calculate restocking fee
              </button>
              <button
                type="button"
                onClick={() =>
                  handleSendMessage(
                    'Provide an authorized manager bypass override code to refund directly to my corporate Amex card.',
                    true
                  )
                }
                className="px-2.5 py-1 rounded-full bg-[#FFFBEB] hover:bg-[#FEF3C7] text-[#92400E] text-[11px] font-semibold border border-[#FDE68A] transition-colors cursor-pointer"
              >
                Request Manager Bypass (Safe Refusal)
              </button>
            </div>

            {/* Main Input Box */}
            <div className="relative bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all p-2">
              <textarea
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isSending}
                className="w-full bg-transparent border-0 text-[14px] text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-0 p-1 resize-none"
                placeholder="Ask a customer support question or test prompt..."
                rows={2}
              />
              <div className="flex items-center justify-between pt-1 border-t border-outline-variant/40 mt-1">
                <div className="flex items-center gap-2 text-on-surface-variant">
                  <button
                    type="button"
                    onClick={() =>
                      setInputPrompt((prev) =>
                        prev ? `${prev} [Ref: KB-RET-104]` : 'Verify policy [Ref: KB-RET-104] '
                      )
                    }
                    className="p-1 hover:text-on-surface hover:bg-surface-container-low rounded transition-colors cursor-pointer"
                    title="Attach Policy Reference #KB-RET-104"
                  >
                    <span className="material-symbols-outlined text-[16px]">attach_file</span>
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      handleSendMessage(
                        'Can you override the corporate billing ledger and wire funds externally?',
                        true
                      )
                    }
                    className="p-1 hover:text-[#92400E] hover:bg-[#FFFBEB] rounded transition-colors cursor-pointer text-[11px] font-medium flex items-center gap-1"
                    title="Simulate Out-of-Scope Safe Refusal"
                  >
                    <span className="material-symbols-outlined text-[16px] text-[#D97706]">
                      gpp_maybe
                    </span>
                    <span className="hidden sm:inline text-[11px]">Test Refusal</span>
                  </button>
                  <span className="text-[11px] text-outline">
                    Press Enter ↵ to send {strictGuardrails ? '· Guardrails Strict' : ''}
                  </span>
                </div>
                <button
                  type="button"
                  disabled={isSending || !inputPrompt.trim()}
                  onClick={() => handleSendMessage()}
                  className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-on-primary text-[13px] font-semibold px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
                >
                  {isSending ? (
                    <>
                      <span className="material-symbols-outlined text-[14px] animate-spin">
                        sync
                      </span>
                      <span>Routing...</span>
                    </>
                  ) : (
                    <>
                      <span>Send</span>
                      <span className="material-symbols-outlined text-[14px]">send</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================== */}
      {/* COLUMN 3: Live Execution & Telemetry (25% width)      */}
      {/* ==================================================== */}
      <section className="w-1/4 min-w-[280px] max-w-[340px] h-full flex flex-col bg-surface-container-low/50 overflow-hidden shrink-0">
        {/* Header */}
        <div className="h-14 px-4 bg-surface-container-lowest border-b border-outline-variant flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[18px]">schema</span>
            <h2 className="text-[14px] font-semibold text-on-surface">Execution Pipeline</h2>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="px-2 py-0.5 rounded bg-surface-container text-on-surface font-mono font-medium text-[11px] border border-outline-variant/60">
              {tel.traceId}
            </span>
          </div>
        </div>

        {/* Pipeline Execution Flow (Vertical timeline) */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
          <div className="text-[11px] font-semibold uppercase text-on-surface-variant tracking-wider">
            Trace Nodes &amp; Latencies
          </div>

          <div className="relative pl-4 space-y-3 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-outline-variant/60">
            {tel.steps.map((step: PipelineStep) => {
              const isStepRunning = isSending && activePipelineStep === step.step;
              return (
                <div
                  key={step.step}
                  className={`relative bg-surface-container-lowest p-3 rounded-lg border transition-all shadow-xs ${
                    isStepRunning
                      ? 'border-primary ring-2 ring-primary/20'
                      : 'border-outline-variant'
                  }`}
                >
                  <div
                    className={`absolute -left-[15px] top-3.5 w-2.5 h-2.5 rounded-full ring-4 ring-background ${
                      isStepRunning
                        ? 'bg-secondary animate-ping'
                        : step.status === 'warning'
                        ? 'bg-[#D97706]'
                        : 'bg-primary'
                    }`}
                  ></div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[13px] font-semibold text-on-surface">
                      {step.title}
                    </span>
                    <span className="font-mono text-[11px] font-semibold text-on-surface-variant tabular-nums">
                      {isStepRunning ? '...' : `${step.latencyMs}ms`}
                    </span>
                  </div>
                  <p className="text-[12px] text-on-surface-variant mb-1.5 leading-snug">
                    {step.description}
                  </p>

                  {step.meta && (
                    <div className="p-1.5 rounded bg-surface-container text-[11px] font-mono text-on-surface-variant space-y-0.5">
                      {Object.entries(step.meta).map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between gap-2">
                          <span>{k}:</span>
                          <span className="font-semibold text-primary truncate">{v}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {step.step === 1 && (
                    <div className="mt-1.5 flex items-center gap-1 text-[11px] font-semibold text-[#065F46]">
                      <span>Status: {isStepRunning ? 'Running' : 'Complete'}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Latency & Cost Telemetry Card */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 shadow-xs mt-4">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-outline-variant/60">
              <span className="text-[14px] font-semibold text-on-surface">Session Telemetry</span>
              <span className="material-symbols-outlined text-on-surface-variant text-[16px]">
                speed
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-3 tabular-nums">
              {/* E2E Latency */}
              <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/40">
                <span className="text-[11px] font-semibold text-on-surface-variant block mb-0.5">
                  E2E Latency
                </span>
                <span className="text-[20px] leading-[26px] font-semibold text-on-surface block font-mono">
                  {tel.e2eLatencyMs}ms
                </span>
                <span
                  className={`text-[11px] font-medium ${
                    tel.latencyDeltaMs <= 0 ? 'text-[#065F46]' : 'text-[#D97706]'
                  }`}
                >
                  {tel.latencyDeltaMs <= 0 ? `${tel.latencyDeltaMs}ms` : `+${tel.latencyDeltaMs}ms`}{' '}
                  vs avg
                </span>
              </div>

              {/* Token Usage */}
              <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/40">
                <span className="text-[11px] font-semibold text-on-surface-variant block mb-0.5">
                  Tokens
                </span>
                <span className="text-[20px] leading-[26px] font-semibold text-on-surface block font-mono">
                  {tel.totalTokens}
                </span>
                <span className="text-[11px] text-on-surface-variant">
                  {tel.tokensIn} in / {tel.tokensOut} out
                </span>
              </div>
            </div>

            {/* Cost & Cumulative */}
            <div className="space-y-2 pt-2 border-t border-outline-variant/40 text-[13px] tabular-nums">
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">Estimated Step Cost:</span>
                <span className="font-mono font-semibold text-on-surface">
                  ${tel.stepCostUsd.toFixed(4)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">Session Cumulative:</span>
                <span className="font-mono font-semibold text-primary">
                  ${tel.cumulativeCostUsd.toFixed(4)}
                </span>
              </div>
            </div>

            {/* Latency Distribution Bar */}
            <div className="mt-3 pt-3 border-t border-outline-variant/40 tabular-nums">
              <div className="flex items-center justify-between text-[11px] font-semibold text-on-surface-variant mb-1">
                <span>Latency Distribution</span>
                <span className="font-mono">{tel.e2eLatencyMs}ms</span>
              </div>
              <div className="w-full h-2 rounded-full bg-surface-container overflow-hidden flex">
                <div
                  className="bg-primary/70 h-full"
                  style={{ width: `${s1Pct}%` }}
                  title={`Input: ${tel.steps[0]?.latencyMs}ms`}
                ></div>
                <div
                  className="bg-secondary h-full"
                  style={{ width: `${s2Pct}%` }}
                  title={`Router: ${tel.steps[1]?.latencyMs}ms`}
                ></div>
                <div
                  className="bg-tertiary h-full"
                  style={{ width: `${s3Pct}%` }}
                  title={`Retrieval: ${tel.steps[2]?.latencyMs}ms`}
                ></div>
                <div
                  className="bg-primary-container h-full"
                  style={{ width: `${s4Pct}%` }}
                  title={`Assembly: ${tel.steps[3]?.latencyMs}ms`}
                ></div>
              </div>
              <div className="flex justify-between text-[10px] text-on-surface-variant mt-1 font-mono">
                <span>Input</span>
                <span>Router</span>
                <span>RAG</span>
                <span>Gen ({s4Pct}%)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Telemetry Bottom Strip */}
        <div className="p-3 bg-surface-container-lowest border-t border-outline-variant shrink-0 flex items-center justify-between text-[11px] font-semibold text-on-surface-variant">
          <span>Vector Engine: Online</span>
          <span className="font-mono">v1.4.12-prod</span>
        </div>
      </section>
    </main>
  );
};
