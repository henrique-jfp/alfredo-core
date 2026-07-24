export function Topbar({ title, subtitle, eyebrow }: { title: string; subtitle: string; eyebrow?: string }) {
  return (
    <header className="mb-6 flex flex-col gap-4 md:gap-5">
      <div className="alfredo-card overflow-hidden p-5 md:p-6">
        <div className="max-w-2xl">
          {eyebrow && <div className="alfredo-section-label mb-2">{eyebrow}</div>}
          <h1 className="alfredo-page-title">{title}</h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{subtitle}</p>
        </div>
      </div>
    </header>
  );
}

