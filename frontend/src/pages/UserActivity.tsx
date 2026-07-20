import React from "react";
import { Users } from "lucide-react";
import type { UserActivity } from "../types/user";

interface UserActivityProps {
  userActivities: UserActivity[];
}

export const UserActivityPage: React.FC<UserActivityProps> = ({
  userActivities,
}) => {
  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden animate-fade-in font-sans">
      {userActivities.length === 0 ? (
        <div className="p-16 text-center">
          <div className="w-12 h-12 bg-surface-2 border border-border text-text-muted rounded-full flex items-center justify-center mx-auto mb-3">
            <Users className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-text mb-1 font-sans">
            No Active Users Found
          </h4>
          <p className="text-xs text-text-faint max-w-xs mx-auto font-sans">
            No active user data available.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-2 border-b border-border text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
                <th className="py-3 px-5">User Name</th>
                <th className="py-3 px-5">Email Address</th>
                <th className="py-3 px-5">Total Queries</th>
                <th className="py-3 px-5">Login Time</th>
                <th className="py-3 px-5">Last Active</th>
                <th className="py-3 px-5">Success Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 text-xs">
              {userActivities.map((user) => (
                <tr
                  key={user.id}
                  className="hover:bg-surface-hover/40 transition-colors group"
                >
                  <td className="py-4 px-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-[#1D3F3A] text-accent font-extrabold flex items-center justify-center shadow-md border border-accent/20 text-xs font-mono">
                        {user.name.charAt(0)}
                      </div>
                      <span className="font-bold text-text font-sans">
                        {user.name}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-5 text-text-muted font-medium font-mono text-[10px]">
                    {user.email ||
                      `${user.name.toLowerCase().replace(" ", "")}@lapisai.com`}
                  </td>
                  <td className="py-4 px-5 font-bold text-text-muted font-mono">
                    {user.totalQueries}
                  </td>
                  <td className="py-4 px-5 text-text-muted font-mono text-[10px]">
                    {user.loginTime || "2026-06-30 08:30:00"}
                  </td>
                  <td className="py-4 px-5 text-text-muted font-mono text-[10px]">
                    {user.lastActivity}
                  </td>
                  <td className="py-4 px-5">
                    <div className="flex items-center gap-3 max-w-xs font-sans">
                      <div className="flex-1 h-2 bg-surface-2 rounded-full overflow-hidden border border-border">
                        <div
                          className={`h-full rounded-full ${
                            user.successRate >= 95
                              ? "bg-gradient-to-r from-accent to-teal"
                              : "bg-gradient-to-r from-amber-500 to-orange-500"
                          }`}
                          style={{
                            width: `${user.successRate}%`,
                          }}
                        ></div>
                      </div>
                      <span className="font-bold text-text min-w-[40px] text-right font-mono">
                        {user.successRate.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
