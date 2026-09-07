/**
 * jsdom performs no layout, so every element measures 0x0 and Recharts'
 * ResponsiveContainer renders nothing. Tests that need a chart to lay out call
 * this to give elements a size, then restore it afterwards.
 */
export function giveLayout(width = 640, height = 400) {
  const original = Element.prototype.getBoundingClientRect;
  const rect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: width,
    bottom: height,
    width,
    height,
    toJSON: () => ({}),
  } as DOMRect;

  Element.prototype.getBoundingClientRect = () => rect;

  return () => {
    Element.prototype.getBoundingClientRect = original;
  };
}
