import { describe, expect, it } from "vitest";

import { buildGoalForecastSeries } from "./goalForecast";

describe("buildGoalForecastSeries", () => {
  it("builds a simple slope forecast from the first to the last actual point", () => {
    const forecast = buildGoalForecastSeries({
      actualPoints: [
        {
          timestamp: new Date("2026-04-01T00:00:00Z").getTime(),
          value: 250,
        },
        {
          timestamp: new Date("2026-04-06T00:00:00Z").getTime(),
          value: 240,
        },
      ],
      algorithm: "simple",
      nowTimestamp: new Date("2026-04-08T00:00:00Z").getTime(),
      targetValue: 220,
    });

    expect(forecast.bridgeSeries.at(-1)).toEqual([
      new Date("2026-04-08T00:00:00Z").getTime(),
      236,
    ]);
    expect(forecast.futureSeries.at(-1)).toEqual([
      new Date("2026-04-16T00:00:00Z").getTime(),
      220,
    ]);
  });

  it("builds a weighted week-over-week forecast from weekly changes", () => {
    const forecast = buildGoalForecastSeries({
      actualPoints: [
        { timestamp: new Date("2026-04-01T12:00:00Z").getTime(), value: 250 },
        { timestamp: new Date("2026-04-08T12:00:00Z").getTime(), value: 246 },
        { timestamp: new Date("2026-04-15T12:00:00Z").getTime(), value: 241 },
      ],
      algorithm: "weighted_week_over_week",
      nowTimestamp: new Date("2026-04-22T12:00:00Z").getTime(),
      targetValue: 230,
    });

    expect(forecast.bridgeSeries.at(-1)?.[1]).toBeCloseTo(236.44, 2);
    expect(forecast.futureSeries.at(-1)?.[0]).toBeGreaterThan(
      new Date("2026-04-22T12:00:00Z").getTime(),
    );
    expect(forecast.futureSeries.at(-1)?.[1]).toBe(230);
  });

  it("builds a weighted day-over-day forecast using weekday deltas", () => {
    const forecast = buildGoalForecastSeries({
      actualPoints: [
        { timestamp: new Date("2026-04-06T12:00:00Z").getTime(), value: 250 },
        { timestamp: new Date("2026-04-07T12:00:00Z").getTime(), value: 249 },
        { timestamp: new Date("2026-04-08T12:00:00Z").getTime(), value: 247 },
        { timestamp: new Date("2026-04-09T12:00:00Z").getTime(), value: 246 },
        { timestamp: new Date("2026-04-13T12:00:00Z").getTime(), value: 245 },
        { timestamp: new Date("2026-04-14T12:00:00Z").getTime(), value: 244 },
        { timestamp: new Date("2026-04-15T12:00:00Z").getTime(), value: 242 },
      ],
      algorithm: "weighted_day_over_day",
      nowTimestamp: new Date("2026-04-16T12:00:00Z").getTime(),
      targetValue: 240,
    });

    expect(forecast.bridgeSeries.at(-1)?.[1]).toBeCloseTo(240.88, 2);
    expect(forecast.nowPoint?.[1]).toBeCloseTo(240.88, 2);
    expect(forecast.futureSeries.at(-1)?.[0]).toBeGreaterThan(
      new Date("2026-04-16T12:00:00.000Z").getTime(),
    );
    expect(forecast.futureSeries.at(-1)?.[1]).toBe(240);
  });

  it("falls back from week-over-week to simple when there is not enough weekly delta history", () => {
    const forecast = buildGoalForecastSeries({
      actualPoints: [
        {
          timestamp: new Date("2026-04-01T00:00:00Z").getTime(),
          value: 250,
        },
        {
          timestamp: new Date("2026-04-06T00:00:00Z").getTime(),
          value: 240,
        },
      ],
      algorithm: "weighted_week_over_week",
      nowTimestamp: new Date("2026-04-08T00:00:00Z").getTime(),
      targetValue: 220,
    });

    expect(forecast.bridgeSeries.at(-1)).toEqual([
      new Date("2026-04-08T00:00:00Z").getTime(),
      236,
    ]);
    expect(forecast.futureSeries.at(-1)).toEqual([
      new Date("2026-04-16T00:00:00Z").getTime(),
      220,
    ]);
  });

  it("falls back from day-over-day to week-over-week when consecutive daily deltas are unavailable", () => {
    const forecast = buildGoalForecastSeries({
      actualPoints: [
        { timestamp: new Date("2026-04-01T12:00:00Z").getTime(), value: 250 },
        { timestamp: new Date("2026-04-08T12:00:00Z").getTime(), value: 246 },
        { timestamp: new Date("2026-04-15T12:00:00Z").getTime(), value: 241 },
      ],
      algorithm: "weighted_day_over_day",
      nowTimestamp: new Date("2026-04-22T12:00:00Z").getTime(),
      targetValue: 230,
    });

    expect(forecast.bridgeSeries.at(-1)?.[1]).toBeCloseTo(236.44, 2);
    expect(forecast.futureSeries.at(-1)?.[1]).toBe(230);
  });
});
