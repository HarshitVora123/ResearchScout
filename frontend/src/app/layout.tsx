import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';
import { AuthProvider } from '@/lib/auth-context';

export const metadata: Metadata = {
  title: 'ResearchScout — Research opportunities',
  description:
    'Find PhD positions, internships, fellowships, and scholarships. Search by research area, role, location, and deadline.',
  keywords: [
    'research opportunities',
    'PhD positions',
    'research internship',
    'fellowship',
    'scholarship',
    'research jobs',
    'machine learning',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AuthProvider>
          <Navbar />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
