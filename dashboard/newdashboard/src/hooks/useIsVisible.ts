import { useEffect, useRef, useState } from 'react';

/**
 * Hook that returns true when the element ref is visible in the viewport.
 * Used to pause polling when a tab is not visible.
 */
export function useIsVisible<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) {
      setIsVisible(true); // Fallback: assume visible if no ref
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}
