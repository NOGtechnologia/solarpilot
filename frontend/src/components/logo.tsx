export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden focusable="false">
      <defs>
        <linearGradient id="sp-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FBBF24" />
          <stop offset="1" stopColor="#F97316" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="#0B0F14" />
      <path d="M12 44a20 20 0 0 1 40 0" fill="none" stroke="url(#sp-logo)" strokeWidth="5" strokeLinecap="round" />
      <circle cx="32" cy="44" r="9" fill="url(#sp-logo)" />
      <path d="M32 14v6M14.5 21.5l4.2 4.2M49.5 21.5l-4.2 4.2" stroke="#FBBF24" strokeWidth="4" strokeLinecap="round" />
      <path d="M8 52h48" stroke="#8B5CF6" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}
