'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import type { OpportunityDetail } from '@/lib/api';
import { getOpportunityDetail } from '@/lib/api';
import { typeColor, fundingColor, formatDate, deadlineLabel, daysUntil, confidenceLabel } from '@/lib/utils';

export default function OpportunityDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [opp, setOpp] = useState<OpportunityDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getOpportunityDetail(id);
        setOpp(data);
      } catch (err) {
        console.error('Failed to load opportunity:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="container" style={{ padding: '48px 24px' }}>
        <div className="skeleton" style={{ height: '400px', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  if (!opp) {
    return (
      <div className="container" style={{ padding: '80px 24px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>Opportunity not found</h2>
        <Link href="/opportunities" className="btn btn-primary" style={{ marginTop: '24px' }}>
          ← Back to opportunities
        </Link>
      </div>
    );
  }

  const days = daysUntil(opp.deadline);

  return (
    <div className="container" style={{ paddingBottom: '80px' }}>
      {/* Back link */}
      <div style={{ padding: '24px 0 16px' }}>
        <Link href="/opportunities" className="btn btn-ghost btn-sm">
          ← Back to opportunities
        </Link>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        {/* ── Main Content ──────────────── */}
        <div className="glass-card animate-in" style={{ padding: '40px', opacity: 0 }}>
          {/* Header */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
              <span className={`badge ${typeColor(opp.opportunity_type)}`}>
                {opp.opportunity_type}
              </span>
              {opp.funding_type && (
                <span className={`badge ${fundingColor(opp.funding_type)}`}>
                  {opp.funding_type}
                </span>
              )}
              {opp.location_type && (
                <span className="badge badge-default">{opp.location_type}</span>
              )}
            </div>

            <h1 style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.2 }}>
              {opp.title}
            </h1>

            <div style={{ marginTop: '12px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '15px', color: 'hsl(var(--text-secondary))' }}>
              <span>🏛️ {opp.organization}</span>
              {opp.department && <span>📁 {opp.department}</span>}
              {opp.country && <span>📍 {opp.country}{opp.city && `, ${opp.city}`}</span>}
            </div>
          </div>

          {/* Summary */}
          {opp.summary && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px', color: 'hsl(var(--text-secondary))' }}>Summary</h2>
              <p style={{ lineHeight: 1.7, fontSize: '15px' }}>{opp.summary}</p>
            </section>
          )}

          {/* Research Areas */}
          {opp.research_areas.length > 0 && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Research Areas</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {opp.research_areas.map((area) => (
                  <span key={area} className="badge badge-purple">{area}</span>
                ))}
              </div>
            </section>
          )}

          {/* Required Skills */}
          {opp.required_skills.length > 0 && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Required Skills</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {opp.required_skills.map((skill) => (
                  <span key={skill} className="badge badge-blue">{skill}</span>
                ))}
              </div>
            </section>
          )}

          {/* Programming Languages */}
          {opp.programming_languages.length > 0 && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Programming Languages</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {opp.programming_languages.map((lang) => (
                  <span key={lang} className="badge badge-cyan">{lang}</span>
                ))}
              </div>
            </section>
          )}

          {/* Eligibility */}
          {(opp.degree_levels.length > 0 || opp.required_gpa || opp.publications_required) && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Eligibility</h2>
              <div style={{ display: 'grid', gap: '8px', fontSize: '14px' }}>
                {opp.degree_levels.length > 0 && (
                  <div>🎓 Degree: {opp.degree_levels.join(', ')}</div>
                )}
                {opp.required_gpa && <div>📊 Minimum GPA: {opp.required_gpa}</div>}
                {opp.publications_required && <div>📄 Publications required</div>}
                {opp.recommendation_letters && (
                  <div>✉️ {opp.recommendation_letters} recommendation letter(s) required</div>
                )}
              </div>
            </section>
          )}

          {/* Compensation */}
          {(opp.stipend || opp.salary_range) && (
            <section style={{ marginBottom: '28px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Compensation</h2>
              <div style={{ fontSize: '14px' }}>
                {opp.stipend && <div>💰 Stipend: {opp.stipend}</div>}
                {opp.salary_range && <div>💵 Salary: {opp.salary_range}</div>}
              </div>
            </section>
          )}

          {/* Contact */}
          {(opp.professor || opp.contact_email) && (
            <section>
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'hsl(var(--text-secondary))' }}>Contact</h2>
              <div style={{ fontSize: '14px' }}>
                {opp.professor && <div>👤 {opp.professor}</div>}
                {opp.professor_email && <div>📧 {opp.professor_email}</div>}
                {opp.contact_email && opp.contact_email !== opp.professor_email && (
                  <div>📧 {opp.contact_email}</div>
                )}
              </div>
            </section>
          )}
        </div>

        {/* ── Sidebar ──────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Apply Card */}
          <div className="glass-card animate-in animate-delay-1" style={{ padding: '28px', opacity: 0 }}>
            <a
              href={opp.application_link}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-lg"
              style={{ width: '100%', marginBottom: '16px' }}
            >
              Apply Now ↗
            </a>

            {opp.deadline && (
              <div style={{ textAlign: 'center', marginBottom: '12px' }}>
                <div style={{
                  fontSize: '13px',
                  color: 'hsl(var(--text-muted))',
                  marginBottom: '4px',
                }}>Deadline</div>
                <div style={{
                  fontSize: '17px',
                  fontWeight: 700,
                  color: days !== null && days <= 7 ? 'hsl(var(--danger))' : 'hsl(var(--text-primary))',
                }}>
                  {formatDate(opp.deadline)}
                </div>
                <div style={{
                  fontSize: '13px',
                  color: days !== null && days <= 7 ? 'hsl(var(--danger))' : 'hsl(var(--text-secondary))',
                }}>
                  {deadlineLabel(opp.deadline)}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gap: '8px', fontSize: '14px', color: 'hsl(var(--text-secondary))' }}>
              {opp.duration && <div>⏱️ Duration: {opp.duration}</div>}
              {opp.start_date && <div>📅 Starts: {formatDate(opp.start_date)}</div>}
            </div>
          </div>

          {/* Documents Required */}
          {opp.documents_required.length > 0 && (
            <div className="glass-card animate-in animate-delay-2" style={{ padding: '24px', opacity: 0 }}>
              <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'hsl(var(--text-secondary))' }}>
                Documents Required
              </h3>
              <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '6px', fontSize: '14px' }}>
                {opp.documents_required.map((doc) => (
                  <li key={doc}>📎 {doc}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Metadata */}
          <div className="glass-card animate-in animate-delay-3" style={{ padding: '24px', opacity: 0 }}>
            <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'hsl(var(--text-secondary))' }}>
              Metadata
            </h3>
            <div style={{ display: 'grid', gap: '8px', fontSize: '13px', color: 'hsl(var(--text-muted))' }}>
              <div>Discovered: {formatDate(opp.date_discovered)}</div>
              <div>Last verified: {formatDate(opp.last_verified)}</div>
              <div>Confidence: {confidenceLabel(opp.confidence_score)} ({(opp.confidence_score * 100).toFixed(0)}%)</div>
              <div>Authenticity: {(opp.authenticity_score * 100).toFixed(0)}%</div>
              <a
                href={opp.source_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'hsl(var(--primary))', wordBreak: 'break-all' }}
              >
                View source ↗
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
