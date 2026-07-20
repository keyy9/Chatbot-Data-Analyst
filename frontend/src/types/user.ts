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
  lastActive: string;
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
