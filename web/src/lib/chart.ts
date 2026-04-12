export interface NumericAxisBounds {
  max: number;
  min: number;
}

export function getPaddedNumericAxisBounds(values: number[]): NumericAxisBounds | null {
  if (values.length === 0) {
    return null;
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum;

  if (range > 0) {
    const padding = range * 0.1;
    return {
      min: minimum - padding,
      max: maximum + padding,
    };
  }

  const baselinePadding = Math.abs(maximum) * 0.1;
  const padding = baselinePadding > 0 ? baselinePadding : 1;
  return {
    min: minimum - padding,
    max: maximum + padding,
  };
}
