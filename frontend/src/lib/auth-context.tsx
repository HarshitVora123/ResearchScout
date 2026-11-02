'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { getSession, login as apiLogin, logoutSession, register as apiRegister } from '@/lib/api';

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

  // The session is held in HttpOnly cookies and cannot be read by page scripts.
  useEffect(() => {
    getSession()
      .then(() => setState({ token: 'cookie-session', refreshToken: null, isAuthenticated: true, isLoading: false }))
      .catch(() => setState({ token: null, refreshToken: null, isAuthenticated: false, isLoading: false }));
  }, []);

  const handleLogin = useCallback(() => {
    setState({
      token: 'cookie-session',
      refreshToken: null,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      handleLogin();
    },
    [handleLogin]
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await apiRegister(email, password, fullName);
      handleLogin();
    },
    [handleLogin]
  );

  const logout = useCallback(() => {
    void logoutSession();
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
