"use client";

import { ArrowSquareOut, Newspaper } from "@phosphor-icons/react";

import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtRelative } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { NewsItem } from "@/lib/types";

export function NewsCard({ data }: { data: { items: NewsItem[]; enabled: boolean } | undefined }) {
  const { t, lang } = useI18n();
  return (
    <Card>
      <CardHeader title={t("news.title")} icon={<Newspaper size={14} />} />
      {!data ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : !data.enabled ? (
        <p className="text-sm text-muted">{t("news.disabled")}</p>
      ) : !data.items.length ? (
        <p className="text-sm text-muted">{t("news.none")}</p>
      ) : (
        <ul className="-mx-2 divide-y divide-border">
          {data.items.slice(0, 6).map((n) => (
            <li key={n.link}>
              <a
                href={n.link}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="group flex flex-col gap-1 rounded-xl px-2 py-2.5 hover:bg-card-2"
              >
                <span className="flex items-start gap-1 text-sm font-medium leading-snug">
                  <span className="line-clamp-2">{n.title}</span>
                  <ArrowSquareOut size={12} className="mt-1 shrink-0 text-muted opacity-0 group-hover:opacity-100" aria-hidden />
                </span>
                <span className="text-[11px] text-muted">
                  {n.source} · {fmtRelative(n.published, lang)}
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
