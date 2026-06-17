"use client";

import { useEffect, useRef } from "react";
import Pusher from "pusher-js";
import { api } from "./api";

type RealtimeHandlers = {
  onBalanceUpdate?: (data: { account_id: number; balance: number; reference_id: string }) => void;
  onTransaction?: (data: Record<string, unknown>) => void;
};

export function useRealtime(userId: number | null, handlers: RealtimeHandlers) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!userId) return;

    let pusher: Pusher | null = null;

    async function connect() {
      const key = process.env.NEXT_PUBLIC_PUSHER_KEY;
      if (!key) return;

      pusher = new Pusher(key, {
        cluster: process.env.NEXT_PUBLIC_PUSHER_CLUSTER || "ap2",
        authEndpoint: "/api/security/pusher-auth",
      });

      const channel = pusher.subscribe(`private-user-${userId}`);
      channel.bind("balance.updated", (data: { account_id: number; balance: number; reference_id: string }) => {
        handlersRef.current.onBalanceUpdate?.(data);
      });
      channel.bind("transaction.created", (data: Record<string, unknown>) => {
        handlersRef.current.onTransaction?.(data);
      });
    }

    connect();
    return () => {
      pusher?.disconnect();
    };
  }, [userId]);
}
