/** Utility functions for the frontend */

/** Format a date string to a readable format */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'No date';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'Invalid date';
  }
}

/** Calculate days remaining until a deadline */
export function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const deadline = new Date(dateStr);
  const now = new Date();
  const diff = deadline.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

/** Format days remaining as a human-readable string */
export function deadlineLabel(dateStr: string | null): string {
  const days = daysUntil(dateStr);
  if (days === null) return 'Open';
  if (days === 0) return 'Due today';
  if (days === 1) return '1 day left';
  if (days <= 7) return `${days} days left`;
  if (days <= 30) return `${Math.ceil(days / 7)} weeks left`;
  return formatDate(dateStr);
}

/** Get a color class for opportunity type badges */
export function typeColor(type: string): string {
  const colors: Record<string, string> = {
    PhD: 'badge-purple',
    Internship: 'badge-blue',
    Fellowship: 'badge-emerald',
    Scholarship: 'badge-amber',
    Postdoc: 'badge-rose',
    'Summer School': 'badge-cyan',
    'AI Residency': 'badge-violet',
    'Research Assistant': 'badge-teal',
    'Masters Thesis': 'badge-indigo',
  };
  return colors[type] || 'badge-default';
}

/** Get a color class for funding type badges */
export function fundingColor(type: string | null): string {
  if (!type) return 'badge-default';
  const colors: Record<string, string> = {
    'Fully Funded': 'badge-emerald',
    Partial: 'badge-amber',
    'Self-funded': 'badge-rose',
    Unknown: 'badge-default',
  };
  return colors[type] || 'badge-default';
}

/** Truncate text with ellipsis */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + '…';
}

/** Confidence score to human-readable label */
export function confidenceLabel(score: number): string {
  if (score >= 0.8) return 'High';
  if (score >= 0.5) return 'Medium';
  return 'Low';
}
