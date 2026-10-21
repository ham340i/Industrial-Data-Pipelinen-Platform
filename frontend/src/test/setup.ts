import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";
import { useEditorStore } from "../state/editor";

// React Flow measures its container with ResizeObserver, absent in jsdom.
class TestResizeObserver implements ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = TestResizeObserver;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  useEditorStore.getState().reset();
  if (typeof localStorage !== "undefined") localStorage.clear();
});
afterAll(() => server.close());
