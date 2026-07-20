import React, { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { KeyRound, CheckCircle2 } from "lucide-react";
import { authApi, ApiError } from "../lib/apiClient";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!token) {
      setError("No reset token found. Make sure you opened the link from your email.");
      return;
    }
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword(token, newPassword);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Failed to reset password. The link may have expired.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg text-text px-4">
        <div className="max-w-sm w-full bg-surface border border-border rounded-xl p-8 text-center glass-panel">
          <p className="text-sm text-text-muted font-semibold">
            This reset link is invalid. Make sure you opened it directly from your email.
          </p>
          <Link to="/login" className="text-accent text-xs font-bold mt-4 inline-block hover:underline">
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg text-text px-4">
        <div className="max-w-sm w-full bg-surface border border-border rounded-xl p-8 text-center glass-panel">
          <div className="w-12 h-12 bg-success/10 border border-success/25 text-success rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-text mb-1">Password reset successfully</h3>
          <p className="text-xs text-text-muted">Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg text-text px-4">
      <div className="max-w-sm w-full bg-surface border border-border rounded-xl shadow-2xl overflow-hidden glass-panel">
        <div className="px-6 py-5 border-b border-border bg-surface-2/50 text-center">
          <div className="w-10 h-10 bg-accent/10 border border-accent/20 text-accent rounded-full flex items-center justify-center mx-auto mb-2">
            <KeyRound className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-text">Reset Password</h3>
          <p className="text-[11px] text-text-muted mt-1">Enter a new password for your account</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-danger/10 border border-danger/20 text-danger p-3 rounded-lg text-xs font-bold">
              {error}
            </div>
          )}

          <Input
            label="New Password"
            type="password"
            placeholder="Min 8 characters"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />

          <Input
            label="Confirm Password"
            type="password"
            placeholder="Repeat new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />

          <Button type="submit" className="w-full" isLoading={isLoading}>
            Reset Password
          </Button>
        </form>
      </div>
    </div>
  );
}
