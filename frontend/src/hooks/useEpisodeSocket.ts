import { useEffect, useReducer, useRef } from "react";

import { api, socketUrl } from "@/services/api";
import type {
  EpisodeDetail,
  EpisodeStatus,
  EvaluationReport,
  LiveState,
  Performance,
  SimEvent,
  SocketMessage,
} from "@/types/api";

export type ConnectionStatus = "connecting" | "open" | "closed";
const MAX_EVENTS = 600;
const RECONNECT_MS = 1500;

export interface EpisodeFeed {
  connection: ConnectionStatus;
  episode: EpisodeDetail | null;
  state: LiveState | null;
  status: EpisodeStatus | null;
  events: SimEvent[];
  evaluation: EvaluationReport | null;
  performance: Performance;
}

type FeedAction =
  | { kind: "connection"; connection: ConnectionStatus }
  | { kind: "history"; events: SimEvent[] }
  | { kind: "evaluation"; evaluation: EvaluationReport }
  | { kind: "message"; message: SocketMessage };

const INITIAL: EpisodeFeed = {
  connection: "connecting",
  episode: null,
  state: null,
  status: null,
  events: [],
  evaluation: null,
  performance: {},
};

/** Merge events by sequence number. A batch that restarts at 1 means the episode was reset. */
export function mergeEvents(current: SimEvent[], incoming: SimEvent[]): SimEvent[] {
  if (incoming.length === 0) return current;
  const restarted = incoming[0].seq === 1 && current.length > 0 && current[current.length - 1].seq >= 1;
  const base = restarted ? [] : current;
  const lastSeq = base.length ? base[base.length - 1].seq : 0;
  const fresh = incoming.filter((event) => event.seq > lastSeq);
  return [...base, ...fresh].slice(-MAX_EVENTS);
}

export function feedReducer(feed: EpisodeFeed, action: FeedAction): EpisodeFeed {
  switch (action.kind) {
    case "connection":
      return { ...feed, connection: action.connection };
    case "history":
      return { ...feed, events: mergeEvents(action.events, feed.events) };
    case "evaluation":
      return { ...feed, evaluation: action.evaluation };
    case "message": {
      const message = action.message;
      switch (message.type) {
        case "hello":
          return {
            ...feed,
            episode: message.episode,
            state: message.state,
            status: message.state?.status ?? message.episode.status,
          };
        case "state": {
          const wasReset = feed.state !== null && message.state.metrics.steps < feed.state.metrics.steps;
          return {
            ...feed,
            state: message.state,
            status: message.state.status,
            evaluation: wasReset ? null : feed.evaluation,
          };
        }
        case "events":
          return { ...feed, events: mergeEvents(feed.events, message.events) };
        case "finished":
          return { ...feed, evaluation: message.evaluation };
        case "status":
          return { ...feed, status: message.status };
        case "perf":
          return { ...feed, performance: message.perf };
      }
    }
  }
}

/** Live feed for one episode: state, events, the final evaluation and render performance. */
export function useEpisodeSocket(episodeId: string | undefined): EpisodeFeed {
  const [feed, dispatch] = useReducer(feedReducer, INITIAL);
  const closedByUs = useRef(false);

  useEffect(() => {
    if (!episodeId) return;
    closedByUs.current = false;
    let socket: WebSocket | null = null;
    let retry: number | undefined;

    api.events(episodeId).then(
      (events) => dispatch({ kind: "history", events }),
      () => undefined,
    );
    api.evaluation(episodeId).then(
      (evaluation) => dispatch({ kind: "evaluation", evaluation }),
      () => undefined,
    );

    const connect = () => {
      dispatch({ kind: "connection", connection: "connecting" });
      socket = new WebSocket(socketUrl(episodeId));
      socket.onopen = () => dispatch({ kind: "connection", connection: "open" });
      socket.onmessage = (event) =>
        dispatch({ kind: "message", message: JSON.parse(event.data as string) as SocketMessage });
      socket.onclose = () => {
        dispatch({ kind: "connection", connection: "closed" });
        if (!closedByUs.current) retry = window.setTimeout(connect, RECONNECT_MS);
      };
    };
    connect();

    return () => {
      closedByUs.current = true;
      if (retry) window.clearTimeout(retry);
      socket?.close();
    };
  }, [episodeId]);

  return feed;
}
