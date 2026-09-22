export default function Loading() {
  return (
    <section
      className="loading-state top-space"
      aria-live="polite"
      aria-busy="true"
    >
      <p className="eyebrow">
        FSC
      </p>
      <div className="loading-bar" />
      <div className="loading-line wide" />
      <div className="loading-line" />
      <span className="sr-only">
        Inhalte werden geladen.
      </span>
    </section>
  );
}
