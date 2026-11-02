import Link from 'next/link';

const features = [
  {
    icon: '🤖',
    title: 'AI-Powered Discovery',
    desc: 'Autonomous agents search, crawl, and extract research opportunities from thousands of sources across the global internet — 24/7.',
  },
  {
    icon: '🎯',
    title: 'Personalized Matching',
    desc: 'Multi-signal ranking engine matches opportunities to your skills, publications, research interests, and career goals.',
  },
  {
    icon: '🛡️',
    title: 'Verified & Trusted',
    desc: 'Every opportunity passes 6 validation checks including scam detection, domain trust scoring, and hallucination detection.',
  },
  {
    icon: '🧠',
    title: 'Knowledge Graph',
    desc: 'Neo4j-powered knowledge graph connects researchers, organizations, topics, and opportunities for deep insights.',
  },
  {
    icon: '⚡',
    title: 'Real-time Alerts',
    desc: 'Get notified instantly via email, Telegram, or Discord when new opportunities matching your profile are discovered.',
  },
  {
    icon: '📊',
    title: 'Smart Analytics',
    desc: 'Track application progress, analyze trends, and get AI-generated cover letters and professor email drafts.',
  },
];

const stats = [
  { value: '10K+', label: 'Opportunities' },
  { value: '500+', label: 'Sources' },
  { value: '20+', label: 'AI Agents' },
  { value: '50+', label: 'Countries' },
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
            AI agents autonomously discover PhD positions, internships,
            fellowships, and scholarships from thousands of sources worldwide —
            personalized to your research profile.
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

          <div className="hero-stats animate-in animate-delay-3">
            {stats.map((stat) => (
              <div key={stat.label} className="glass-card stat-card">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────── */}
      <section className="container">
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <h2 className="page-title animate-in">
            Powered by <span className="gradient-text">Multi-Agent AI</span>
          </h2>
          <p className="page-subtitle animate-in animate-delay-1">
            20+ specialized agents work together to discover, verify, and recommend opportunities
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
            Create a free profile and let our AI agents find opportunities tailored to your
            research interests and skills.
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
          <p>© 2025 ResearchScout. Built with AI agents for researchers worldwide.</p>
        </div>
      </footer>
    </>
  );
}
