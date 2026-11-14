import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * Load data when the component mounts or `deps` change.
 * Pass `refreshMs` to poll, for example on dashboards that show live counts.
 */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = [], refreshMs?: number): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const load = useCallback(async (isActive: () => boolean) => {
    try {
      const result = await loaderRef.current();
      if (isActive()) {
        setData(result);
        setError(null);
      }
    } catch (reason) {
      if (isActive()) setError(reason instanceof Error ? reason.message : "Something went wrong.");
    } finally {
      if (isActive()) setLoading(false);
    }
  }, []);

  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    const isActive = () => active;
    setLoading(true);
    void load(isActive);
    const timer = refreshMs ? window.setInterval(() => void load(isActive), refreshMs) : undefined;
    return () => {
      active = false;
      if (timer) window.clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken, refreshMs, load]);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);
  return { data, error, loading, reload };
}
