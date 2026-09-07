import "@testing-library/jest-dom/vitest";

// jsdom does not implement scrollIntoView, which the chat panel uses to autoscroll.
Element.prototype.scrollIntoView ??= () => {};

// jsdom has no ResizeObserver; Recharts' ResponsiveContainer measures with one.
class ResizeObserverStub implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element) {
    this.callback(
      [{ target, contentRect: target.getBoundingClientRect() } as ResizeObserverEntry],
      this,
    );
  }

  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver ??= ResizeObserverStub;
