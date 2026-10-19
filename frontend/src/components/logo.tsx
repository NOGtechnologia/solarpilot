import { SunHorizon } from "@phosphor-icons/react/dist/ssr";

/** App-Icon: Amber-Verlauf mit Sonnenaufgang (Phosphor „SunHorizon“, gefüllt). */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="inline-flex shrink-0 items-center justify-center"
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.28,
        background: "linear-gradient(140deg, #FCD34D 0%, #F5A524 45%, #EA580C 100%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,.45), 0 2px 8px rgba(245,165,36,.35)",
      }}
    >
      <SunHorizon weight="fill" size={Math.round(size * 0.68)} color="#FFFFFF" />
    </span>
  );
}
