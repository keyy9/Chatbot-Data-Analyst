import type { ManagedUser } from "../types/user";
import type { ManagedUserApiShape } from "./apiClient";

export function mapManagedUser(raw: ManagedUserApiShape): ManagedUser {
  const total = raw.total_queries;
  const successful = raw.successful_queries;

  return {
    id: raw.id,
    // Older accounts predate the username column and have it as null in
    // the DB - fall back to the email's local part so there's always a
    // non-empty string to render/initial-avatar off of.
    username: raw.username || raw.email.split("@")[0],
    email: raw.email,
    role: raw.role === "admin" ? "Admin" : "User",
    status:
      raw.status === "active" ? "Active" : raw.status === "suspended" ? "Suspended" : "Inactive",
    totalQueries: total,
    successfulQueries: successful,
    failedQueries: raw.failed_queries,
    successRate: total > 0 ? successful / total : 0,
    lastActive: raw.last_login_at ? new Date(raw.last_login_at).toLocaleString() : "Never",
    createdAt: raw.created_at ? new Date(raw.created_at).toLocaleDateString() : "—",
  };
}

export function toApiStatus(status: ManagedUser["status"]): "active" | "inactive" | "suspended" {
  return status.toLowerCase() as "active" | "inactive" | "suspended";
}
