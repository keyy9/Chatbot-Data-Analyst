export interface ManagedUser {
  id: string;
  username: string;
  email: string;
  role: 'Admin' | 'User';
  status: 'Active' | 'Inactive' | 'Suspended';
  totalQueries: number;
  successfulQueries: number;
  failedQueries: number;
  successRate: number;
  /** Human-readable form of `lastActiveAt`, or "Never". Display only. */
  lastActive: string;
  /** Raw ISO timestamp - sort and compare on this, never on `lastActive`. */
  lastActiveAt: string | null;
  createdAt: string;
}

export interface UserActivity {
  id: string;
  name: string;
  email: string;
  totalQueries: number;
  loginTime: string;
  lastActivity: string;
  successRate: number;
}
