import type { ManagedUser } from "../types/user";
import type { QueryLog } from "../types/query";
import type { ManagedUserApiShape } from "./apiClient";

/**
 * Name to render for a query log's author. The backend resolves the name
 * against the `users` table and flags accounts that are gone, so this never
 * has to guess by matching strings against the managed-user list.
 */
export function queryLogAuthor(log: QueryLog): string {
  return log.userDeleted ? "Deleted User" : log.user;
}

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
    lastActive: raw.last_active_at ? new Date(raw.last_active_at).toLocaleString() : "Never",
    lastActiveAt: raw.last_active_at,
    createdAt: raw.created_at ? new Date(raw.created_at).toLocaleDateString() : "—",
  };
}

export function toApiStatus(status: ManagedUser["status"]): "active" | "inactive" | "suspended" {
  return status.toLowerCase() as "active" | "inactive" | "suspended";
}
