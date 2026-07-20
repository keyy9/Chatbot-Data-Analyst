import React, { useState, useMemo } from "react";
import {
  Search,
  Users,
  ChevronUp,
  ChevronDown,
  Edit3,
  Lock,
  Unlock,
  Trash2,
  UserPlus,
} from "lucide-react";
import { StatusBadge } from "../components/StatusBadge";
import { UserProfileDrawer } from "../components/drawers/UserProfileDrawer";
import { AddManagedUserModal } from "../components/modals/AddManagedUserModal";
import { EditManagedUserModal } from "../components/modals/EditManagedUserModal";
import { DeleteConfirmModal } from "../components/modals/DeleteConfirmModal";
import type { ManagedUser } from "../types/user";

type ActionResult = { success: boolean; error?: string; message?: string };

interface UserManagementProps {
  managedUsers: ManagedUser[];
  managedUsersLoading: boolean;
  onCreateUser: (email: string, username: string, password: string) => Promise<ActionResult>;
  onUpdateUsername: (targetId: string, username: string) => Promise<ActionResult>;
  onUpdateStatus: (targetId: string, status: ManagedUser["status"]) => Promise<ActionResult>;
  onTriggerResetPassword: (targetId: string) => Promise<ActionResult>;
  onDeleteUser: (targetId: string) => Promise<ActionResult>;
  userMgmtSearch: string;
  setUserMgmtSearch: (search: string) => void;
  userMgmtRoleFilter: "All" | "Admin" | "User";
  setUserMgmtRoleFilter: (role: "All" | "Admin" | "User") => void;
  userMgmtStatusFilter: "All" | "Active" | "Inactive" | "Suspended";
  setUserMgmtStatusFilter: (status: "All" | "Active" | "Inactive" | "Suspended") => void;
  userMgmtSortCol: "username" | "lastActive" | "none";
  setUserMgmtSortCol: (col: "username" | "lastActive" | "none") => void;
  userMgmtSortOrder: "asc" | "desc";
  setUserMgmtSortOrder: (order: "asc" | "desc") => void;
  userMgmtCurrentPage: number;
  setUserMgmtCurrentPage: (page: number) => void;
  userMgmtPerPage: number;
  showToast: (msg: string) => void;
}

