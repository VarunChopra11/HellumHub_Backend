import { useState } from 'react';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from '@/components/ui';

interface AdminKeyGateProps {
  onSubmit: (key: string) => void;
}

export function AdminKeyGate({ onSubmit }: AdminKeyGateProps) {
  const [apiKey, setApiKey] = useState('');

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>OTA Dashboard</CardTitle>
          <CardDescription>Enter the admin key to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (apiKey.trim()) {
                onSubmit(apiKey.trim());
              }
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="admin-api-key">Admin API Key</Label>
              <Input
                id="admin-api-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Enter key"
                autoFocus
              />
            </div>
            <Button type="submit" className="w-full" disabled={!apiKey.trim()}>
              Continue
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
