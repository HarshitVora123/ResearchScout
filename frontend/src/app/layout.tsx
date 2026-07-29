import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';
import { AuthProvider } from '@/lib/auth-context';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'ResearchScout — AI-Powered Research Opportunity Discovery',
  description:
    'Discover PhD positions, internships, fellowships, and scholarships worldwide. AI agents automatically find, verify, and recommend research opportunities personalized to your profile.',
  keywords: [
    'research opportunities',
    'PhD positions',
    'research internship',
    'fellowship',
    'scholarship',
    'AI research',
    'machine learning',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>
          <Navbar />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
