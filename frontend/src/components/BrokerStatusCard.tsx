"use client";

import { useEffect, useState } from "react";
import { protectedRequest } from "@/lib/auth";

type BrokerStatus = {
  broker: string;
  name: string;
  status: string;
  marketDataStatus: string;
  tradingStatus: string;
  marketDataConfigured: boolean;
  tradingConfigured: boolean;
  redirectUrlConfigured: boolean;
};

export function BrokerStatusCard() {
  const [items, setItems] = useState<BrokerStatus[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    protectedRequest<BrokerStatus[]>("/brokers")
      .then(setItems)
      .catch(() => setFailed(true));
  }, []);

  return (
    <section className="broker-status-card" aria-labelledby="broker-status-title">
      <div className="broker-status-heading">
        <div>
          <p className="eyebrow green">TRADING CONNECTIONS</p>
          <h2 id="broker-status-title">Broker setup</h2>
        </div>
        <span className={`broker-state ${items?.some((item) => item.status === "CONNECTED") ? "is-connected" : ""}`}>
          {failed ? "Unavailable" : items?.length ? items[0].status.replaceAll("_", " ") : items ? "No brokers enabled" : "Loading"}
        </span>
      </div>
      {failed ? (
        <p className="muted">Broker status could not be loaded. Please refresh your session and try again.</p>
      ) : items?.length ? (
        <div className="broker-status-list">
          {items.map((item) => (
            <div className="broker-status-item" key={item.broker}>
              <div className="broker-status-name"><strong>{item.name}</strong><span>{item.status.replaceAll("_", " ")}</span></div>
              <div className="broker-status-meta">
                <span>Market Data API <b>{item.marketDataStatus.replaceAll("_", " ")}</b></span>
                <span>Trading API <b>{item.tradingStatus.replaceAll("_", " ")}</b></span>
                <span>Redirect URL setting <b>{item.redirectUrlConfigured ? "Set (not active)" : "Unset"}</b></span>
              </div>
              {item.status === "NOT_CONFIGURED" && (
                <p className="broker-setup-note">Add this broker’s approved API host and separate credentials to the server environment. The live authentication flow is not enabled yet.</p>
              )}
              {item.status === "DISCONNECTED" && (
                <p className="broker-setup-note">API settings are present, but no live broker session has been established.</p>
              )}
            </div>
          ))}
        </div>
      ) : items ? (
        <p className="muted">No broker has been enabled by the server administrator.</p>
      ) : (
        <p className="muted">Loading broker status…</p>
      )}
    </section>
  );
}
