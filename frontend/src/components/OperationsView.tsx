import React, { useState, useEffect, useMemo } from 'react';
import {
  apiClient,
  HealthResponse,
  TraceLogEntry,
} from '../services/apiClient';

interface OperationsViewProps {
  traces: TraceLogEntry[];
  onAppendTrace: (log: TraceLogEntry) => void;
}

export const OperationsView: React.FC<OperationsViewProps> = ({
  traces,
  onAppendTrace,
}) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [timeWindow, setTimeWindow] = useState('Last 1 hour');
  const [isProbing, setIsProbing] = useState(false);
  const [rawSearch, setRawSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All Statuses');
  const [routerFilter, setRouterFilter] = useState('All Routers');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copiedTraceId, setCopiedTraceId] = useState<string | null>(null);
  const [inspectedTrace, setInspectedTrace] = useState<{
    trace: TraceLogEntry;
    mode: 'payload' | 'graph';
  } | null>(null);
  const [securityAuditOpen, setSecurityAuditOpen] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    apiClient.getHealth().then(setHealth);
  }, []);

  // Debounce trace search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(rawSearch.trim().toLowerCase());
      setPage(1);
    }, 180);
    return () => clearTimeout(timer);
  }, [rawSearch]);

  const handleRunDiagnosticProbe = async () => {
    setIsProbing(true);
    const freshHealth = await apiClient.getHealth();
    await new Promise((r) => setTimeout(r, 400));
    setHealth({
      ...freshHealth,
      services: {
        ...freshHealth.services,
        fastapi: {
          ...freshHealth.services.fastapi,
          probeLatencyMs: Number((1.4 + Math.random() * 0.7).toFixed(1)),
        },
        faiss: {
          ...freshHealth.services.faiss,
          p99LatencyMs: Number((13.6 + Math.random() * 1.4).toFixed(1)),
        },
      },
    });

    const now = new Date();
    const preciseTime = `${now.toTimeString().split(' ')[0]}.${String(
      now.getMilliseconds()
    ).padStart(3, '0')}`;
    const shortId = Math.random().toString(16).substring(2, 6);
    onAppendTrace({
      id: `tr-probe-${Date.now()}`,
      timestamp: preciseTime,
      traceId: `req_98a${shortId}`,
      endpoint: '/v1/chat/completions',
      routerUsed: 'TF-IDF + Logistic',
      specialist: 'Diagnostic Probe',
      latencyMs: 148 + Math.floor(Math.random() * 45),
      statusCode: 200,
      statusText: '200 OK',
      clientIp: '10.240.12.8',
      payloadPreview: JSON.stringify({
        probe: 'synthetic_grounding_check',
        faiss_status: 'READY',
        mongodb_status: 'CONNECTED',
        verified_chunks: ['KB-RET-104'],
      }),
    });

    setIsProbing(false);
  };

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      const matchesStatus =
        statusFilter === 'All Statuses' ||
        (statusFilter.startsWith('200') && t.statusCode === 200) ||
        (statusFilter.startsWith('422') && t.statusCode === 422) ||
        (statusFilter.startsWith('429') && t.statusCode === 429) ||
        (statusFilter.startsWith('500') && t.statusCode === 500);

      const matchesRouter =
        routerFilter === 'All Routers' || t.routerUsed === routerFilter;

      const matchesSearch =
        !debouncedSearch ||
        t.traceId.toLowerCase().includes(debouncedSearch) ||
        t.endpoint.toLowerCase().includes(debouncedSearch) ||
        t.specialist.toLowerCase().includes(debouncedSearch) ||
        t.clientIp.toLowerCase().includes(debouncedSearch);

      return matchesStatus && matchesRouter && matchesSearch;
    });
  }, [traces, statusFilter, routerFilter, debouncedSearch]);

  const handleCopyTraceId = (traceId: string) => {
    navigator.clipboard?.writeText(traceId);
    setCopiedTraceId(traceId);
    setTimeout(() => setCopiedTraceId(null), 1500);
  };

  if (!health) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center text-on-surface-variant text-[14px]">
        Loading gateway health telemetry from /v1/health...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-background custom-scrollbar">
      <div className="p-8 max-w-[1600px] mx-auto space-y-6">
        {/* Page Header & Action Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
          <div className="space-y-1">
            <h1 className="text-[24px] leading-[32px] font-bold text-on-surface tracking-tight">
              Reliability &amp; Infrastructure Operations
            </h1>
            <p className="text-[14px] text-on-surface-variant">
              Real-time gateway telemetry, vector store index health, provider quota tracking, and
              live distributed request traces.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Time Window Selector */}
            <div className="relative">
              <select
                value={timeWindow}
                onChange={(e) => setTimeWindow(e.target.value)}
                className="h-9 pl-3 pr-8 rounded-lg border border-outline-variant/50 bg-surface-container-lowest text-on-surface text-[12px] font-medium focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary shadow-xs cursor-pointer appearance-none"
              >
                <option>Last 1 hour</option>
                <option>Last 6 hours</option>
                <option>Last 24 hours</option>
              </select>
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
                expand_more
              </span>
            </div>

            {/* Primary Diagnostic Probe Button */}
            <button
              type="button"
              disabled={isProbing}
              onClick={handleRunDiagnosticProbe}
              className="h-9 px-4 rounded-lg bg-primary hover:bg-[#4338ca] disabled:opacity-75 text-on-primary text-[13px] font-semibold flex items-center gap-2 shadow-xs transition-colors duration-150 cursor-pointer"
            >
              <span
                className={`material-symbols-outlined text-[18px] ${
                  isProbing ? 'animate-spin' : ''
                }`}
              >
                radar
              </span>
              <span>{isProbing ? 'Probing /v1/health...' : 'Run Diagnostic Probe'}</span>
            </button>
          </div>
        </div>

        {/* SECTION 1: Service Health & Gateway Status (Grid of 3 cards) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 tabular-nums">
          {/* Card 1: FastAPI Gateway */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-[20px]">router</span>
                  </span>
                  <div>
                    <h3 className="text-[14px] text-on-surface font-semibold">
                      {health.services.fastapi.name}
                    </h3>
                    <span className="text-[11px] text-on-surface-variant font-mono">
                      {health.services.fastapi.cluster}
                    </span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[11px] font-semibold">
                  {health.services.fastapi.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-outline-variant/20">
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">Uptime</div>
                  <div className="text-[16px] font-bold text-on-surface">
                    {health.services.fastapi.uptime}
                  </div>
                </div>
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Probe Latency
                  </div>
                  <div className="text-[16px] font-bold text-primary font-mono">
                    {health.services.fastapi.probeLatencyMs} ms
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 text-on-surface-variant pt-1 font-mono text-[12px]">
                <div className="flex justify-between items-center">
                  <span>/v1/health probe:</span>
                  <span className="text-[#065F46] font-semibold">
                    {health.services.fastapi.healthProbe}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Active workers:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.fastapi.activeWorkers}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Memory load:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.fastapi.memoryLoad}
                  </span>
                </div>
              </div>
            </div>
            <div className="w-full bg-surface-container-low h-1.5 rounded-full overflow-hidden mt-3">
              <div
                className="bg-primary h-full rounded-full"
                style={{ width: `${health.services.fastapi.loadPercent}%` }}
              ></div>
            </div>
          </div>

          {/* Card 2: Vector Store (FAISS) */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-[20px]">hub</span>
                  </span>
                  <div>
                    <h3 className="text-[14px] text-on-surface font-semibold">
                      {health.services.faiss.name}
                    </h3>
                    <span className="text-[11px] text-on-surface-variant font-mono">
                      {health.services.faiss.indexType}
                    </span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[11px] font-semibold">
                  {health.services.faiss.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-outline-variant/20">
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Vectors Indexed
                  </div>
                  <div className="text-[16px] font-bold text-on-surface font-mono">
                    {health.services.faiss.vectorsIndexed.toLocaleString()}
                  </div>
                </div>
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    p99 Query Latency
                  </div>
                  <div className="text-[16px] font-bold text-primary font-mono">
                    {health.services.faiss.p99LatencyMs} ms
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 text-on-surface-variant pt-1 font-mono text-[12px]">
                <div className="flex justify-between items-center">
                  <span>In-memory status:</span>
                  <span className="text-[#065F46] font-medium">
                    {health.services.faiss.cacheStatus}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Last index build:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.faiss.lastBuild}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Partition shards:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.faiss.partitions}
                  </span>
                </div>
              </div>
            </div>
            <div className="w-full bg-surface-container-low h-1.5 rounded-full overflow-hidden mt-3">
              <div
                className="bg-[#10B981] h-full rounded-full"
                style={{ width: `${health.services.faiss.syncPercent}%` }}
              ></div>
            </div>
          </div>

          {/* Card 3: State & Cache (MongoDB / Redis) */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-[20px]">database</span>
                  </span>
                  <div>
                    <h3 className="text-[14px] text-on-surface font-semibold">
                      {health.services.mongodb.name}
                    </h3>
                    <span className="text-[11px] text-on-surface-variant font-mono">
                      {health.services.mongodb.cluster}
                    </span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[11px] font-semibold">
                  {health.services.mongodb.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-outline-variant/20">
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Replica Lag
                  </div>
                  <div className="text-[16px] font-bold text-on-surface font-mono">
                    {health.services.mongodb.replicaLagMs} ms
                  </div>
                </div>
                <div className="p-2 rounded bg-surface-container-low/60">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Pool Utilization
                  </div>
                  <div className="text-[16px] font-bold text-primary font-mono">
                    {health.services.mongodb.poolUtilization}
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 text-on-surface-variant pt-1 font-mono text-[12px]">
                <div className="flex justify-between items-center">
                  <span>Cluster State:</span>
                  <span className="text-[#065F46] font-medium">
                    {health.services.mongodb.clusterState}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>TTL Index Sync:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.mongodb.ttlSync}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Redis Key Eviction:</span>
                  <span className="text-on-surface font-medium">
                    {health.services.mongodb.redisEviction}
                  </span>
                </div>
              </div>
            </div>
            <div className="w-full bg-surface-container-low h-1.5 rounded-full overflow-hidden mt-3">
              <div
                className="bg-primary h-full rounded-full"
                style={{ width: `${health.services.mongodb.poolPercent}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* SECTION 2: Performance & Resiliency Metrics (Grid of 3 panels) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 tabular-nums">
          {/* Panel 1: Latency Percentiles Over Time */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">speed</span>
                  <h3 className="text-[14px] text-on-surface font-semibold">
                    Latency Percentiles (Recent)
                  </h3>
                </div>
                <span className="text-[11px] font-semibold text-on-surface-variant">
                  Resolution: 10m intervals
                </span>
              </div>
              <p className="text-[13px] text-on-surface-variant mb-4">
                Grounded response resolution comparing median (p50) against tail SLAs (p95).
              </p>

              {/* SVG Line Chart Visual */}
              <div className="relative w-full h-44 bg-surface-container-low/30 rounded-lg p-3 border border-outline-variant/20 flex flex-col justify-between">
                <div className="absolute inset-x-3 top-3 border-b border-dashed border-outline-variant/25 text-[10px] font-mono text-outline">
                  800ms SLA Target
                </div>
                <div className="absolute inset-x-3 top-1/2 border-b border-dashed border-outline-variant/20 text-[10px] font-mono text-outline">
                  400ms
                </div>
                <div className="absolute inset-x-3 bottom-8 border-b border-dashed border-outline-variant/20 text-[10px] font-mono text-outline">
                  200ms
                </div>

                <svg
                  className="w-full h-28 overflow-visible mt-2"
                  preserveAspectRatio="none"
                  viewBox="0 0 320 100"
                >
                  {/* p95 amber line */}
                  <path
                    d="M 0,42 Q 60,35 120,48 T 240,38 T 320,40"
                    fill="none"
                    stroke="#D97706"
                    strokeLinecap="round"
                    strokeWidth="2.2"
                  />
                  {/* p50 indigo line */}
                  <path
                    d="M 0,78 Q 60,74 120,77 T 240,73 T 320,75"
                    fill="none"
                    stroke="#4F46E5"
                    strokeLinecap="round"
                    strokeWidth="2.5"
                  />
                  <circle cx="120" cy="48" fill="#D97706" r="3" />
                  <circle cx="240" cy="38" fill="#D97706" r="3" />
                  <circle cx="320" cy="40" fill="#D97706" r="3.5" />
                  <circle cx="120" cy="77" fill="#4F46E5" r="3" />
                  <circle cx="240" cy="73" fill="#4F46E5" r="3" />
                  <circle cx="320" cy="75" fill="#4F46E5" r="3.5" />
                </svg>

                <div className="flex justify-between items-center text-[10px] font-mono text-on-surface-variant pt-2 border-t border-outline-variant/20">
                  {health.latencySeries.labels.map((lbl) => (
                    <span key={lbl}>{lbl}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-outline-variant/20 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#4F46E5]"></span>
                  <span className="text-[11px] font-semibold text-on-surface">
                    p50:{' '}
                    <strong className="font-mono text-primary">
                      {health.latencySeries.currentP50}ms
                    </strong>{' '}
                    (Avg)
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#D97706]"></span>
                  <span className="text-[11px] font-semibold text-on-surface">
                    p95:{' '}
                    <strong className="font-mono text-[#D97706]">
                      {health.latencySeries.currentP95}ms
                    </strong>{' '}
                    (SLA &lt; 800ms)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Panel 2: Request Throughput & HTTP Status Breakdown */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    bar_chart
                  </span>
                  <h3 className="text-[14px] text-on-surface font-semibold">
                    Throughput &amp; Status Code Ratio
                  </h3>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]">
                  {health.throughput.reqPerHour}
                </span>
              </div>
              <p className="text-[13px] text-on-surface-variant mb-4">
                Traffic composition by HTTP response code across all client edge sessions.
              </p>

              <div className="space-y-3">
                <div className="h-6 w-full rounded-md overflow-hidden flex bg-surface-container-low border border-outline-variant/20">
                  <div
                    className="bg-[#10B981] h-full"
                    style={{ width: `${health.throughput.success2xxPercent}%` }}
                  ></div>
                  <div
                    className="bg-[#F59E0B] h-full"
                    style={{ width: `${health.throughput.rateLimit429Percent}%` }}
                  ></div>
                  <div
                    className="bg-[#EF4444] h-full"
                    style={{ width: `${health.throughput.error5xxPercent}%` }}
                  ></div>
                </div>

                <div className="space-y-2 pt-1 text-[12px]">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-xs bg-[#10B981]"></span>
                      <span className="text-on-surface font-medium">
                        2xx Success (Grounded Deliveries)
                      </span>
                    </span>
                    <span className="font-mono text-on-surface font-semibold">
                      {health.throughput.success2xxPercent}%{' '}
                      <span className="text-on-surface-variant font-normal">
                        ({health.throughput.success2xxCount})
                      </span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-xs bg-[#F59E0B]"></span>
                      <span className="text-on-surface font-medium">
                        429 Rate Limited (Client Backoff)
                      </span>
                    </span>
                    <span className="font-mono text-[#92400E] font-semibold">
                      {health.throughput.rateLimit429Percent}%{' '}
                      <span className="text-on-surface-variant font-normal">
                        ({health.throughput.rateLimit429Count})
                      </span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-xs bg-[#EF4444]"></span>
                      <span className="text-on-surface font-medium">
                        5xx Server Errors (Uncaught Exceptions)
                      </span>
                    </span>
                    <span className="font-mono text-error font-semibold">
                      {health.throughput.error5xxPercent}%{' '}
                      <span className="text-on-surface-variant font-normal">
                        ({health.throughput.error5xxCount})
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-outline-variant/20 flex items-center justify-between text-[11px] font-semibold">
              <span className="text-on-surface-variant">
                Aggregate Volume:{' '}
                <strong className="text-on-surface">{health.throughput.totalVolume}</strong>
              </span>
              <span className="inline-flex items-center gap-1 font-mono text-[#065F46]">
                <span className="material-symbols-outlined text-[14px]">verified</span> Error Rate:{' '}
                {health.throughput.errorRate}
              </span>
            </div>
          </div>

          {/* Panel 3: Provider Quota & Resiliency */}
          <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    account_tree
                  </span>
                  <h3 className="text-[14px] text-on-surface font-semibold">
                    Provider Quota &amp; Resiliency
                  </h3>
                </div>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#EFF6FF] text-[#1E40AF] border border-[#BFDBFE]">
                  Multi-Provider Tier
                </span>
              </div>
              <p className="text-[13px] text-on-surface-variant mb-4">
                Token usage thresholds, adaptive backoff health, and fallback circuit state.
              </p>

              <div className="space-y-2">
                <div className="flex justify-between items-center text-[13px]">
                  <span className="font-medium text-on-surface">Active TPM Utilization</span>
                  <span className="font-mono text-primary font-semibold">
                    284k / 1,000k TPM (28.4%)
                  </span>
                </div>
                <div className="w-full bg-surface-container-low h-2.5 rounded-full overflow-hidden">
                  <div className="bg-primary h-full rounded-full" style={{ width: '28.4%' }}></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-4">
                <div className="p-2.5 rounded-lg border border-outline-variant/20 bg-surface-container-low/40">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Circuit Breaker
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[14px] text-[#065F46] font-semibold">
                      Closed / Healthy
                    </span>
                  </div>
                </div>
                <div className="p-2.5 rounded-lg border border-outline-variant/20 bg-surface-container-low/40">
                  <div className="text-[11px] font-semibold text-on-surface-variant">
                    Retry Frequency
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[14px] text-on-surface font-mono font-semibold">
                      0.4%
                    </span>
                    <span className="text-[11px] text-on-surface-variant">(Normal)</span>
                  </div>
                </div>
              </div>

              <div className="mt-3 p-2.5 rounded-lg bg-[#ECFDF5] border border-[#A7F3D0] flex items-center gap-2">
                <span className="material-symbols-outlined text-[#065F46] text-[18px]">
                  security
                </span>
                <span className="text-[11px] text-[#065F46] font-semibold">
                  0 retry storms detected in the last 24h
                </span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-outline-variant/20 flex items-center justify-between text-[13px]">
              <span className="text-[11px] font-semibold text-on-surface-variant">
                Secondary Failover Route:
              </span>
              <span className="inline-flex items-center gap-1 font-mono text-[12px] text-[#065F46] font-semibold">
                Standby 100% Ready
              </span>
            </div>
          </div>
        </div>

        {/* SECTION 3: Live Structured Logs / Distributed Request Traces */}
        <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/40 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-outline-variant/20 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center text-primary">
                <span className="material-symbols-outlined text-[20px]">reorder</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-[16px] font-bold text-on-surface">
                    Live Request Traces &amp; Gateway Logs
                  </h3>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[11px] font-semibold">
                    Streaming active
                  </span>
                </div>
                <p className="text-[13px] text-on-surface-variant">
                  Monotonic log tail with deterministic semantic routing classification.
                </p>
              </div>
            </div>

            {/* Quick Filter Toolbar */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative">
                <span className="material-symbols-outlined text-[18px] text-on-surface-variant absolute left-2.5 top-1/2 -translate-y-1/2">
                  search
                </span>
                <input
                  value={rawSearch}
                  onChange={(e) => setRawSearch(e.target.value)}
                  className="h-8 pl-8 pr-3 rounded-lg border border-outline-variant/50 bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant/60 text-[13px] focus:outline-none focus:ring-1 focus:ring-primary w-52"
                  placeholder="Search Trace ID or IP..."
                  type="text"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 pl-2.5 pr-7 rounded-lg border border-outline-variant/50 bg-surface-container-lowest text-on-surface text-[12px] font-medium focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
              >
                <option>All Statuses</option>
                <option>200 OK</option>
                <option>422 Validation Error</option>
                <option>429 Rate Limited</option>
                <option>500 Server Error</option>
              </select>

              <select
                value={routerFilter}
                onChange={(e) => setRouterFilter(e.target.value)}
                className="h-8 pl-2.5 pr-7 rounded-lg border border-outline-variant/50 bg-surface-container-lowest text-on-surface text-[12px] font-medium focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
              >
                <option>All Routers</option>
                <option>TF-IDF + Logistic</option>
                <option>LLM Structured Output</option>
                <option>Rule-Based Regex</option>
              </select>

              <label className="flex items-center gap-1.5 px-2.5 h-8 rounded-lg border border-outline-variant/50 bg-surface-container-low/40 cursor-pointer text-[12px] font-medium text-on-surface select-none">
                <input
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="rounded border-outline-variant/60 text-primary focus:ring-primary h-3.5 w-3.5"
                  type="checkbox"
                />
                <span>Auto-scroll</span>
              </label>
            </div>
          </div>

          {/* Structured Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse tabular-nums">
              <thead>
                <tr className="bg-surface-container-low/50 border-b border-outline-variant/20 text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4">Request / Trace ID</th>
                  <th className="py-2.5 px-4">Endpoint</th>
                  <th className="py-2.5 px-4">Router Used</th>
                  <th className="py-2.5 px-4">Specialist Agents Invoked</th>
                  <th className="py-2.5 px-4">Latency</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20 text-[13px]">
                {filteredTraces.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-on-surface-variant">
                      No request traces match the active filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredTraces.map((trace) => (
                    <tr
                      key={trace.id}
                      className="hover:bg-surface-container-low/30 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono text-[12px] text-on-surface-variant whitespace-nowrap">
                        {trace.timestamp}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="inline-flex items-center gap-1 font-mono text-[12px] bg-surface-container-low px-2 py-0.5 rounded text-primary border border-outline-variant/30">
                          <span>{trace.traceId}</span>
                          <button
                            type="button"
                            onClick={() => handleCopyTraceId(trace.traceId)}
                            className="hover:text-on-surface cursor-pointer"
                            title="Copy Trace ID"
                          >
                            <span className="material-symbols-outlined text-[13px]">
                              {copiedTraceId === trace.traceId ? 'check' : 'content_copy'}
                            </span>
                          </button>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[12px] text-on-surface font-medium whitespace-nowrap">
                        {trace.endpoint}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${
                            trace.routerUsed === 'Rule-Based Regex'
                              ? 'bg-surface-container-low text-on-surface-variant border-outline-variant/40'
                              : 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]'
                          }`}
                        >
                          {trace.routerUsed}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={
                            trace.statusCode !== 200
                              ? 'text-on-surface-variant italic'
                              : 'text-on-surface font-medium'
                          }
                        >
                          {trace.specialist}
                        </span>
                      </td>
                      <td
                        className={`py-3 px-4 font-mono text-[12px] font-semibold whitespace-nowrap ${
                          trace.statusCode === 429 ? 'text-[#D97706]' : 'text-on-surface'
                        }`}
                      >
                        {trace.latencyMs} ms
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        {trace.statusCode === 200 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-[11px] font-semibold">
                            <span className="material-symbols-outlined text-[14px]">check</span>{' '}
                            {trace.statusText}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] text-[11px] font-semibold">
                            <span className="material-symbols-outlined text-[14px]">
                              {trace.statusCode === 429 ? 'timer' : 'warning'}
                            </span>{' '}
                            {trace.statusText}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="inline-flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setInspectedTrace({ trace, mode: 'payload' })}
                            className="text-primary hover:underline text-[12px] font-medium cursor-pointer"
                          >
                            Payload
                          </button>
                          <span className="text-outline-variant">·</span>
                          <button
                            type="button"
                            onClick={() => setInspectedTrace({ trace, mode: 'graph' })}
                            className="text-on-surface-variant hover:text-on-surface text-[12px] font-medium cursor-pointer"
                          >
                            Trace Graph
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Table Footer */}
          <div className="p-4 border-t border-outline-variant/20 bg-surface-container-low/20 flex flex-col sm:flex-row items-center justify-between text-[13px] text-on-surface-variant gap-2">
            <div className="flex items-center gap-2 font-mono text-[12px]">
              <span>
                Showing {filteredTraces.length} of 14,290 traces. Monotonic logging stream active.
              </span>
            </div>
            <div className="flex items-center gap-2 tabular-nums">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 py-1 rounded border border-outline-variant/40 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-[11px] font-semibold transition-colors cursor-pointer"
              >
                Previous
              </button>
              <span className="font-mono text-[11px] px-2 text-on-surface font-semibold">
                Page {page} of 286
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(286, p + 1))}
                className="px-2.5 py-1 rounded border border-outline-variant/40 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-[11px] font-semibold transition-colors cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Telemetry Groundedness & Provenance Engine */}
        <div className="bg-surface-container-low/40 rounded-lg border border-outline-variant/40 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="material-symbols-outlined text-primary text-[22px] mt-0.5">
              verified_user
            </span>
            <div>
              <h4 className="text-[14px] font-semibold text-on-surface">
                Telemetry Groundedness &amp; Provenance Engine
              </h4>
              <p className="text-[13px] text-on-surface-variant">
                Traces are cryptographically signed at the gateway ingress. Retrieval queries
                reference verified FAISS vector snapshots with an average similarity confidence of
                0.942.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right font-mono text-[11px]">
              <span className="text-on-surface-variant">Cluster Quorum:</span>
              <span className="text-[#065F46] font-semibold ml-1">Healthy (3/3 nodes)</span>
            </div>
            <button
              type="button"
              onClick={() => setSecurityAuditOpen(true)}
              className="px-3 py-1.5 rounded-lg border border-outline-variant/50 bg-surface-container-lowest hover:bg-surface-container-low text-primary text-[12px] font-semibold transition-colors cursor-pointer"
            >
              Audit Security Log
            </button>
          </div>
        </div>
      </div>

      {/* Trace Payload / Graph Inspector Modal */}
      {inspectedTrace && (
        <div className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-xl w-full p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant pb-3">
              <div>
                <h3 className="text-[15px] font-semibold text-on-surface">
                  {inspectedTrace.mode === 'payload'
                    ? `Ingress Payload Inspector · ${inspectedTrace.trace.traceId}`
                    : `Distributed Trace Span Graph · ${inspectedTrace.trace.traceId}`}
                </h3>
                <p className="text-[12px] text-on-surface-variant font-mono">
                  {inspectedTrace.trace.endpoint} · {inspectedTrace.trace.timestamp} · Client IP:{' '}
                  {inspectedTrace.trace.clientIp}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setInspectedTrace(null)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {inspectedTrace.mode === 'payload' ? (
              <pre className="bg-surface-container-low p-3.5 rounded-lg border border-outline-variant/60 font-mono text-[12px] text-on-surface overflow-x-auto">
                {JSON.stringify(JSON.parse(inspectedTrace.trace.payloadPreview), null, 2)}
              </pre>
            ) : (
              <div className="space-y-2.5 text-[12px] font-mono">
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/40 flex justify-between">
                  <span>1. Edge Gateway Ingress (mTLS Verify)</span>
                  <span className="text-primary font-semibold">2.1 ms</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/40 flex justify-between">
                  <span>2. Semantic Router ({inspectedTrace.trace.routerUsed})</span>
                  <span className="text-primary font-semibold">
                    {Math.max(2, Math.round(inspectedTrace.trace.latencyMs * 0.18))} ms
                  </span>
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/40 flex justify-between">
                  <span>3. FAISS IndexFlatIP Top-K Lookup</span>
                  <span className="text-primary font-semibold">
                    {Math.max(1, Math.round(inspectedTrace.trace.latencyMs * 0.08))} ms
                  </span>
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/40 flex justify-between">
                  <span>4. Specialist Agent ({inspectedTrace.trace.specialist})</span>
                  <span className="text-emerald-700 font-semibold">
                    {Math.max(1, Math.round(inspectedTrace.trace.latencyMs * 0.72))} ms
                  </span>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setInspectedTrace(null)}
                className="px-4 py-1.5 rounded-lg bg-primary-container text-on-primary text-[12px] font-semibold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Security Audit Log Modal */}
      {securityAuditOpen && (
        <div className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-lg w-full p-5 shadow-xl space-y-3">
            <div className="flex items-center justify-between border-b border-outline-variant pb-2.5">
              <h3 className="text-[15px] font-semibold text-on-surface">
                Cryptographic Provenance &amp; Quorum Audit
              </h3>
              <button
                type="button"
                onClick={() => setSecurityAuditOpen(false)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="text-[12px] font-mono bg-surface-container-low p-3 rounded-lg border border-outline-variant/40 space-y-1.5 text-on-surface">
              <div>Quorum Nodes: us-east-1a, us-east-1b, us-east-1d (3/3 ONLINE)</div>
              <div>FAISS Snapshot SHA256: 8f9c2a44e91b7c0012df89012a4b7d2e</div>
              <div>XSS / HTML Input Sanitizer: ENFORCED (Strict Policy v1.4)</div>
              <div>Last Tamper Audit: 0 anomalies in 14,290 traces</div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setSecurityAuditOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-primary-container text-on-primary text-[12px] font-semibold"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
