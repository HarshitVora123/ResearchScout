'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { login as apiLogin, register as apiRegister, type TokenResponse } from '@/lib/api';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Load from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem('rs_access_token');
    const refreshToken = localStorage.getItem('rs_refresh_token');
    setState({
      token,
      refreshToken,
      isAuthenticated: !!token,
      isLoading: false,
    });
  }, []);

  const handleTokens = useCallback((data: TokenResponse) => {
    localStorage.setItem('rs_access_token', data.access_token);
    localStorage.setItem('rs_refresh_token', data.refresh_token);
    setState({
      token: data.access_token,
      refreshToken: data.refresh_token,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await apiLogin(email, password);
      handleTokens(data);
    },
    [handleTokens]
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const data = await apiRegister(email, password, fullName);
      handleTokens(data);
    },
    [handleTokens]
  );

  const logout = useCallback(() => {
    localStorage.removeItem('rs_access_token');
    localStorage.removeItem('rs_refresh_token');
    setState({
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
