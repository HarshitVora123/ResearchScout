import Link from 'next/link';

const features = [
  {
    icon: '🔎',
    title: 'Search research roles',
    desc: 'Browse PhD positions, internships, fellowships, and scholarships in one place.',
  },
  {
    icon: '🎯',
    title: 'Personalized Matching',
    desc: 'Add your research interests and skills to see relevant openings more easily.',
  },
  {
    icon: '🛡️',
    title: 'Verified & Trusted',
    desc: 'Each listing links back to its source so you can check the details before applying.',
  },
  {
    icon: '🧠',
    title: 'Useful filters',
    desc: 'Narrow results by location, subject, role type, funding, or deadline.',
  },
  {
    icon: '⚡',
    title: 'Save your search',
    desc: 'Keep track of the openings you want to revisit while you prepare an application.',
  },
  {
    icon: '📊',
    title: 'Application help',
    desc: 'Use the available application tools to organize your materials and draft outreach.',
  },
];

export default function HomePage() {
  return (
    <>
      {/* ── Hero ─────────────────────────────── */}
      <section className="hero">
        <div className="container">
          <h1 className="hero-title animate-in">
            Discover Your Next{' '}
            <span className="gradient-text">Research Opportunity</span>
          </h1>
          <p className="hero-subtitle animate-in animate-delay-1">
            Search PhD positions, internships, fellowships, and scholarships.
            Filter by field and location, then follow the source link for details.
          </p>

          <div className="hero-actions animate-in animate-delay-2">
            <Link href="/opportunities" className="btn btn-primary btn-lg">
              Browse Opportunities
            </Link>
            <Link href="/register" className="btn btn-secondary btn-lg">
              Create Profile
            </Link>
          </div>

          {/* Quick Search */}
          <div className="animate-in animate-delay-2" style={{ maxWidth: '580px', margin: '24px auto 0' }}>
            <form action="/opportunities" method="GET" style={{ display: 'flex', gap: '8px' }}>
              <input
                name="query"
                type="text"
                className="input"
                placeholder="🔍 Search by topic (e.g., LLMs, Robotics, Bioinformatics)..."
                style={{ background: 'hsl(var(--bg-card) / 0.8)', padding: '14px 18px', fontSize: '15px' }}
              />
              <button type="submit" className="btn btn-primary" style={{ padding: '0 24px' }}>
                Search
              </button>
            </form>
            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginTop: '12px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'hsl(var(--text-muted))', alignSelf: 'center' }}>Popular:</span>
              {['AI & LLMs', 'Robotics', 'Quantum', 'Computer Vision'].map((tag) => (
                <Link
                  key={tag}
                  href={`/opportunities?query=${encodeURIComponent(tag)}`}
                  className="badge badge-purple"
                  style={{ textDecoration: 'none', cursor: 'pointer', fontSize: '11px' }}
                >
                  {tag}
                </Link>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* ── Features ─────────────────────────── */}
      <section className="container">
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <h2 className="page-title animate-in">
            Made for your search
          </h2>
          <p className="page-subtitle animate-in animate-delay-1">
            Practical tools to find openings and keep your applications organized.
          </p>
        </div>

        <div className="features-grid">
          {features.map((feature, i) => (
            <div key={feature.title} className={`glass-card feature-card animate-in animate-delay-${Math.min(i, 4)}`}>
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-desc">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────── */}
      <section className="container" style={{ padding: '80px 24px', textAlign: 'center' }}>
        <div className="glass-card" style={{ padding: '60px 40px', maxWidth: '700px', margin: '0 auto' }}>
          <h2 className="page-title">Ready to find your next position?</h2>
          <p className="page-subtitle" style={{ marginBottom: '32px' }}>
            Create a profile to save your interests and get started browsing.
          </p>
          <Link href="/register" className="btn btn-accent btn-lg">
            Get Started — It&apos;s Free
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────── */}
      <footer style={{
        borderTop: '1px solid hsl(var(--border-subtle))',
        padding: '32px 0',
        textAlign: 'center',
        color: 'hsl(var(--text-muted))',
        fontSize: '13px',
      }}>
        <div className="container">
          <p>© 2026 ResearchScout</p>
        </div>
      </footer>
    </>
  );
}
