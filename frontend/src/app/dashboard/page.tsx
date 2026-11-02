'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import OpportunityCard from '@/components/OpportunityCard';
import ResumeInsights from '@/components/ResumeInsights';
import type { OpportunityBrief, UserProfile, ResumeAnalysis, Recommendation } from '@/lib/api';
import { getProfile, getTrendingOpportunities, getRecommendations, triggerDiscovery, uploadResume } from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [trending, setTrending] = useState<OpportunityBrief[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [feedTab, setFeedTab] = useState<'recommended' | 'trending'>('recommended');
  const [loadingData, setLoadingData] = useState(true);

  // Discovery form state
  const [topics, setTopics] = useState('');
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMsg, setDiscoveryMsg] = useState('');

  // Resume upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [resumeAnalysis, setResumeAnalysis] = useState<ResumeAnalysis | null>(null);
  const [resumeFileName, setResumeFileName] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    async function load() {
      if (!token) return;
      try {
        const [profileRes, trendingRes, recsRes] = await Promise.allSettled([
          getProfile(token),
          getTrendingOpportunities(8),
          getRecommendations(token, 8),
        ]);
        if (profileRes.status === 'fulfilled') setProfile(profileRes.value);
        if (trendingRes.status === 'fulfilled') setTrending(trendingRes.value);
        if (recsRes.status === 'fulfilled' && recsRes.value?.recommendations) {
          setRecommendations(recsRes.value.recommendations);
        }
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

  async function handleResumeFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    setUploadingResume(true);
    setResumeError(null);
    setResumeAnalysis(null);
    setResumeFileName(file.name);

    try {
      const analysis = await uploadResume(token, file);
      setResumeAnalysis(analysis);

      // Refresh profile to pick up newly added skills/interests
      try {
        const updatedProfile = await getProfile(token);
        setProfile(updatedProfile);
      } catch {
        // Silently preserve existing profile state
      }
    } catch (err: any) {
      setResumeError(err.message || 'Failed to upload resume. Please try again.');
    } finally {
      setUploadingResume(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
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

      {/* ── Stats Row ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
        {[
          { value: profile?.skills?.length || 0, label: 'Skills' },
          { value: profile?.publications?.length || 0, label: 'Publications' },
          { value: profile?.projects?.length || 0, label: 'Projects' },
          { value: profile?.research_interests?.length || 0, label: 'Interests' },
        ].map((stat, i) => (
          <div key={stat.label} className={`glass-card stat-card animate-in animate-delay-${i}`}>
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* ── Resume Insights Panel (shows after upload) ─ */}
      {resumeAnalysis && (
        <ResumeInsights
          analysis={resumeAnalysis}
          fileName={resumeFileName}
          onClose={() => setResumeAnalysis(null)}
        />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px', marginTop: resumeAnalysis ? 32 : 0 }}>
        {/* ── Main Column ──────────────────────────────── */}
        <div>
          {/* Discovery Widget */}
          <div className="glass-card animate-in" style={{ padding: '28px', marginBottom: '24px' }}>
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

          {/* Opportunities Feed with Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setFeedTab('recommended')}
                className={`btn btn-sm ${feedTab === 'recommended' ? 'btn-primary' : 'btn-secondary'}`}
              >
                🎯 Matched For You ({recommendations.length})
              </button>
              <button
                onClick={() => setFeedTab('trending')}
                className={`btn btn-sm ${feedTab === 'trending' ? 'btn-primary' : 'btn-secondary'}`}
              >
                🔥 Trending ({trending.length})
              </button>
            </div>
          </div>

          {loadingData ? (
            <div style={{ display: 'grid', gap: '16px' }}>
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '180px', borderRadius: 'var(--radius-lg)' }} />
              ))}
            </div>
          ) : feedTab === 'recommended' ? (
            recommendations.length > 0 ? (
              <div style={{ display: 'grid', gap: '16px' }}>
                {recommendations.map((rec, i) => {
                  const opp = rec.opportunity as OpportunityBrief;
                  return (
                    <div key={rec.opportunity_id || i} style={{ position: 'relative' }}>
                      <div style={{
                        position: 'absolute',
                        top: '12px',
                        right: '16px',
                        zIndex: 2,
                        background: 'rgba(99,102,241,0.15)',
                        border: '1px solid rgba(99,102,241,0.3)',
                        borderRadius: '20px',
                        padding: '3px 10px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: '#a5b4fc',
                      }}>
                        {Math.round(rec.score * 100)}% Match
                      </div>
                      <OpportunityCard opportunity={{ ...opp, id: rec.opportunity_id || opp.id }} index={i} />
                      {rec.match_reasons && rec.match_reasons.length > 0 && (
                        <div style={{
                          margin: '-8px 12px 12px 12px',
                          padding: '8px 14px',
                          background: 'rgba(255,255,255,0.02)',
                          borderRadius: '0 0 var(--radius-md) var(--radius-md)',
                          borderLeft: '2px solid #6366f1',
                          fontSize: '12px',
                          color: 'hsl(var(--text-muted))',
                        }}>
                          💡 {rec.match_reasons[0]}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
                <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '12px' }}>
                  No personalized matches yet. Upload your resume or add skills in your profile to see tailored recommendations!
                </p>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setFeedTab('trending')}
                >
                  View Trending Opportunities
                </button>
              </div>
            )
          ) : (
            trending.length > 0 ? (
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
            )
          )}
        </div>

        {/* ── Sidebar ──────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Profile Card */}
          <div className="glass-card animate-in animate-delay-1" style={{ padding: '24px' }}>
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
            <div className="glass-card animate-in animate-delay-2" style={{ padding: '24px' }}>
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
            <div className="glass-card animate-in animate-delay-3" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Research Interests</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {profile.research_interests.map((interest) => (
                  <span key={interest.id} className="badge badge-purple">{interest.topic}</span>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions — Resume Upload Hero */}
          <div className="glass-card animate-in animate-delay-4" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '6px' }}>Upload Resume</h3>
            <p style={{ fontSize: '13px', color: 'hsl(var(--text-muted))', marginBottom: '14px', lineHeight: 1.5 }}>
              Upload your CV/resume to get instant eligibility analysis across all opportunities.
            </p>

            {/* Upload zone */}
            <div
              onClick={() => !uploadingResume && fileInputRef.current?.click()}
              style={{
                border: '2px dashed rgba(99,102,241,0.4)',
                borderRadius: 14,
                padding: '22px 16px',
                textAlign: 'center',
                cursor: uploadingResume ? 'wait' : 'pointer',
                background: uploadingResume ? 'rgba(99,102,241,0.06)' : 'rgba(99,102,241,0.04)',
                transition: 'all 0.2s',
              }}
            >
              {uploadingResume ? (
                <>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    border: '3px solid rgba(99,102,241,0.2)',
                    borderTopColor: '#6366f1',
                    animation: 'spin 0.8s linear infinite',
                    margin: '0 auto 10px',
                  }} />
                  <div style={{ fontSize: 13, color: '#818cf8', fontWeight: 600 }}>Analysing resume…</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                    Parsing skills, matching opportunities
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>📤</div>
                  <div style={{ fontSize: 13, color: '#818cf8', fontWeight: 600 }}>
                    {resumeAnalysis ? 'Upload another resume' : 'Click to upload'}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                    PDF, DOCX or TXT
                  </div>
                </>
              )}
            </div>

            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,.docx,.txt"
              onChange={handleResumeFileChange}
              style={{ display: 'none' }}
            />

            {resumeError && (
              <div style={{
                marginTop: 12, padding: '10px 14px', borderRadius: 10,
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)',
                fontSize: 13, color: '#f87171',
              }}>
                ⚠ {resumeError}
              </div>
            )}

            {resumeAnalysis && (
              <div style={{
                marginTop: 12, padding: '10px 14px', borderRadius: 10,
                background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.25)',
                fontSize: 13, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span>✓</span>
                <span>
                  Analysed — {resumeAnalysis.matched_opportunities.filter(m => m.eligibility_score >= 65).length} strong matches found
                </span>
              </div>
            )}

            {/* Divider */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', margin: '16px 0' }} />

            <div style={{ display: 'grid', gap: '8px' }}>
              <Link href="/opportunities" className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                📋 Browse All Opportunities
              </Link>
              <Link href="/dashboard/notifications" className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                ⚙️ Notification Settings
              </Link>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
