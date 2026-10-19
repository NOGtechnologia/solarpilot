// Erzeugt public/favicon.svg aus dem Phosphor-Icon „SunHorizon“ (gleiches Motiv wie components/logo.tsx).
//   node scripts/make-favicon.mjs  &&  node scripts/render-assets.mjs icons
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { SunHorizon } from "@phosphor-icons/react/dist/ssr";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const icon = renderToStaticMarkup(createElement(SunHorizon, { weight: "fill", size: 44, color: "#FFFFFF" }))
  .replace("<svg ", '<svg x="10" y="10" ');

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FCD34D"/>
      <stop offset="0.45" stop-color="#F5A524"/>
      <stop offset="1" stop-color="#EA580C"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="18" fill="url(#g)"/>
  ${icon}
</svg>
`;
writeFileSync(join(root, "public", "favicon.svg"), svg);
console.log("favicon.svg erzeugt");
