'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { getNotificationSettings, saveNotificationSettings, type NotificationSettings } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

const defaults: NotificationSettings = {
  email_enabled: true,
  telegram_enabled: false,
  telegram_chat_id: '',
  discord_enabled: false,
  discord_webhook_url: '',
  daily_digest: true,
  deadline_reminders: true,
};
type ToggleKey = 'email_enabled' | 'daily_digest' | 'deadline_reminders' | 'telegram_enabled' | 'discord_enabled';

export default function NotificationSettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [settings, setSettings] = useState(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace('/login');
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    getNotificationSettings()
      .then((value) => setSettings((current) => ({ ...current, ...value })))
      .catch((error: unknown) => setMessage(error instanceof Error ? error.message : 'Could not load settings.'))
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  function toggle(key: ToggleKey) {
    setSettings((current) => ({ ...current, [key]: !current[key] }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      await saveNotificationSettings(settings);
      setMessage('Settings saved.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save settings.');
    } finally {
      setSaving(false);
    }
  }

  if (loading || isLoading) return <div className="container" style={{ padding: 48 }}>Loading settings…</div>;

  return (
    <div className="container" style={{ maxWidth: 760, paddingBottom: 60 }}>
      <div className="page-header">
        <h1 className="page-title">Notification settings</h1>
        <p className="page-subtitle">Choose which ResearchScout updates you receive.</p>
      </div>
      <form className="glass-card" onSubmit={submit} style={{ padding: 28, display: 'grid', gap: 18 }}>
        {([
          ['email_enabled', 'Email notifications'],
          ['daily_digest', 'Daily opportunity digest'],
          ['deadline_reminders', 'Deadline reminders'],
          ['telegram_enabled', 'Telegram notifications'],
          ['discord_enabled', 'Discord notifications'],
        ] as [ToggleKey, string][]).map(([key, label]) => (
          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="checkbox" checked={Boolean(settings[key])} onChange={() => toggle(key)} />
            {label}
          </label>
        ))}
        <label className="input-group">
          <span className="input-label">Telegram chat ID</span>
          <input className="input" value={settings.telegram_chat_id || ''} onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })} />
        </label>
        <label className="input-group">
          <span className="input-label">Discord webhook URL</span>
          <input className="input" type="url" value={settings.discord_webhook_url || ''} onChange={(e) => setSettings({ ...settings, discord_webhook_url: e.target.value })} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save settings'}</button>
        {message && <p role="status">{message}</p>}
      </form>
    </div>
  );
}
