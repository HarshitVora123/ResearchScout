'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { OpportunityBrief } from '@/lib/api';
import { saveOpportunity, unsaveOpportunity } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { typeColor, fundingColor, deadlineLabel, daysUntil, truncate } from '@/lib/utils';

interface Props {
  opportunity: OpportunityBrief;
  index?: number;
  initialSaved?: boolean;
}

export default function OpportunityCard({ opportunity, index = 0, initialSaved = false }: Props) {
  const { token, isAuthenticated } = useAuth();
  const [saved, setSaved] = useState(initialSaved);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const days = daysUntil(opportunity.deadline);
  const isUrgent = days !== null && days <= 7;

  async function handleToggleSave(e: React.MouseEvent) {
    e.preventDefault();
    if (!isAuthenticated || !token || saving) return;
    setSaving(true);
    setSaveError('');
    try {
      if (saved) {
        await unsaveOpportunity(opportunity.id, token);
        setSaved(false);
      } else {
        await saveOpportunity(opportunity.id, token);
        setSaved(true);
      }
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Could not update saved opportunity.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={`glass-card opp-card animate-in animate-delay-${Math.min(index % 5, 4)}`}
    >
      <div className="opp-card-header">
        <div>
          <Link href={`/opportunities/${opportunity.id}`}>
            <h3 className="opp-card-title">{opportunity.title}</h3>
          </Link>
          <p className="opp-card-org">
            🏛️ {opportunity.organization}
            {opportunity.country && ` · 📍 ${opportunity.country}`}
            {opportunity.city && `, ${opportunity.city}`}
          </p>
        </div>
      </div>

      {opportunity.summary && (
        <p style={{ fontSize: '14px', color: 'hsl(var(--text-secondary))', lineHeight: 1.5 }}>
          {truncate(opportunity.summary, 140)}
        </p>
      )}

      <div className="opp-card-tags">
        <span className={`badge ${typeColor(opportunity.opportunity_type)}`}>
          {opportunity.opportunity_type}
        </span>
        {opportunity.funding_type && (
          <span className={`badge ${fundingColor(opportunity.funding_type)}`}>
            {opportunity.funding_type}
          </span>
        )}
        {opportunity.location_type && (
          <span className="badge badge-default">{opportunity.location_type}</span>
        )}
      </div>

      {opportunity.research_areas.length > 0 && (
        <div className="opp-card-tags">
          {opportunity.research_areas.slice(0, 3).map((area) => (
            <span key={area} className="badge badge-default" style={{ fontSize: '11px' }}>
              {area}
            </span>
          ))}
          {opportunity.research_areas.length > 3 && (
            <span className="badge badge-default" style={{ fontSize: '11px' }}>
              +{opportunity.research_areas.length - 3} more
            </span>
          )}
        </div>
      )}

      <div className="opp-card-footer">
        <span className={`deadline-badge ${isUrgent ? 'urgent' : 'normal'}`}>
          ⏰ {deadlineLabel(opportunity.deadline)}
        </span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isAuthenticated && (
            <button
              onClick={handleToggleSave}
              disabled={saving}
              className={`btn btn-sm ${saved ? 'btn-accent' : 'btn-ghost'}`}
              title={saved ? 'Remove from saved' : 'Save opportunity'}
              style={{ fontSize: '12px' }}
            >
              {saved ? '★ Saved' : '☆ Save'}
            </button>
          )}
          <Link href={`/opportunities/${opportunity.id}`} className="btn btn-ghost btn-sm">
            View details →
          </Link>
        </div>
      </div>
      {saveError && <p role="alert" style={{ color: '#f87171', fontSize: 12, marginTop: 8 }}>{saveError}</p>}
    </div>
  );
}
