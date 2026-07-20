import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Sun, Moon, Lock, Mail } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import logoImg from "../assets/logo.png";

type Mode = "login" | "otp" | "forgot" | "forgot-sent";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, verifyOtp, requestPasswordReset, user } = useAuthStore();
  const { theme, setTheme, initializeUi } = useUiStore();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const inputRefs = React.useRef<(HTMLInputElement | null)[]>([]);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleOtpChange = (value: string, index: number) => {
    if (value && !/^\d$/.test(value)) return;

    const newDigits = [...otpDigits];
    newDigits[index] = value;
    setOtpDigits(newDigits);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Backspace") {
      if (!otpDigits[index] && index > 0) {
        const newDigits = [...otpDigits];
        newDigits[index - 1] = "";
        setOtpDigits(newDigits);
        inputRefs.current[index - 1]?.focus();
      } else {
        const newDigits = [...otpDigits];
        newDigits[index] = "";
        setOtpDigits(newDigits);
      }
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim();
    if (!/^\d{1,6}$/.test(pastedData)) return;

    const newDigits = [...otpDigits];
    for (let i = 0; i < Math.min(pastedData.length, 6); i++) {
      newDigits[i] = pastedData[i];
    }
    setOtpDigits(newDigits);

    const focusIndex = Math.min(pastedData.length, 5);
    inputRefs.current[focusIndex]?.focus();
  };

  // Auth state is now hydrated once at the App level (see App.tsx) so it's
  // available on any route, not just this page.
  useEffect(() => {
    initializeUi();
  }, [initializeUi]);

  useEffect(() => {
    // If already authenticated, redirect to the right area
    if (user?.isAuthenticated) {
      navigate(user.role === "admin" ? "/admin" : "/chat");
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please fill in both email and password fields.");
      return;
    }

    setLoading(true);
    const res = await login(email.trim(), password.trim(), rememberMe);
    setLoading(false);

    if (!res.success) {
      setError(res.error || "Login failed");
      return;
    }

    if (res.requiresOtp) {
      setMode("otp");
      return;
    }

    if (res.role === "admin") {
      localStorage.setItem("admin_authenticated", "true");
      navigate("/admin");
    } else {
      navigate("/chat");
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const fullOtp = otpDigits.join("");
    if (fullOtp.length < 6) {
      setError("Please enter all 6 digits of the verification code.");
      return;
    }

    setLoading(true);
    const res = await verifyOtp(fullOtp);
    setLoading(false);

    if (!res.success) {
      setError(res.error || "Verification failed");
      return;
    }

    localStorage.setItem("admin_authenticated", "true");
    navigate("/admin");
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("Enter your email first.");
      return;
    }

    setLoading(true);
    const res = await requestPasswordReset(email.trim());
    setLoading(false);

    if (!res.success) {
      setError(res.error || "Something went wrong");
      return;
    }

    setMode("forgot-sent");
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center p-6 font-sans select-none relative overflow-hidden bg-bg text-text">
      {/* Soft ambient glow accents, iOS-wallpaper style */}
      <div className="pointer-events-none absolute -top-32 -left-24 w-96 h-96 rounded-full bg-accent/20 blur-[100px]" />
      <div className="pointer-events-none absolute -bottom-32 -right-24 w-96 h-96 rounded-full bg-teal/25 blur-[100px]" />

      {/* Top Right Floating Theme Toggle */}
      <div className="absolute top-6 right-6 z-10">
        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-full border border-border bg-surface/60 hover:bg-surface-hover text-warning transition-all cursor-pointer flex items-center justify-center shadow-sm glass-panel"
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Logo and Greeting */}
        {mode !== "otp" && (
          <div className="text-center space-y-2 animate-fade-in">
            <div className="w-14 h-14 bg-accent rounded-[1.1rem] flex items-center justify-center shadow-lg shadow-accent/30 mx-auto">
              <img src={logoImg} alt="Lapis AI Logo" className="w-8 h-8 object-contain invert brightness-0" />
            </div>
            <h2 className="text-xl font-extrabold tracking-wide text-text">
              Lapis AI Analyst
            </h2>
            <p className="text-xs text-text-muted">
              {mode === "forgot" || mode === "forgot-sent"
                ? "Reset your password"
                : "Sign in to start natural language retail queries"}
            </p>
          </div>
        )}

        {/* Card */}
        <div className="p-8 rounded-[1.75rem] border border-border shadow-xl transition-all duration-300 bg-surface glass-panel">
          {mode === "login" && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-[11px] font-bold text-left leading-relaxed">
                  {error}
                </div>
              )}

              <Input
                label="Email Address"
                type="email"
                placeholder="you@lapisai.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<Mail className="w-4 h-4" />}
                required
              />

              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock className="w-4 h-4" />}
                required
              />

              <div className="flex items-center justify-between text-xs pt-1 select-none">
                <label className="flex items-center gap-2 font-semibold text-text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-border bg-surface-2 text-accent focus:ring-accent"
                  />
                  Remember Me
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setError("");
                    setMode("forgot");
                  }}
                  className="text-[10px] text-accent font-bold hover:underline cursor-pointer"
                >
                  Forgot Password?
                </button>
              </div>

              <Button type="submit" className="w-full mt-2" isLoading={loading}>
                Sign In
              </Button>
            </form>
          )}

          {mode === "otp" && (
            <form onSubmit={handleVerifyOtp} className="space-y-6">
              <div className="text-center">
                {/* Circular envelope icon */}
                <div className="w-16 h-16 rounded-full bg-accent-soft text-accent flex items-center justify-center mx-auto mb-4 border border-accent/10">
                  <Mail className="w-7 h-7" />
                </div>

                <h3 className="text-xl font-bold text-text mb-1">
                  Verify Your Email
                </h3>
                <p className="text-xs text-text-muted leading-relaxed">
                  Please Enter The Verification Code We Sent To{" "}
                  <span className="font-bold text-text-muted break-all">{email}</span>
                </p>
              </div>

              {error && (
                <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-[11px] font-bold text-left leading-relaxed">
                  {error}
                </div>
              )}

              {/* 6 Digit Inputs */}
              <div className="flex justify-between gap-2 max-w-sm mx-auto my-6">
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => { inputRefs.current[idx] = el; }}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(e.target.value, idx)}
                    onKeyDown={(e) => handleOtpKeyDown(e, idx)}
                    onPaste={handleOtpPaste}
                    className="w-11 h-14 sm:w-12 sm:h-16 text-center text-xl font-bold rounded-xl border border-border bg-surface-2 text-text focus:ring-2 focus:ring-accent focus:border-accent focus:outline-none transition-all"
                  />
                ))}
              </div>

              {/* Confirm Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-accent hover:opacity-90 active:scale-98 text-white font-semibold py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-accent/20 text-sm flex items-center justify-center"
              >
                {loading ? "Verifying..." : "Confirm"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setError("");
                  setOtpDigits(["", "", "", "", "", ""]);
                  setMode("login");
                }}
                className="w-full text-center text-xs font-semibold text-text-muted hover:underline cursor-pointer pt-2"
              >
                Back to sign in
              </button>
            </form>
          )}

          {mode === "forgot" && (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              {error && (
                <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-[11px] font-bold text-left leading-relaxed">
                  {error}
                </div>
              )}

              <Input
                label="Email Address"
                type="email"
                placeholder="you@lapisai.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<Mail className="w-4 h-4" />}
                required
              />

              <Button type="submit" className="w-full mt-2" isLoading={loading}>
                Send Reset Link
              </Button>

              <button
                type="button"
                onClick={() => {
                  setError("");
                  setMode("login");
                }}
                className="w-full text-center text-[11px] text-text-muted hover:underline cursor-pointer"
              >
                Back to sign in
              </button>
            </form>
          )}

          {mode === "forgot-sent" && (
            <div className="space-y-4 text-center">
              <p className="text-xs text-text-muted leading-relaxed">
                If <span className="font-bold text-text">{email}</span> is registered, a reset
                link has been sent. Check the inbox and follow the link to set a new password.
              </p>
              <Button
                type="button"
                className="w-full mt-2"
                onClick={() => {
                  setMode("login");
                  setPassword("");
                }}
              >
                Back to sign in
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default Login;
