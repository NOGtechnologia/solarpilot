import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto mt-16 max-w-md text-center">
      <p className="num text-6xl font-semibold text-solar">404</p>
      <p className="mt-3 text-muted">Diese Seite gibt es nicht. · Page not found.</p>
      <Link href="/" className="mt-6 inline-block rounded-xl bg-solar px-4 py-2 font-medium text-[#0B0F14]">
        SolarPilot
      </Link>
    </div>
  );
}
