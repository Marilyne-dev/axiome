import { useCallback, useEffect, useState } from "react";

/** Charge des données : { data, error, loading, reload }. */
export default function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: "", status: 0, loading: true });
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: "", status: 0 }));
    fn().then((data) => setState({ data, error: "", status: 0, loading: false }))
        .catch((e) => setState({ data: null, error: e.message, status: e.status || 0, loading: false }));
  }, deps); // eslint-disable-line
  useEffect(run, [run]);
  return { ...state, reload: run };
}
