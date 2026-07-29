'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import OpportunityCard from '@/components/OpportunityCard';
import type { OpportunityBrief, UserProfile } from '@/lib/api';
import { getProfile, getTrendingOpportunities, triggerDiscovery } from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [trending, setTrending] = useState<OpportunityBrief[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Discovery form state
  const [topics, setTopics] = useState('');
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMsg, setDiscoveryMsg] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    async function load() {
      if (!token) return;
      try {
        const [profileData, trendingData] = await Promise.all([
          getProfile(token),
          getTrendingOpportunities(6),
        ]);
        setProfile(profileData);
        setTrending(trendingData);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoadingData(false);
      }
    }
    if (token) load();
  }, [token]);

  async function handleDiscover() {
    if (!topics.trim() || !token) return;
    setDiscovering(true);
    setDiscoveryMsg('');
    try {
      const topicList = topics.split(',').map((t) => t.trim()).filter(Boolean);
      const result = await triggerDiscovery(token, topicList);
      setDiscoveryMsg(result.message);
      setTopics('');
    } catch (err: any) {
      setDiscoveryMsg(err.message || 'Discovery failed');
    } finally {
      setDiscovering(false);
    }
  }

  if (isLoading || (!isAuthenticated && !isLoading)) {
    return (
      <div className="container" style={{ padding: '60px 24px' }}>
        <div className="skeleton" style={{ height: '300px', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  return (
    <div className="container" style={{ paddingBottom: '80px' }}>
      <div className="page-header">
        <h1 className="page-title animate-in">
          Welcome back, <span className="gradient-text">{profile?.full_name?.split(' ')[0] || 'Researcher'}</span>
        </h1>
        <p className="page-subtitle animate-in animate-delay-1">
          Your personalized research opportunity dashboard
        </p>
      </div>

      {/* ── Stats Row ────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
        {[
          { value: profile?.skills?.length || 0, label: 'Skills' },
          { value: profile?.publications?.length || 0, label: 'Publications' },
          { value: profile?.projects?.length || 0, label: 'Projects' },
          { value: profile?.research_interests?.length || 0, label: 'Interests' },
        ].map((stat, i) => (
          <div key={stat.label} className={`glass-card stat-card animate-in animate-delay-${i}`} style={{ opacity: 0 }}>
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        {/* ── Main Column ──────────────────── */}
        <div>
          {/* Discovery Widget */}
          <div className="glass-card animate-in" style={{ padding: '28px', marginBottom: '24px', opacity: 0 }}>
            <h2 style={{ fontSize: '17px', fontWeight: 700, marginBottom: '12px' }}>
              🔍 Discover New Opportunities
            </h2>
            <p style={{ fontSize: '14px', color: 'hsl(var(--text-secondary))', marginBottom: '16px' }}>
              Enter research topics and our AI agents will search, crawl, and extract opportunities for you.
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                className="input"
                placeholder="e.g., NLP, Computer Vision, Robotics"
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleDiscover()}
              />
              <button
                className="btn btn-primary"
                onClick={handleDiscover}
                disabled={discovering || !topics.trim()}
                style={{ whiteSpace: 'nowrap' }}
              >
                {discovering ? '🔄 Searching...' : '🚀 Discover'}
              </button>
            </div>
            {discoveryMsg && (
              <div style={{
                marginTop: '12px',
                padding: '10px 14px',
                background: 'hsl(var(--accent) / 0.12)',
                borderRadius: 'var(--radius-md)',
                fontSize: '13px',
                color: 'hsl(var(--accent))',
              }}>
                {discoveryMsg}
              </div>
            )}
          </div>

          {/* Trending Opportunities */}
          <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '16px' }}>
            🔥 Trending Opportunities
          </h2>
          {loadingData ? (
            <div style={{ display: 'grid', gap: '16px' }}>
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '180px', borderRadius: 'var(--radius-lg)' }} />
              ))}
            </div>
          ) : trending.length > 0 ? (
            <div style={{ display: 'grid', gap: '16px' }}>
              {trending.map((opp, i) => (
                <OpportunityCard key={opp.id} opportunity={opp} index={i} />
              ))}
            </div>
          ) : (
            <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
              <p style={{ color: 'hsl(var(--text-secondary))' }}>
                No opportunities yet. Use the discovery widget above to find some!
              </p>
            </div>
          )}
        </div>

        {/* ── Sidebar ──────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Profile Card */}
          <div className="glass-card animate-in animate-delay-1" style={{ padding: '24px', opacity: 0 }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '16px' }}>Your Profile</h3>
            <div style={{ display: 'grid', gap: '10px', fontSize: '14px' }}>
              <div>
                <span style={{ color: 'hsl(var(--text-muted))' }}>Email:</span>{' '}
                {profile?.email}
              </div>
              {profile?.university && (
                <div>
                  <span style={{ color: 'hsl(var(--text-muted))' }}>University:</span>{' '}
                  {profile.university}
                </div>
              )}
              {profile?.degree_level && (
                <div>
                  <span style={{ color: 'hsl(var(--text-muted))' }}>Degree:</span>{' '}
                  {profile.degree_level}
                </div>
              )}
              {profile?.country && (
                <div>
                  <span style={{ color: 'hsl(var(--text-muted))' }}>Country:</span>{' '}
                  {profile.country}
                </div>
              )}
            </div>
          </div>

          {/* Skills */}
          {profile?.skills && profile.skills.length > 0 && (
            <div className="glass-card animate-in animate-delay-2" style={{ padding: '24px', opacity: 0 }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Skills</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {profile.skills.map((skill) => (
                  <span key={skill.id} className="badge badge-blue">{skill.skill_name}</span>
                ))}
              </div>
            </div>
          )}

          {/* Research Interests */}
          {profile?.research_interests && profile.research_interests.length > 0 && (
            <div className="glass-card animate-in animate-delay-3" style={{ padding: '24px', opacity: 0 }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Research Interests</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {profile.research_interests.map((interest) => (
                  <span key={interest.id} className="badge badge-purple">{interest.topic}</span>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="glass-card animate-in animate-delay-4" style={{ padding: '24px', opacity: 0 }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Quick Actions</h3>
            <div style={{ display: 'grid', gap: '8px' }}>
              <Link href="/opportunities" className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                📋 Browse All Opportunities
              </Link>
              <button className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                📤 Upload Resume
              </button>
              <button className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                ⚙️ Notification Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
