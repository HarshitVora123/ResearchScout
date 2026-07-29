'use client';

import { useEffect, useState, useCallback } from 'react';
import OpportunityCard from '@/components/OpportunityCard';
import type { OpportunityBrief, PaginatedResponse } from '@/lib/api';
import { getOpportunities } from '@/lib/api';

const OPPORTUNITY_TYPES = [
  'PhD', 'Internship', 'Fellowship', 'Scholarship', 'Postdoc',
  'Summer School', 'AI Residency', 'Research Assistant', 'Masters Thesis',
];

const FUNDING_TYPES = ['Fully Funded', 'Partial', 'Self-funded'];

const COUNTRIES = [
  'USA', 'UK', 'Germany', 'Switzerland', 'Canada',
  'Netherlands', 'France', 'Singapore', 'Japan', 'India',
  'Australia', 'Sweden', 'Denmark', 'Austria', 'China',
];

export default function OpportunitiesPage() {
  const [data, setData] = useState<PaginatedResponse<OpportunityBrief> | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedFunding, setSelectedFunding] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('date_discovered');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getOpportunities({
        opportunity_type: selectedTypes.length ? selectedTypes : undefined,
        funding_type: selectedFunding.length ? selectedFunding : undefined,
        country: selectedCountries.length ? selectedCountries : undefined,
        query: search || undefined,
        page,
        page_size: 12,
        sort_by: sortBy,
        sort_order: 'desc',
      });
      setData(result);
    } catch (err) {
      console.error('Failed to fetch opportunities:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedTypes, selectedFunding, selectedCountries, search, page, sortBy]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function toggleFilter(list: string[], setter: (v: string[]) => void, value: string) {
    setter(
      list.includes(value)
        ? list.filter((v) => v !== value)
        : [...list, value]
    );
    setPage(1);
  }

  return (
    <div className="container" style={{ paddingBottom: '60px' }}>
      <div className="page-header">
        <h1 className="page-title animate-in">
          Research <span className="gradient-text">Opportunities</span>
        </h1>
        <p className="page-subtitle animate-in animate-delay-1">
          Browse {data?.total || '...'} verified opportunities from top institutions worldwide
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '24px' }}>
        {/* ── Filters Sidebar ──────────────── */}
        <aside className="glass-card animate-in" style={{ alignSelf: 'start', position: 'sticky', top: '80px', opacity: 0 }}>
          {/* Search */}
          <div className="filter-section">
            <input
              className="input"
              placeholder="🔍 Search opportunities..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>

          {/* Sort */}
          <div className="filter-section">
            <div className="filter-title">Sort by</div>
            <select
              className="input"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="date_discovered">Newest First</option>
              <option value="deadline">Deadline (Soonest)</option>
              <option value="confidence_score">Confidence</option>
            </select>
          </div>

          {/* Opportunity Type */}
          <div className="filter-section">
            <div className="filter-title">Type</div>
            {OPPORTUNITY_TYPES.map((type) => (
              <label key={type} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedTypes.includes(type)}
                  onChange={() => toggleFilter(selectedTypes, setSelectedTypes, type)}
                />
                {type}
              </label>
            ))}
          </div>

          {/* Funding */}
          <div className="filter-section">
            <div className="filter-title">Funding</div>
            {FUNDING_TYPES.map((type) => (
              <label key={type} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedFunding.includes(type)}
                  onChange={() => toggleFilter(selectedFunding, setSelectedFunding, type)}
                />
                {type}
              </label>
            ))}
          </div>

          {/* Country */}
          <div className="filter-section">
            <div className="filter-title">Country</div>
            {COUNTRIES.map((country) => (
              <label key={country} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedCountries.includes(country)}
                  onChange={() => toggleFilter(selectedCountries, setSelectedCountries, country)}
                />
                {country}
              </label>
            ))}
          </div>

          {/* Reset */}
          {(selectedTypes.length > 0 || selectedFunding.length > 0 || selectedCountries.length > 0 || search) && (
            <div className="filter-section">
              <button
                className="btn btn-ghost btn-sm"
                style={{ width: '100%' }}
                onClick={() => {
                  setSelectedTypes([]);
                  setSelectedFunding([]);
                  setSelectedCountries([]);
                  setSearch('');
                  setPage(1);
                }}
              >
                Clear all filters
              </button>
            </div>
          )}
        </aside>

        {/* ── Results Grid ─────────────────── */}
        <div>
          {loading ? (
            <div style={{ display: 'grid', gap: '16px' }}>
              {[...Array(6)].map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '200px', borderRadius: 'var(--radius-lg)' }} />
              ))}
            </div>
          ) : data && data.items.length > 0 ? (
            <>
              <div style={{ display: 'grid', gap: '16px' }}>
                {data.items.map((opp, i) => (
                  <OpportunityCard key={opp.id} opportunity={opp} index={i} />
                ))}
              </div>

              {/* Pagination */}
              {data.total_pages > 1 && (
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '32px' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    ← Previous
                  </button>
                  <span style={{ padding: '8px 16px', fontSize: '14px', color: 'hsl(var(--text-secondary))' }}>
                    Page {data.page} of {data.total_pages}
                  </span>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={page >= data.total_pages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="glass-card" style={{ padding: '60px', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔭</div>
              <h3 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>
                No opportunities found
              </h3>
              <p style={{ color: 'hsl(var(--text-secondary))' }}>
                Try adjusting your filters or check back later as we discover more.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
