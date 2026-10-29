import React, { useState } from 'react';
import { BrandLogo } from './BrandLogo';
import { apiClient } from '../services/apiClient';

interface AuthViewProps {
  sessionExpiredNotice?: boolean;
  onAuthenticated: (authPayload: {
    token: string;
    user: { name: string; email: string; role: string; initials: string };
  }) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({
  sessionExpiredNotice = true,
  onAuthenticated,
}) => {
  const [identifier, setIdentifier] = useState('eng-ops@techmart.internal');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [showSessionBanner, setShowSessionBanner] = useState(sessionExpiredNotice);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [authStatus, setAuthStatus] = useState<'idle' | 'loading' | 'verified' | 'sso'>('idle');
  const [infoModal, setInfoModal] = useState<'docs' | 'security' | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!identifier.trim()) {
      setErrorMessage('Corporate Email or Username is required.');
      return;
    }
    if (!password || password.trim().length < 4) {
      setErrorMessage('Password must be at least 4 characters.');
      return;
    }

    setAuthStatus('loading');
    try {
      const response = await apiClient.login(identifier, password);
      setAuthStatus('verified');
      setTimeout(() => {
        onAuthenticated({
          token: response.access_token,
          user: response.user,
        });
      }, 450);
    } catch (err) {
      setAuthStatus('idle');
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Invalid credentials or gateway authentication failure.'
      );
    }
  };

  const handleSSO = async () => {
    setErrorMessage(null);
    setAuthStatus('sso');
    try {
      const response = await apiClient.login(
        identifier.trim() || 'eng-ops@techmart.internal',
        'okta-sso-assertion-token'
      );
      setAuthStatus('verified');
      setTimeout(() => {
        onAuthenticated({
          token: response.access_token,
          user: response.user,
        });
      }, 450);
    } catch (err) {
      setAuthStatus('idle');
      setErrorMessage(err instanceof Error ? err.message : 'SSO handshake failed.');
    }
  };

  return (
    <div className="bg-background text-on-surface min-h-screen flex flex-col justify-between antialiased relative overflow-x-hidden">
      {/* Subtle Ambient Top Grid / Decorative Horizon */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-40">
        <div className="absolute -top-[300px] left-1/2 -translate-x-1/2 w-[900px] h-[550px] bg-gradient-to-b from-primary-fixed/30 via-surface-container-low/20 to-transparent blur-3xl"></div>
        <div className="absolute inset-0 bg-[radial-gradient(#c7c4d8_1px,transparent_1px)] [background-size:24px_24px] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_35%,#000_60%,transparent_100%)] opacity-30"></div>
      </div>

      {/* Main Centered Authentication Card */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-[440px] bg-surface-container-lowest border border-outline-variant/40 rounded-xl shadow-[0_1px_3px_0_rgba(15,23,42,0.06),0_1px_2px_-1px_rgba(15,23,42,0.04)] overflow-hidden transition-all duration-200">
          {/* Top Accent Line */}
          <div className="h-1 w-full bg-gradient-to-r from-primary-container via-primary to-secondary-container"></div>

          <div className="p-6 sm:p-8">
            {/* Header Section */}
            <header className="flex flex-col items-center text-center">
              <div className="relative w-11 h-11 mb-3 rounded-lg flex items-center justify-center bg-surface-container-low border border-outline-variant/30 shadow-xs">
                <BrandLogo className="w-8 h-8" />
              </div>

              <h1 className="text-[20px] leading-[28px] font-semibold text-on-surface tracking-tight">
                TechMart Support AI
              </h1>
              <p className="text-[13px] leading-[18px] text-on-surface-variant mt-0.5">
                Intelligent Support. Grounded Answers.
              </p>

              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mt-3 rounded-full bg-surface-container-low border border-outline-variant/30 text-on-surface-variant text-[11px] font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-tertiary-container"></span>
                <span>v1.4 Production Gateway</span>
              </div>
            </header>

            {/* Session Expiration Alert Banner */}
            {showSessionBanner && !errorMessage && (
              <aside
                className="mt-5 p-3 rounded-lg bg-surface-container border border-outline-variant/40 text-on-surface flex items-start gap-2.5 transition-all duration-200"
                role="alert"
              >
                <span className="material-symbols-outlined text-secondary text-[18px] shrink-0 mt-0.5">
                  info
                </span>
                <div className="flex-1 text-left">
                  <p className="text-[13px] leading-snug text-on-surface-variant">
                    <strong className="font-semibold text-on-surface">
                      Session expired due to inactivity.
                    </strong>{' '}
                    Please sign in to resume your active telemetry and chat stream.
                  </p>
                </div>
                <button
                  aria-label="Dismiss alert"
                  className="text-outline hover:text-on-surface transition-colors p-0.5 -mr-1 -mt-1 rounded"
                  onClick={() => setShowSessionBanner(false)}
                  type="button"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              </aside>
            )}

            {/* Validation / Invalid Credentials Error Banner */}
            {errorMessage && (
              <aside
                className="mt-5 p-3 rounded-lg bg-error-container/70 border border-error/30 text-on-error-container flex items-start gap-2.5 transition-all duration-200"
                role="alert"
              >
                <span className="material-symbols-outlined text-error text-[18px] shrink-0 mt-0.5">
                  error
                </span>
                <div className="flex-1 text-left">
                  <p className="text-[13px] leading-snug text-on-error-container">
                    <strong className="font-semibold">Authentication Error:</strong> {errorMessage}
                  </p>
                </div>
                <button
                  aria-label="Dismiss error"
                  className="text-on-error-container/70 hover:text-on-error-container transition-colors p-0.5 -mr-1 -mt-1 rounded"
                  onClick={() => setErrorMessage(null)}
                  type="button"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              </aside>
            )}

            {/* Authentication Form */}
            <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
              {/* Field 1: Email or Username */}
              <div className="space-y-1.5 text-left">
                <label
                  className="block text-[12px] leading-[16px] font-medium text-on-surface"
                  htmlFor="identifier"
                >
                  Email or Username <span className="text-error font-bold">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-[18px]">person</span>
                  </div>
                  <input
                    className="block w-full pl-9 pr-3 py-2 text-[14px] leading-[22px] bg-surface-container-lowest border border-outline-variant rounded-lg text-on-surface placeholder:text-outline focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/20 transition-all duration-150"
                    id="identifier"
                    name="identifier"
                    placeholder="eng-ops@techmart.internal"
                    required
                    type="text"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                  />
                </div>
              </div>

              {/* Field 2: Password */}
              <div className="space-y-1.5 text-left">
                <div className="flex items-center justify-between">
                  <label
                    className="block text-[12px] leading-[16px] font-medium text-on-surface"
                    htmlFor="password"
                  >
                    Password <span className="text-error font-bold">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setErrorMessage(
                        'Password reset requires corporate Okta MFA verification or contacting Tier-3 SecOps.'
                      )
                    }
                    className="text-[11px] font-semibold text-primary-container hover:text-primary transition-colors focus:outline-none focus:underline"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-[18px]">lock</span>
                  </div>
                  <input
                    className="block w-full pl-9 pr-10 py-2 text-[14px] leading-[22px] bg-surface-container-lowest border border-outline-variant rounded-lg text-on-surface placeholder:text-outline focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/20 tracking-wider transition-all duration-150"
                    id="password"
                    name="password"
                    placeholder="Enter corporate credentials"
                    required
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    aria-label="Toggle password visibility"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-outline hover:text-on-surface focus:outline-none"
                    onClick={() => setShowPassword((prev) => !prev)}
                    type="button"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {showPassword ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Options Row: Remember Me & SSO indicator */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-outline-variant text-primary-container focus:ring-primary-container/30 focus:ring-offset-0 cursor-pointer"
                    id="remember"
                    name="remember"
                    type="checkbox"
                  />
                  <span className="text-[13px] text-on-surface-variant">
                    Keep session active for 12 hours
                  </span>
                </label>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-tertiary bg-tertiary-fixed/30 px-2 py-0.5 rounded">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>
                  SSO Ready
                </span>
              </div>

              {/* Primary Submit Action */}
              <div className="pt-2">
                <button
                  disabled={authStatus === 'loading' || authStatus === 'verified'}
                  className={`w-full h-10 px-4 flex items-center justify-center gap-2 rounded-lg text-on-primary text-[14px] font-semibold transition-all duration-150 shadow-sm hover:shadow active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-primary-container/40 ${
                    authStatus === 'verified'
                      ? 'bg-tertiary-container'
                      : 'bg-primary-container hover:bg-primary'
                  } ${authStatus === 'loading' ? 'opacity-90 cursor-wait' : ''}`}
                  type="submit"
                >
                  <span>
                    {authStatus === 'loading'
                      ? 'Authenticating via /v1/auth/login...'
                      : authStatus === 'verified'
                      ? 'Session Verified'
                      : 'Sign In to Gateway'}
                  </span>
                  <span
                    className={`material-symbols-outlined text-[18px] ${
                      authStatus === 'loading' ? 'animate-spin' : ''
                    }`}
                  >
                    {authStatus === 'loading'
                      ? 'sync'
                      : authStatus === 'verified'
                      ? 'check_circle'
                      : 'arrow_forward'}
                  </span>
                </button>
              </div>
            </form>

            {/* SSO Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-outline-variant/30"></div>
              </div>
              <div className="relative flex justify-center text-center">
                <span className="bg-surface-container-lowest px-3 text-[11px] font-semibold text-outline uppercase tracking-wider">
                  or authenticate via enterprise identity
                </span>
              </div>
            </div>

            {/* SSO Button */}
            <button
              onClick={handleSSO}
              disabled={authStatus !== 'idle'}
              className="w-full h-10 px-4 flex items-center justify-center gap-2.5 rounded-lg border border-outline-variant/60 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface text-[14px] font-semibold transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary-container/20"
              type="button"
            >
              <span
                className={`material-symbols-outlined text-secondary text-[20px] ${
                  authStatus === 'sso' ? 'animate-spin' : ''
                }`}
              >
                {authStatus === 'sso' ? 'sync' : 'fingerprint'}
              </span>
              <span>
                {authStatus === 'sso'
                  ? 'Redirecting to Okta Identity Provider...'
                  : 'Sign in with Okta / SSO'}
              </span>
            </button>
          </div>

          {/* Bottom Inset Telemetry Strip */}
          <div className="px-6 py-2.5 bg-surface-container-low/60 border-t border-outline-variant/30 flex items-center justify-between text-on-surface-variant text-[11px] font-semibold">
            <span className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-tertiary-container text-[14px]">
                verified_user
              </span>
              mTLS Handshake Active
            </span>
            <span className="font-mono text-outline">region: us-east-1</span>
          </div>
        </div>

        {/* Security Note & Protocol Badges Below Card */}
        <div className="mt-6 flex flex-col items-center text-center space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-lowest border border-outline-variant/40 shadow-xs text-on-surface-variant text-[11px] font-semibold">
            <span className="material-symbols-outlined text-primary-container text-[15px]">
              shield
            </span>
            <span>Protected by JWT Session Authentication &amp; Strict Rate Limiting (v1.4)</span>
          </div>

          <nav className="flex items-center justify-center gap-4 text-on-surface-variant text-[13px] pt-1">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-tertiary"></span>
              <span>
                API Status: <span className="font-medium text-tertiary">Operational</span>
              </span>
            </span>
            <span className="text-outline-variant">·</span>
            <button
              type="button"
              onClick={() => setInfoModal('docs')}
              className="hover:text-primary-container hover:underline transition-colors"
            >
              Docs &amp; OpenID Config
            </button>
            <span className="text-outline-variant">·</span>
            <button
              type="button"
              onClick={() => setInfoModal('security')}
              className="hover:text-primary-container hover:underline transition-colors"
            >
              Security Compliance
            </button>
          </nav>
        </div>
      </main>

      {/* Info Modal for OpenID / Security Compliance */}
      {infoModal && (
        <div className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-md w-full p-5 shadow-xl space-y-3">
            <div className="flex items-center justify-between border-b border-outline-variant/40 pb-2.5">
              <h3 className="text-[15px] font-semibold text-on-surface">
                {infoModal === 'docs'
                  ? 'OpenID Connect & /v1 Gateway Config'
                  : 'Enterprise Security Compliance'}
              </h3>
              <button
                type="button"
                onClick={() => setInfoModal(null)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
            {infoModal === 'docs' ? (
              <div className="text-[12px] font-mono bg-surface-container-low p-3 rounded-lg border border-outline-variant/40 space-y-1 text-on-surface">
                <div>issuer: https://gateway.techmart.internal/v1</div>
                <div>token_endpoint: POST /v1/auth/login</div>
                <div>jwks_uri: /v1/.well-known/jwks.json</div>
                <div>grant_types: [&quot;password&quot;, &quot;urn:ietf:params:oauth:grant-type:jwt-bearer&quot;]</div>
              </div>
            ) : (
              <p className="text-[13px] text-on-surface-variant leading-relaxed">
                All support sessions are encrypted end-to-end with AES-256-GCM. Prompts are
                sanitized at ingress before FAISS vector lookup and logged with cryptographic
                provenance signatures.
              </p>
            )}
            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={() => setInfoModal(null)}
                className="px-3.5 py-1.5 rounded-lg bg-primary-container text-on-primary text-[12px] font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Global Footer Copyright / Grounding Anchor */}
      <footer className="relative z-10 py-4 text-center text-[11px] font-semibold text-outline border-t border-outline-variant/20 bg-surface-container-lowest/70 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-on-surface">TechMart Support AI</span>
            <span>— Grounded Answers Platform</span>
          </div>
          <div>
            <span>Encrypted end-to-end (AES-256-GCM) · Enterprise Partition 09</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
