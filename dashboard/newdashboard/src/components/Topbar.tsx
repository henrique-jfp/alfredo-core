export function Topbar({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="mb-6 flex flex-col gap-4 md:gap-5">
      <div className="alfredo-card overflow-hidden px-4 py-4 md:px-6 md:py-5">
        <div className="max-w-2xl">
          <div className="alfredo-section-label mb-2">Briefing do Dia</div>
          <h1 className="alfredo-page-title">{title}</h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--text-secondary)]">{subtitle}</p>
        </div>
      </div>
    </header>
  );
}
