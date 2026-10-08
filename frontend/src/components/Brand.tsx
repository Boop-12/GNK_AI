import Link from "next/link";

export function Brand() {
  return <Link href="/" className="gnk-brand" aria-label="GNK ALGO home"><span className="gnk-monogram" aria-hidden="true">G<span>↗</span></span><span>GNK <b>ALGO</b><small>INTELLIGENCE IN MOTION</small></span></Link>;
}
