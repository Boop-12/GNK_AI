"use client";

import { useState } from "react";

const markets = ["NIFTY 50", "BANK NIFTY", "SENSEX", "COMMODITIES"];

export function MarketTicker() {
  const [paused, setPaused] = useState(false);
  return <section className="market-strip" aria-label="Indian market coverage">
    <span className="market-label">INDIAN MARKETS. ONE PERSPECTIVE.</span>
    <div className="market-window">
      <div className={`market-track${paused ? " is-paused" : ""}`}>
        {[0, 1].map(copy => <div className="market-group" key={copy} aria-hidden={copy === 1 ? true : undefined}>
          {markets.map(market => <span className="market-item" key={market}><b>{market}</b><i aria-hidden="true">+</i></span>)}
        </div>)}
      </div>
    </div>
    <span className="market-feed-note">Coverage goals · live feed pending</span>
    <button className="market-pause" type="button" onClick={() => setPaused(!paused)} aria-label={paused ? "Resume market scrolling" : "Pause market scrolling"} aria-pressed={paused} title={paused ? "Resume scrolling" : "Pause scrolling"}>{paused ? "▶" : "Ⅱ"}</button>
  </section>;
}