export const UserManagement: React.FC<UserManagementProps> = ({
  managedUsers,
  managedUsersLoading,
  onCreateUser,
  onUpdateUsername,
  onUpdateStatus,
  onTriggerResetPassword,
  onDeleteUser,
  userMgmtSearch,
  setUserMgmtSearch,
  userMgmtRoleFilter,
  setUserMgmtRoleFilter,
  userMgmtStatusFilter,
  setUserMgmtStatusFilter,
  userMgmtSortCol,
  setUserMgmtSortCol,
  userMgmtSortOrder,
  setUserMgmtSortOrder,
  userMgmtCurrentPage,
  setUserMgmtCurrentPage,
  userMgmtPerPage,
  showToast,
}) => {
  // Derived (not independent state) so it always reflects the latest fetch -
  // no manual patching needed in the drawer/modals after a mutation.
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const selectedManagedUser = useMemo(
    () => managedUsers.find((u) => u.id === selectedUserId) ?? null,
    [managedUsers, selectedUserId]
  );
  const setSelectedManagedUser = (user: ManagedUser | null) => setSelectedUserId(user ? user.id : null);

  const [isAddingManagedUser, setIsAddingManagedUser] = useState(false);
  const [editingManagedUser, setEditingManagedUser] = useState<ManagedUser | null>(null);
  const [deletingManagedUser, setDeletingManagedUser] = useState<ManagedUser | null>(null);

  const handleToggleStatus = async (user: ManagedUser) => {
    if (user.role === "Admin") return;
    const updatedStatus = user.status === "Active" ? "Suspended" : "Active";
    const res = await onUpdateStatus(user.id, updatedStatus);
    if (res.success) {
      showToast(
        `User ${user.username} has been ${updatedStatus === "Active" ? "activated" : "suspended"} successfully.`
      );
    } else {
      showToast(`⚠️ ${res.error || "Failed to update status"}`);
    }
  };

  // User Management Filtering & Sorting logic
  const filteredManagedUsers = useMemo(() => {
    let list = [...managedUsers];

    if (userMgmtSearch) {
      const q = userMgmtSearch.toLowerCase();
      list = list.filter(
        (u) =>
          u.username.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q)
      );
    }

    if (userMgmtRoleFilter !== "All") {
      list = list.filter((u) => u.role === userMgmtRoleFilter);
    }

    if (userMgmtStatusFilter !== "All") {
      list = list.filter((u) => u.status === userMgmtStatusFilter);
    }

    if (userMgmtSortCol !== "none") {
      list.sort((a, b) => {
        let valA: any = a[userMgmtSortCol];
        let valB: any = b[userMgmtSortCol];

        if (typeof valA === "string") {
          return userMgmtSortOrder === "asc"
            ? valA.localeCompare(valB)
            : valB.localeCompare(valA);
        } else {
          return userMgmtSortOrder === "asc" ? valA - valB : valB - valA;
        }
      });
    }

    return list;
  }, [
    managedUsers,
    userMgmtSearch,
    userMgmtRoleFilter,
    userMgmtStatusFilter,
    userMgmtSortCol,
    userMgmtSortOrder,
  ]);

  const paginatedManagedUsers = useMemo(() => {
    const startIndex = (userMgmtCurrentPage - 1) * userMgmtPerPage;
    return filteredManagedUsers.slice(startIndex, startIndex + userMgmtPerPage);
  }, [filteredManagedUsers, userMgmtCurrentPage, userMgmtPerPage]);

  const totalUserMgmtPages = Math.max(
    1,
    Math.ceil(filteredManagedUsers.length / userMgmtPerPage)
  );

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden">
        {/* Search and Filters Header */}
        <div className="p-5 border-b border-border bg-surface-2/45 space-y-4 md:space-y-0 md:flex md:items-center md:justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search users by username or email..."
              value={userMgmtSearch}
              onChange={(e) => {
                setUserMgmtSearch(e.target.value);
                setUserMgmtCurrentPage(1);
              }}
              className="w-full bg-surface-hover border border-border text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-9 pr-4 py-2 rounded-lg text-sm focus:outline-none transition-all placeholder:text-xs font-sans"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Role Filter */}
            <select
              value={userMgmtRoleFilter}
              onChange={(e) => {
                setUserMgmtRoleFilter(e.target.value as any);
                setUserMgmtCurrentPage(1);
              }}
              className="bg-surface-hover text-xs font-semibold px-3 py-2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer font-sans"
            >
              <option value="All">All Roles</option>
              <option value="Admin">Admin</option>
              <option value="User">User</option>
            </select>

            {/* Status Filter */}
            <select
              value={userMgmtStatusFilter}
              onChange={(e) => {
                setUserMgmtStatusFilter(e.target.value as any);
                setUserMgmtCurrentPage(1);
              }}
              className="bg-surface-hover text-xs font-semibold px-3 py-2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer font-sans"
            >
              <option value="All">All Statuses</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
              <option value="Suspended">Suspended</option>
            </select>

            {/* Reset filters */}
            {(userMgmtSearch ||
              userMgmtRoleFilter !== "All" ||
              userMgmtStatusFilter !== "All") && (
              <button
                type="button"
                onClick={() => {
                  setUserMgmtSearch("");
                  setUserMgmtRoleFilter("All");
                  setUserMgmtStatusFilter("All");
                  setUserMgmtCurrentPage(1);
                }}
                className="text-xs text-accent hover:text-accent hover:underline font-bold px-2 py-1 flex items-center gap-1 cursor-pointer font-sans"
              >
                Clear
              </button>
            )}

            {/* Add User Button */}
            <button
              type="button"
              onClick={() => {
                setIsAddingManagedUser(true);
              }}
              className="bg-gradient-to-r from-accent to-teal hover:opacity-90 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition-all flex items-center gap-1.5 cursor-pointer ml-auto md:ml-0 font-sans"
            >
              <UserPlus className="w-3.5 h-3.5" />
              Add User
            </button>
          </div>
        </div>

        {/* TABLE CONTENT */}
        {managedUsersLoading ? (
          <div className="p-16 text-center text-xs text-text-muted font-sans">
            Loading users...
          </div>
        ) : filteredManagedUsers.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-12 h-12 bg-surface-2 border border-border text-text-muted rounded-full flex items-center justify-center mx-auto mb-3">
              <Users className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-text mb-1 font-sans">
              No Users Found
            </h4>
            <p className="text-xs text-text-faint max-w-xs mx-auto font-sans">
              No user accounts matched your search terms or filters. Try adjusting
              your search criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-sans">
              <thead>
                <tr className="bg-surface-2 border-b border-border text-[10px] font-bold text-text-muted uppercase tracking-wider select-none font-mono">
                  <th className="py-3 px-5">User ID</th>

                  <th
                    className="py-3 px-5 cursor-pointer hover:text-text transition-colors"
                    onClick={() => {
                      const order =
                        userMgmtSortCol === "username" &&
                        userMgmtSortOrder === "asc"
                          ? "desc"
                          : "asc";
                      setUserMgmtSortCol("username");
                      setUserMgmtSortOrder(order);
                    }}
                  >
                    <div className="flex items-center gap-1">
                      Username
                      {userMgmtSortCol === "username" &&
                        (userMgmtSortOrder === "asc" ? (
                          <ChevronUp className="w-3 h-3 text-accent" />
                        ) : (
                          <ChevronDown className="w-3 h-3 text-accent" />
                        ))}
                    </div>
                  </th>

                  <th className="py-3 px-5">Email</th>
                  <th className="py-3 px-5">Role</th>
                  <th className="py-3 px-5">Status</th>

                  <th
                    className="py-3 px-5 cursor-pointer hover:text-text transition-colors"
                    onClick={() => {
                      const order =
                        userMgmtSortCol === "lastActive" &&
                        userMgmtSortOrder === "asc"
                          ? "desc"
                          : "asc";
                      setUserMgmtSortCol("lastActive");
                      setUserMgmtSortOrder(order);
                    }}
                  >
                    <div className="flex items-center gap-1">
                      Last Active
                      {userMgmtSortCol === "lastActive" &&
                        (userMgmtSortOrder === "asc" ? (
                          <ChevronUp className="w-3 h-3 text-accent" />
                        ) : (
                          <ChevronDown className="w-3 h-3 text-accent" />
                        ))}
                    </div>
                  </th>

                  <th className="py-3 px-5">Created Date</th>
                  <th className="py-3 px-5 text-center">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-border/40 text-xs">
                {paginatedManagedUsers.map((user) => {
                  const isManageable = user.role !== "Admin";
                  return (
                  <tr
                    key={user.id}
                    onClick={() => setSelectedManagedUser(user)}
                    className="hover:bg-surface-hover/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-5 font-mono text-[10px] text-text-muted">
                      {user.id}
                    </td>
                    <td className="py-3.5 px-5 font-bold text-text font-sans">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-surface-hover text-text-muted font-extrabold flex items-center justify-center border border-border text-[11px] font-mono">
                          {user.username.charAt(0).toUpperCase()}
                        </div>
                        <span>{user.username}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-5 text-text-muted font-mono text-[10px]">
                      {user.email}
                    </td>
                    <td className="py-3.5 px-5">
                      <StatusBadge type="role" value={user.role} />
                    </td>
                    <td className="py-3.5 px-5">
                      <StatusBadge type="status" value={user.status} />
                    </td>
                    <td className="py-3.5 px-5 text-text-muted font-mono text-[10px]">
                      {user.lastActive}
                    </td>
                    <td className="py-3.5 px-5 text-text-muted font-mono text-[10px]">
                      {user.createdAt}
                    </td>
                    <td
                      className="py-3.5 px-5 text-center"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {!isManageable ? (
                        <span className="text-[10px] text-text-faint italic">Not manageable here</span>
                      ) : (
                        <div className="flex items-center justify-center gap-2">
                          <button
                            type="button"
                            onClick={() => setEditingManagedUser(user)}
                            className="p-1.5 text-xs text-blue-400 hover:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded border border-blue-500/20 transition-all cursor-pointer"
                            title="Edit Username"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleToggleStatus(user)}
                            className={`p-1.5 text-xs rounded border transition-all cursor-pointer ${
                              user.status === "Active"
                                ? "text-warning hover:text-warning bg-warning/10 hover:bg-warning/20 border-warning/20"
                                : "text-success hover:text-success bg-success/10 hover:bg-success/20 border-success/20"
                            }`}
                            title={user.status === "Active" ? "Suspend User" : "Activate User"}
                          >
                            {user.status === "Active" ? (
                              <Lock className="w-3.5 h-3.5" />
                            ) : (
                              <Unlock className="w-3.5 h-3.5" />
                            )}
                          </button>

                          <button
                            type="button"
                            onClick={() => setDeletingManagedUser(user)}
                            className="p-1.5 text-xs text-red-500 hover:text-red-400 bg-red-500/10 hover:bg-red-500/20 rounded border border-red-500/20 transition-all cursor-pointer"
                            title="Delete User"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* PAGINATION PANEL */}
        {filteredManagedUsers.length > 0 && (
          <div className="p-4 border-t border-border bg-surface-2/45 flex items-center justify-between font-sans">
            <span className="text-xs text-text-muted font-semibold font-sans">
              Showing {(userMgmtCurrentPage - 1) * userMgmtPerPage + 1} to{" "}
              {Math.min(
                userMgmtCurrentPage * userMgmtPerPage,
                filteredManagedUsers.length
              )}{" "}
              of {filteredManagedUsers.length} user accounts
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={userMgmtCurrentPage === 1}
                onClick={() => setUserMgmtCurrentPage(userMgmtCurrentPage - 1)}
                className={`px-2.5 py-1.5 rounded text-xs font-bold border border-border transition-all font-sans ${
                  userMgmtCurrentPage === 1
                    ? "bg-surface-hover/40 text-text-faint cursor-not-allowed"
                    : "bg-surface-hover text-text hover:bg-[#1D3F3A] cursor-pointer"
                }`}
              >
                Previous
              </button>

              {Array.from({ length: totalUserMgmtPages }).map((_, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => setUserMgmtCurrentPage(idx + 1)}
                  className={`w-7 h-7 rounded text-xs font-bold transition-all font-mono ${
                    userMgmtCurrentPage === idx + 1
                      ? "bg-gradient-to-r from-accent to-teal text-white shadow-md shadow-accent/10"
                      : "bg-surface-hover border border-border text-text-muted hover:bg-[#1D3F3A] cursor-pointer"
                  }`}
                >
                  {idx + 1}
                </button>
              ))}

              <button
                type="button"
                disabled={userMgmtCurrentPage === totalUserMgmtPages}
                onClick={() => setUserMgmtCurrentPage(userMgmtCurrentPage + 1)}
                className={`px-2.5 py-1.5 rounded text-xs font-bold border border-border transition-all font-sans ${
                  userMgmtCurrentPage === totalUserMgmtPages
                    ? "bg-surface-hover/40 text-text-faint cursor-not-allowed"
                    : "bg-surface-hover text-text hover:bg-[#1D3F3A] cursor-pointer"
                }`}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Profile details drawer */}
      <UserProfileDrawer
        selectedManagedUser={selectedManagedUser}
        setSelectedManagedUser={setSelectedManagedUser}
        setEditingManagedUser={setEditingManagedUser}
        setDeletingManagedUser={setDeletingManagedUser}
        onToggleStatus={handleToggleStatus}
        onTriggerResetPassword={onTriggerResetPassword}
        showToast={showToast}
      />

      {/* Add User Modal */}
      <AddManagedUserModal
        isOpen={isAddingManagedUser}
        onClose={() => setIsAddingManagedUser(false)}
        managedUsers={managedUsers}
        onCreateUser={onCreateUser}
        showToast={showToast}
      />

      {/* Edit User Modal */}
      <EditManagedUserModal
        isOpen={!!editingManagedUser}
        onClose={() => setEditingManagedUser(null)}
        editingManagedUser={editingManagedUser}
        onUpdateUsername={onUpdateUsername}
        showToast={showToast}
      />

      {/* Delete User Modal */}
      <DeleteConfirmModal
        isOpen={!!deletingManagedUser}
        onClose={() => setDeletingManagedUser(null)}
        deletingManagedUser={deletingManagedUser}
        onDeleteUser={onDeleteUser}
        showToast={showToast}
      />
    </div>
  );
};
