"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export type RoleType = "CREATOR" | "REVIEWER" | "GOVERNANCE_ADMIN";

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface WorkspaceRoleItem {
  workspace_id: string;
  workspace_name: string;
  workspace_slug: string;
  role: RoleType;
}

interface AuthContextType {
  user: UserSummary | null;
  token: string | null;
  workspaces: WorkspaceRoleItem[];
  activeWorkspace: WorkspaceRoleItem | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, fullName: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  setActiveWorkspace: (workspaceId: string) => void;
  switchDemoRole: (role: RoleType) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Demo seed accounts matching server/app/core/seed.py
const DEMO_ACCOUNTS: Record<RoleType, { user: UserSummary; workspace: WorkspaceRoleItem }> = {
  CREATOR: {
    user: {
      id: "demo-creator-id",
      email: "creator@acme.com",
      full_name: "Alice Creator",
      is_active: true,
      is_superuser: false,
    },
    workspace: {
      workspace_id: "acme-global-id",
      workspace_name: "Acme Global Brands",
      workspace_slug: "acme-global",
      role: "CREATOR",
    },
  },
  REVIEWER: {
    user: {
      id: "demo-reviewer-id",
      email: "reviewer@acme.com",
      full_name: "Bob Reviewer",
      is_active: true,
      is_superuser: false,
    },
    workspace: {
      workspace_id: "acme-global-id",
      workspace_name: "Acme Global Brands",
      workspace_slug: "acme-global",
      role: "REVIEWER",
    },
  },
  GOVERNANCE_ADMIN: {
    user: {
      id: "demo-admin-id",
      email: "admin@acme.com",
      full_name: "Carol Governance Admin",
      is_active: true,
      is_superuser: false,
    },
    workspace: {
      workspace_id: "acme-global-id",
      workspace_name: "Acme Global Brands",
      workspace_slug: "acme-global",
      role: "GOVERNANCE_ADMIN",
    },
  },
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSummary | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceRoleItem[]>([]);
  const [activeWorkspace, setActiveWorkspaceState] = useState<WorkspaceRoleItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

  // Initialize from storage or default to Creator demo session
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem("vbt_token");
      const storedUser = localStorage.getItem("vbt_user");
      const storedWorkspaces = localStorage.getItem("vbt_workspaces");
      const storedActiveWs = localStorage.getItem("vbt_active_ws");

      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        if (storedWorkspaces) {
          const wsList = JSON.parse(storedWorkspaces);
          setWorkspaces(wsList);
          if (storedActiveWs) {
            setActiveWorkspaceState(JSON.parse(storedActiveWs));
          } else if (wsList.length > 0) {
            setActiveWorkspaceState(wsList[0]);
          }
        }
      } else {
        // Default to demo Creator profile for instant exploration
        const defaultDemo = DEMO_ACCOUNTS.CREATOR;
        setUser(defaultDemo.user);
        setWorkspaces([defaultDemo.workspace]);
        setActiveWorkspaceState(defaultDemo.workspace);
        setToken("demo-mock-jwt-token");
      }
    } catch {
      // Fallback
      const defaultDemo = DEMO_ACCOUNTS.CREATOR;
      setUser(defaultDemo.user);
      setWorkspaces([defaultDemo.workspace]);
      setActiveWorkspaceState(defaultDemo.workspace);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const message = errData?.detail?.error?.message || "Invalid email or password";
        setIsLoading(false);
        return { success: false, error: message };
      }

      const data = await res.json();
      const accessToken = data.access_token;
      setToken(accessToken);
      localStorage.setItem("vbt_token", accessToken);

      // Fetch Profile & Workspaces
      const profileRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (profileRes.ok) {
        const profileData = await profileRes.json();
        setUser(profileData.user);
        setWorkspaces(profileData.workspaces || []);
        localStorage.setItem("vbt_user", JSON.stringify(profileData.user));
        localStorage.setItem("vbt_workspaces", JSON.stringify(profileData.workspaces || []));

        if (profileData.workspaces && profileData.workspaces.length > 0) {
          setActiveWorkspaceState(profileData.workspaces[0]);
          localStorage.setItem("vbt_active_ws", JSON.stringify(profileData.workspaces[0]));
        }
      }

      setIsLoading(false);
      return { success: true };
    } catch (err: unknown) {
      setIsLoading(false);
      const msg = err instanceof Error ? err.message : "Failed to connect to authentication server";
      return { success: false, error: msg };
    }
  };

  const register = async (email: string, password: string, fullName: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const message = errData?.detail?.error?.message || "Registration failed";
        setIsLoading(false);
        return { success: false, error: message };
      }

      // Auto-login after registration
      return await login(email, password);
    } catch (err: unknown) {
      setIsLoading(false);
      const msg = err instanceof Error ? err.message : "Network error during registration";
      return { success: false, error: msg };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setWorkspaces([]);
    setActiveWorkspaceState(null);
    localStorage.removeItem("vbt_token");
    localStorage.removeItem("vbt_user");
    localStorage.removeItem("vbt_workspaces");
    localStorage.removeItem("vbt_active_ws");
  };

  const setActiveWorkspace = (workspaceId: string) => {
    const ws = workspaces.find((w) => w.workspace_id === workspaceId);
    if (ws) {
      setActiveWorkspaceState(ws);
      localStorage.setItem("vbt_active_ws", JSON.stringify(ws));
    }
  };

  const switchDemoRole = (role: RoleType) => {
    const demo = DEMO_ACCOUNTS[role];
    setUser(demo.user);
    setWorkspaces([demo.workspace]);
    setActiveWorkspaceState(demo.workspace);
    setToken(`demo-jwt-${role.toLowerCase()}`);
    localStorage.setItem("vbt_user", JSON.stringify(demo.user));
    localStorage.setItem("vbt_workspaces", JSON.stringify([demo.workspace]));
    localStorage.setItem("vbt_active_ws", JSON.stringify(demo.workspace));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        workspaces,
        activeWorkspace,
        isLoading,
        login,
        register,
        logout,
        setActiveWorkspace,
        switchDemoRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

