'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function Navbar() {
  const pathname = usePathname();
  const { isAuthenticated, isLoading, logout } = useAuth();

  const isActive = (path: string) => pathname === path ? 'nav-link active' : 'nav-link';

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="navbar-logo">
          🔬 <span>ResearchScout</span>
        </Link>

        <div className="navbar-links">
          <Link href="/opportunities" className={isActive('/opportunities')}>
            Opportunities
          </Link>

          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <Link href="/dashboard" className={isActive('/dashboard')}>
                    Dashboard
                  </Link>
                  <button onClick={logout} className="btn btn-ghost btn-sm">
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className={isActive('/login')}>
                    Log in
                  </Link>
                  <Link href="/register" className="btn btn-primary btn-sm">
                    Sign up
                  </Link>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
