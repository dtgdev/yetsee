"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

type Props = {
  candidateId: string;
  status: string;
};

export default function PromotionActions({ candidateId, status }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function promote(override: boolean) {
    setBusy(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      if (override) {
        query.set("override", "true");
        query.set("reason", "Local Studio runtime testing");
      }
      const suffix = query.size ? `?${query.toString()}` : "";
      const response = await fetch(`${API_URL}/api/v1/discovery/candidates/${candidateId}/promote${suffix}`, {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail ?? `Promotion failed (${response.status})`);
      }
      router.push(`/investigations/${payload.id}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Promotion failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="promotionActions">
      {status === "candidate" ? (
        <button disabled={busy} onClick={() => promote(false)}>Create investigation</button>
      ) : (
        <button disabled={busy} onClick={() => promote(true)}>Promote for local testing</button>
      )}
      {status === "watch" && <span>Override is audited and blocked in production.</span>}
      {error && <p>{error}</p>}
    </div>
  );
}
