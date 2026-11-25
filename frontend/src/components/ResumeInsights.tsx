'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { ResumeAnalysis, OpportunityMatch } from '@/lib/api';

// ── Score color helpers ───────────────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score >= 65) return '#22c55e';   // green
  if (score >= 35) return '#f59e0b';   // amber
  return '#ef4444';                     // red
}

function scoreBg(score: number): string {
  if (score >= 65) return 'rgba(34,197,94,0.12)';
  if (score >= 35) return 'rgba(245,158,11,0.12)';
  return 'rgba(239,68,68,0.12)';
}

function scoreLabel(score: number): string {
  if (score >= 65) return 'Strong Match';
  if (score >= 35) return 'Partial Match';
  return 'Low Match';
}

function degreeFitColor(fit: string): string {
  if (fit === 'Eligible') return '#22c55e';
  if (fit === 'May not match') return '#ef4444';
  return '#94a3b8';
}

// ── Circular score badge ──────────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const r = 28;
  const circumference = 2 * Math.PI * r;
  const dash = (score / 100) * circumference;

  return (
    <div style={{ position: 'relative', width: 72, height: 72, flexShrink: 0 }}>
      <svg width={72} height={72} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={36} cy={36} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={7} />
        <circle
          cx={36} cy={36} r={r}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth={7}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease', filter: `drop-shadow(0 0 6px ${scoreColor(score)})` }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        color: scoreColor(score), fontWeight: 700, lineHeight: 1,
      }}>
        <span style={{ fontSize: 18 }}>{score}</span>
        <span style={{ fontSize: 9, opacity: 0.8, marginTop: 1 }}>/ 100</span>
      </div>
    </div>
  );
}

// ── Skill chip ────────────────────────────────────────────────────────────────
function Chip({ label, color = 'rgba(139,92,246,0.2)', textColor = '#a78bfa' }: {
  label: string; color?: string; textColor?: string;
}) {
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: 20,
      background: color, color: textColor, fontSize: 12, fontWeight: 500,
      border: `1px solid ${textColor}30`, letterSpacing: '0.01em',
    }}>
      {label}
    </span>
  );
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionTitle({ icon, title }: { icon: string; title: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>{title}</h3>
    </div>
  );
}

