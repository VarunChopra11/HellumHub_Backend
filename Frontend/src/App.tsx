import { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { getApiKey, setApiKey, setUnauthorizedHandler } from '@/api';
import { AdminKeyGate } from '@/components/auth/admin-key-gate';
import { AppShell } from '@/components/layout/app-shell';
import { AuditPage } from '@/pages/audit-page';
import { DevicesPage } from '@/pages/devices-page';
import { OverridesPage } from '@/pages/overrides-page';
import { ReleaseDetailPage } from '@/pages/release-detail-page';
import { ReleasesPage } from '@/pages/releases-page';

export default function App() {
  const navigate = useNavigate();
  const [keyVersion, setKeyVersion] = useState(0);

  const hasApiKey = useMemo(() => Boolean(getApiKey()), [keyVersion]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setKeyVersion((value) => value + 1);
      navigate('/');
    });
  }, [navigate]);

  if (!hasApiKey) {
    return (
      <AdminKeyGate
        onSubmit={(key) => {
          setApiKey(key);
          setKeyVersion((value) => value + 1);
          navigate('/releases');
        }}
      />
    );
  }

  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Navigate to="/releases" replace />} />
        <Route path="releases" element={<ReleasesPage />} />
        <Route path="releases/:releaseId" element={<ReleaseDetailPage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="overrides" element={<OverridesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
