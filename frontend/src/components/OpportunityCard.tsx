'use client';

import Link from 'next/link';
import type { OpportunityBrief } from '@/lib/api';
import { typeColor, fundingColor, deadlineLabel, daysUntil, truncate } from '@/lib/utils';

interface Props {
  opportunity: OpportunityBrief;
  index?: number;
}

export default function OpportunityCard({ opportunity, index = 0 }: Props) {
  const days = daysUntil(opportunity.deadline);
  const isUrgent = days !== null && days <= 7;

  return (
    <div
      className={`glass-card opp-card animate-in animate-delay-${Math.min(index % 5, 4)}`}
      style={{ opacity: 0 }}
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
        <Link href={`/opportunities/${opportunity.id}`} className="btn btn-ghost btn-sm">
          View details →
        </Link>
      </div>
    </div>
  );
}