// ── Opportunity match card ────────────────────────────────────────────────────
function MatchCard({ match, index }: { match: OpportunityMatch; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const opp = match.opportunity;
  const color = scoreColor(match.eligibility_score);
  const bg = scoreBg(match.eligibility_score);

  return (
    <div style={{
      background: 'rgba(15,20,40,0.85)',
      border: `1px solid rgba(255,255,255,0.08)`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 16,
      padding: '20px 24px',
      transition: 'transform 0.2s, box-shadow 0.2s',
      animationDelay: `${index * 0.08}s`,
    }}
      className="match-card"
    >
      {/* Header row */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        <ScoreBadge score={match.eligibility_score} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9', marginBottom: 3 }}>
                {opp.title}
              </div>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>
                {opp.organization} · {opp.country}
              </div>
            </div>

            <span style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
              background: bg, color: color, border: `1px solid ${color}40`, whiteSpace: 'nowrap',
            }}>
              {scoreLabel(match.eligibility_score)}
            </span>
          </div>

          {/* Quick stats */}
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <Chip label={opp.opportunity_type} color="rgba(99,102,241,0.15)" textColor="#818cf8" />
            {opp.funding_type && (
              <Chip label={opp.funding_type} color="rgba(34,197,94,0.12)" textColor="#4ade80" />
            )}
            <Chip
              label={match.degree_fit}
              color={`${degreeFitColor(match.degree_fit)}18`}
              textColor={degreeFitColor(match.degree_fit)}
            />
            {match.skill_match.overlap_pct > 0 && (
              <Chip
                label={`${match.skill_match.overlap_pct}% skills`}
                color="rgba(245,158,11,0.12)"
                textColor="#fbbf24"
              />
            )}
          </div>
        </div>
      </div>

      {/* Match reasons */}
      {match.match_reasons.length > 0 && (
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {match.match_reasons.map((r, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: '#94a3b8' }}>
                <span style={{ color: '#22c55e', flexShrink: 0 }}>✓</span> {r}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expandable detail */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: '#6366f1', fontSize: 13, fontWeight: 500, marginTop: 12,
          padding: 0, display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        {expanded ? '▲ Hide details' : '▼ Show skill details'}
      </button>

      {expanded && (
        <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* Matched skills */}
          {match.skill_match.matched.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: '#22c55e', fontWeight: 600, marginBottom: 6 }}>
                ✓ Matched skills ({match.skill_match.matched.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {match.skill_match.matched.map(s => (
                  <Chip key={s} label={s} color="rgba(34,197,94,0.12)" textColor="#4ade80" />
                ))}
              </div>
            </div>
          )}

          {/* Missing skills */}
          {match.skill_match.missing.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: '#f87171', fontWeight: 600, marginBottom: 6 }}>
                ✗ Missing skills ({match.skill_match.missing.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {match.skill_match.missing.map(s => (
                  <Chip key={s} label={s} color="rgba(239,68,68,0.12)" textColor="#f87171" />
                ))}
              </div>
            </div>
          )}

          {/* Research alignment */}
          {match.research_alignment.length > 0 && (
            <div style={{ gridColumn: '1 / -1' }}>
              <div style={{ fontSize: 12, color: '#818cf8', fontWeight: 600, marginBottom: 6 }}>
                🔬 Research alignment
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {match.research_alignment.map(a => (
                  <Chip key={a} label={a} color="rgba(99,102,241,0.15)" textColor="#818cf8" />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <Link
          href={`/opportunities/${match.opportunity_id}`}
          style={{
            padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            background: 'rgba(99,102,241,0.2)', color: '#818cf8',
            border: '1px solid rgba(99,102,241,0.35)', textDecoration: 'none',
            transition: 'background 0.2s',
          }}
        >
          View Details →
        </Link>
        {opp.application_link && (
          <a
            href={opp.application_link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              background: 'rgba(34,197,94,0.12)', color: '#4ade80',
              border: '1px solid rgba(34,197,94,0.3)', textDecoration: 'none',
            }}
          >
            Apply ↗
          </a>
        )}
      </div>
    </div>
  );
}

// ── Main ResumeInsights component ─────────────────────────────────────────────
interface Props {
  analysis: ResumeAnalysis;
  fileName: string;
  onClose: () => void;
}

export default function ResumeInsights({ analysis, fileName, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'profile' | 'matches'>('profile');
  const { parsed_profile: profile, profile_updates, matched_opportunities } = analysis;

  const strongMatches = matched_opportunities.filter(m => m.eligibility_score >= 65);
  const partialMatches = matched_opportunities.filter(m => m.eligibility_score >= 35 && m.eligibility_score < 65);
  const lowMatches = matched_opportunities.filter(m => m.eligibility_score < 35);

  const skillsAdded = Array.isArray(profile_updates.skills_added) ? profile_updates.skills_added : [];
  const interestsAdded = Array.isArray(profile_updates.research_interests_added) ? profile_updates.research_interests_added : [];

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '10px 24px', borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: 'pointer',
    border: 'none', transition: 'all 0.2s',
    background: active ? 'rgba(99,102,241,0.25)' : 'transparent',
    color: active ? '#818cf8' : '#64748b',
    borderBottom: active ? '2px solid #6366f1' : '2px solid transparent',
  });

  return (
    <>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .insights-root { animation: slideIn 0.4s ease both; }
        .match-card { animation: slideIn 0.4s ease both; }
        .match-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
      `}</style>

      <div className="insights-root" style={{
        background: 'linear-gradient(135deg, rgba(15,20,40,0.98) 0%, rgba(20,15,50,0.98) 100%)',
        border: '1px solid rgba(99,102,241,0.3)',
        borderRadius: 24,
        padding: '32px',
        marginTop: 24,
        backdropFilter: 'blur(20px)',
      }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22,
              }}>
                📄
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#f1f5f9' }}>
                  Resume Analysis
                </h2>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
                  {fileName} · {matched_opportunities.length} opportunities analysed
                </div>
              </div>
            </div>

            {/* Summary stats */}
            <div style={{ display: 'flex', gap: 20, marginTop: 14 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: '#22c55e' }}>{strongMatches.length}</div>
                <div style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>Strong Matches</div>
              </div>
              <div style={{ width: 1, background: 'rgba(255,255,255,0.08)' }} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: '#f59e0b' }}>{partialMatches.length}</div>
                <div style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>Partial Matches</div>
              </div>
              <div style={{ width: 1, background: 'rgba(255,255,255,0.08)' }} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: '#818cf8' }}>
                  {profile.skills.length + profile.programming_languages.length}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>Skills Found</div>
              </div>
              {skillsAdded.length > 0 && (
                <>
                  <div style={{ width: 1, background: 'rgba(255,255,255,0.08)' }} />
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 26, fontWeight: 800, color: '#38bdf8' }}>{skillsAdded.length}</div>
                    <div style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>Added to Profile</div>
                  </div>
                </>
              )}
            </div>
          </div>

          <button onClick={onClose} style={{
            background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10, color: '#94a3b8', cursor: 'pointer', fontSize: 20,
            width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 28 }}>
          <button style={tabStyle(activeTab === 'profile')} onClick={() => setActiveTab('profile')}>
            👤 Extracted Profile
          </button>
          <button style={tabStyle(activeTab === 'matches')} onClick={() => setActiveTab('matches')}>
            🎯 Eligibility Matches ({matched_opportunities.length})
          </button>
        </div>

        {/* ── PROFILE TAB ── */}
        {activeTab === 'profile' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>

            {/* Education */}
            <div style={{
              background: 'rgba(255,255,255,0.04)', borderRadius: 16,
              border: '1px solid rgba(255,255,255,0.07)', padding: '20px 22px',
            }}>
              <SectionTitle icon="🎓" title="Education" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {profile.full_name && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>Name</span>
                    <span style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600 }}>{profile.full_name}</span>
                  </div>
                )}
                {profile.university && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>University</span>
                    <span style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600, textAlign: 'right', maxWidth: 200 }}>{profile.university}</span>
                  </div>
                )}
                {profile.degree_level && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>Degree</span>
                    <Chip label={profile.degree_level} color="rgba(99,102,241,0.15)" textColor="#818cf8" />
                  </div>
                )}
                {profile.major && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>Major</span>
                    <span style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600 }}>{profile.major}</span>
                  </div>
                )}
                {profile.gpa !== null && profile.gpa !== undefined && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>GPA</span>
                    <span style={{ color: '#22c55e', fontSize: 14, fontWeight: 700 }}>{profile.gpa.toFixed(2)}</span>
                  </div>
                )}
                {profile.experience_years > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b', fontSize: 13 }}>Experience</span>
                    <span style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600 }}>~{profile.experience_years} yrs</span>
                  </div>
                )}
                {!profile.university && !profile.degree_level && !profile.gpa && (
                  <div style={{ color: '#64748b', fontSize: 13, fontStyle: 'italic' }}>
                    Could not extract education details. Try a more detailed resume.
                  </div>
                )}
              </div>
            </div>

            {/* Technical Skills */}
            <div style={{
              background: 'rgba(255,255,255,0.04)', borderRadius: 16,
              border: '1px solid rgba(255,255,255,0.07)', padding: '20px 22px',
            }}>
              <SectionTitle icon="⚡" title={`Technical Skills (${profile.skills.length + profile.programming_languages.length})`} />

              {profile.programming_languages.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Languages
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {profile.programming_languages.map(l => (
                      <Chip key={l} label={l} color="rgba(56,189,248,0.12)" textColor="#38bdf8" />
                    ))}
                  </div>
                </div>
              )}

              {profile.skills.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Frameworks & Tools
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {profile.skills.map(s => (
                      <Chip key={s} label={s} />
                    ))}
                  </div>
                </div>
              )}

              {skillsAdded.length > 0 && (
                <div style={{
                  marginTop: 14, padding: '10px 14px', borderRadius: 10,
                  background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)',
                }}>
                  <div style={{ fontSize: 12, color: '#38bdf8', fontWeight: 600 }}>
                    ✨ {skillsAdded.length} new skills added to your profile
                  </div>
                </div>
              )}
            </div>

            {/* Research Interests */}
            {profile.research_interests.length > 0 && (
              <div style={{
                background: 'rgba(255,255,255,0.04)', borderRadius: 16,
                border: '1px solid rgba(255,255,255,0.07)', padding: '20px 22px',
              }}>
                <SectionTitle icon="🔬" title={`Research Interests (${profile.research_interests.length})`} />
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {profile.research_interests.map(r => (
                    <Chip key={r} label={r} color="rgba(168,85,247,0.15)" textColor="#c084fc" />
                  ))}
                </div>
                {interestsAdded.length > 0 && (
                  <div style={{
                    marginTop: 12, padding: '8px 12px', borderRadius: 8,
                    background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.2)',
                  }}>
                    <div style={{ fontSize: 12, color: '#c084fc', fontWeight: 600 }}>
                      ✨ {interestsAdded.length} interests added to your profile
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Publications */}
            {profile.publications.length > 0 && (
              <div style={{
                background: 'rgba(255,255,255,0.04)', borderRadius: 16,
                border: '1px solid rgba(255,255,255,0.07)', padding: '20px 22px',
              }}>
                <SectionTitle icon="📚" title={`Publications (${profile.publications.length})`} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {profile.publications.map((pub, i) => (
                    <div key={i} style={{
                      fontSize: 13, color: '#94a3b8', padding: '8px 12px',
                      background: 'rgba(255,255,255,0.03)', borderRadius: 8,
                      borderLeft: '2px solid #6366f1',
                    }}>
                      {pub.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Projects */}
            {profile.projects.length > 0 && (
              <div style={{
                background: 'rgba(255,255,255,0.04)', borderRadius: 16,
                border: '1px solid rgba(255,255,255,0.07)', padding: '20px 22px',
              }}>
                <SectionTitle icon="🚀" title={`Projects (${profile.projects.length})`} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {profile.projects.map((proj, i) => (
                    <div key={i} style={{
                      color: '#94a3b8', padding: '12px 14px',
                      background: 'rgba(255,255,255,0.03)', borderRadius: 8,
                      borderLeft: '2px solid #8b5cf6',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <strong style={{ color: '#e2e8f0', fontSize: 13, lineHeight: 1.5 }}>
                          {proj.title}
                        </strong>
                        {proj.status && (
                          <span style={{ color: '#c084fc', fontSize: 11, whiteSpace: 'nowrap' }}>
                            {proj.status}
                          </span>
                        )}
                      </div>
                      {proj.description && (
                        <p style={{ fontSize: 12, lineHeight: 1.6, margin: '6px 0 0' }}>
                          {proj.description}
                        </p>
                      )}
                      {proj.technologies?.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                          {proj.technologies.map((technology) => (
                            <Chip
                              key={technology}
                              label={technology}
                              color="rgba(56,189,248,0.1)"
                              textColor="#7dd3fc"
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── MATCHES TAB ── */}
        {activeTab === 'matches' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* No matches at all */}
            {matched_opportunities.length === 0 && (
              <div style={{
                textAlign: 'center', padding: '48px 24px',
                color: '#64748b', fontSize: 15,
              }}>
                No active opportunities found. Check back later!
              </div>
            )}

            {/* Strong matches */}
            {strongMatches.length > 0 && (
              <div>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: '#22c55e',
                  marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    borderRadius: '50%', background: '#22c55e',
                  }} />
                  Strong Matches — 65%+ eligibility
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {strongMatches.map((m, i) => <MatchCard key={m.opportunity_id} match={m} index={i} />)}
                </div>
              </div>
            )}

            {/* Partial matches */}
            {partialMatches.length > 0 && (
              <div style={{ marginTop: strongMatches.length > 0 ? 20 : 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: '#f59e0b',
                  marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    borderRadius: '50%', background: '#f59e0b',
                  }} />
                  Partial Matches — 35–65% eligibility
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {partialMatches.map((m, i) => <MatchCard key={m.opportunity_id} match={m} index={i + strongMatches.length} />)}
                </div>
              </div>
            )}

            {/* Low matches */}
            {lowMatches.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: '#64748b',
                  marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    borderRadius: '50%', background: '#475569',
                  }} />
                  Other Opportunities — below 35% match
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {lowMatches.map((m, i) => <MatchCard key={m.opportunity_id} match={m} index={i + strongMatches.length + partialMatches.length} />)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
