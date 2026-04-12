export type ForecastAlgorithm =
  | "simple"
  | "weighted_week_over_week"
  | "weighted_day_over_day";

export interface ForecastChartPoint {
  timestamp: number;
  value: number;
}

export interface ForecastSeries {
  bridgeSeries: Array<[number, number]>;
  futureSeries: Array<[number, number]>;
  nowPoint: [number, number] | null;
}

interface DailyPoint {
  averageValue: number;
  dayIndex: number;
  dayOfWeek: number;
}

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEK_MS = 7 * DAY_MS;
const MAX_FORECAST_DAYS = 3650;

function getLocalDayIndex(timestamp: number): number {
  const date = new Date(timestamp);
  return Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / DAY_MS);
}

function getLocalDayStartTimestamp(timestamp: number): number {
  const date = new Date(timestamp);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

function getNextLocalDayStartTimestamp(timestamp: number): number {
  const date = new Date(timestamp);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1).getTime();
}

function buildDailyPoints(
  points: ForecastChartPoint[],
  { nowTimestamp }: { nowTimestamp: number },
): DailyPoint[] {
  const buckets = new Map<number, { count: number; dayOfWeek: number; sum: number }>();

  for (const point of points) {
    if (!Number.isFinite(point.timestamp) || !Number.isFinite(point.value) || point.timestamp > nowTimestamp) {
      continue;
    }

    const dayIndex = getLocalDayIndex(point.timestamp);
    const existing = buckets.get(dayIndex);
    if (existing === undefined) {
      const pointDate = new Date(point.timestamp);
      buckets.set(dayIndex, {
        count: 1,
        dayOfWeek: pointDate.getDay(),
        sum: point.value,
      });
      continue;
    }

    existing.count += 1;
    existing.sum += point.value;
  }

  return [...buckets.entries()]
    .sort(([leftDayIndex], [rightDayIndex]) => leftDayIndex - rightDayIndex)
    .map(([dayIndex, bucket]) => ({
      averageValue: bucket.sum / bucket.count,
      dayIndex,
      dayOfWeek: bucket.dayOfWeek,
    }));
}

function weightedAverage(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  if (values.length === 1) {
    return values[0] ?? null;
  }

  let weightedSum = 0;
  let weightTotal = 0;
  const maxIndex = values.length - 1;

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (value === undefined) {
      continue;
    }
    const weight = 0.8 + (0.2 * index) / maxIndex;
    weightedSum += value * weight;
    weightTotal += weight;
  }

  return weightTotal > 0 ? weightedSum / weightTotal : null;
}

function emptyForecastSeries(): ForecastSeries {
  return {
    bridgeSeries: [],
    futureSeries: [],
    nowPoint: null,
  };
}

function buildLinearForecastSeries(
  {
    lastActualPoint,
    nowTimestamp,
    slopePerMs,
    targetValue,
  }: {
    lastActualPoint: ForecastChartPoint;
    nowTimestamp: number;
    slopePerMs: number | null;
    targetValue: number;
  },
): ForecastSeries {
  if (slopePerMs === null || !Number.isFinite(slopePerMs) || slopePerMs === 0) {
    return emptyForecastSeries();
  }

  const bridgeSeries: Array<[number, number]> = [];
  const futureSeries: Array<[number, number]> = [];
  const nowPoint =
    nowTimestamp > lastActualPoint.timestamp
      ? ([
          nowTimestamp,
          lastActualPoint.value + slopePerMs * (nowTimestamp - lastActualPoint.timestamp),
        ] satisfies [number, number])
      : null;

  if (nowPoint !== null) {
    bridgeSeries.push([lastActualPoint.timestamp, lastActualPoint.value], nowPoint);
  }

  const targetOffset = targetValue - lastActualPoint.value;
  const projectedTargetTimestamp =
    targetOffset / slopePerMs > 0
      ? lastActualPoint.timestamp + targetOffset / slopePerMs
      : null;

  if (
    projectedTargetTimestamp !== null &&
    Number.isFinite(projectedTargetTimestamp) &&
    projectedTargetTimestamp > lastActualPoint.timestamp
  ) {
    const futureStart = nowPoint ?? [lastActualPoint.timestamp, lastActualPoint.value];
    if (projectedTargetTimestamp > futureStart[0]) {
      futureSeries.push(
        futureStart,
        [projectedTargetTimestamp, targetValue],
      );
    }
  }

  return {
    bridgeSeries,
    futureSeries,
    nowPoint,
  };
}

interface DailyForecastState {
  timestamp: number;
  value: number;
}

function buildWeightedDayOverDayDeltas(
  points: ForecastChartPoint[],
  { nowTimestamp }: { nowTimestamp: number },
): { overallDelta: number | null; weekdayDeltas: Array<number | null> } {
  const dailyPoints = buildDailyPoints(points, { nowTimestamp });
  const weekdayDiffs = Array.from({ length: 7 }, () => [] as number[]);
  const allDiffs: number[] = [];

  for (let index = 1; index < dailyPoints.length; index += 1) {
    const previousPoint = dailyPoints[index - 1];
    const currentPoint = dailyPoints[index];
    if (previousPoint === undefined || currentPoint === undefined) {
      continue;
    }
    if (currentPoint.dayIndex !== previousPoint.dayIndex + 1) {
      continue;
    }

    const delta = currentPoint.averageValue - previousPoint.averageValue;
    weekdayDiffs[previousPoint.dayOfWeek]?.push(delta);
    allDiffs.push(delta);
  }

  return {
    overallDelta: weightedAverage(allDiffs),
    weekdayDeltas: weekdayDiffs.map((deltas) => weightedAverage(deltas)),
  };
}

function advanceWeightedDayOverDay(
  {
    limitTimestamp,
    overallDelta,
    startState,
    targetValue,
    weekdayDeltas,
  }: {
    limitTimestamp: number;
    overallDelta: number | null;
    startState: DailyForecastState;
    targetValue: number | null;
    weekdayDeltas: Array<number | null>;
  },
): { points: Array<[number, number]>; reachedTarget: [number, number] | null } {
  const points: Array<[number, number]> = [[startState.timestamp, startState.value]];
  let cursorTimestamp = startState.timestamp;
  let cursorValue = startState.value;

  for (let iteration = 0; iteration < MAX_FORECAST_DAYS && cursorTimestamp < limitTimestamp; iteration += 1) {
    const currentDate = new Date(cursorTimestamp);
    const dayOfWeek = currentDate.getDay();
    const fullDayDelta = weekdayDeltas[dayOfWeek] ?? overallDelta;
    if (fullDayDelta === null || !Number.isFinite(fullDayDelta)) {
      break;
    }

    const currentDayStart = getLocalDayStartTimestamp(cursorTimestamp);
    const nextDayStart = getNextLocalDayStartTimestamp(cursorTimestamp);
    const segmentEndTimestamp = Math.min(nextDayStart, limitTimestamp);
    const fullDayDuration = nextDayStart - currentDayStart;
    const segmentDuration = segmentEndTimestamp - cursorTimestamp;

    if (fullDayDuration <= 0 || segmentDuration <= 0) {
      break;
    }

    const segmentDelta = fullDayDelta * (segmentDuration / fullDayDuration);
    const nextValue = cursorValue + segmentDelta;

    if (
      targetValue !== null &&
      segmentDelta !== 0 &&
      ((segmentDelta > 0 && targetValue >= cursorValue && targetValue <= nextValue) ||
        (segmentDelta < 0 && targetValue <= cursorValue && targetValue >= nextValue))
    ) {
      const fraction = (targetValue - cursorValue) / segmentDelta;
      const targetTimestamp = cursorTimestamp + segmentDuration * fraction;
      const targetPoint: [number, number] = [targetTimestamp, targetValue];
      points.push(targetPoint);
      return {
        points,
        reachedTarget: targetPoint,
      };
    }

    points.push([segmentEndTimestamp, nextValue]);
    cursorTimestamp = segmentEndTimestamp;
    cursorValue = nextValue;
  }

  return {
    points,
    reachedTarget: null,
  };
}

function buildWeightedDayOverDaySeries(
  {
    actualPoints,
    lastActualPoint,
    nowTimestamp,
    targetValue,
  }: {
    actualPoints: ForecastChartPoint[];
    lastActualPoint: ForecastChartPoint;
    nowTimestamp: number;
    targetValue: number;
  },
): ForecastSeries {
  const { overallDelta, weekdayDeltas } = buildWeightedDayOverDayDeltas(actualPoints, { nowTimestamp });
  if (overallDelta === null || !Number.isFinite(overallDelta)) {
    return emptyForecastSeries();
  }

  const bridgeProjection =
    nowTimestamp > lastActualPoint.timestamp
      ? advanceWeightedDayOverDay({
          limitTimestamp: nowTimestamp,
          overallDelta,
          startState: {
            timestamp: lastActualPoint.timestamp,
            value: lastActualPoint.value,
          },
          targetValue: null,
          weekdayDeltas,
        })
      : { points: [[lastActualPoint.timestamp, lastActualPoint.value]] as Array<[number, number]>, reachedTarget: null };

  const bridgeSeries =
    bridgeProjection.points.length > 1
      ? bridgeProjection.points
      : [];
  const nowPoint =
    nowTimestamp > lastActualPoint.timestamp
      ? (bridgeProjection.points.at(-1) ?? null)
      : null;

  const futureStart =
    nowPoint === null
      ? {
          timestamp: lastActualPoint.timestamp,
          value: lastActualPoint.value,
        }
      : {
          timestamp: nowPoint[0],
          value: nowPoint[1],
        };

  const futureProjection = advanceWeightedDayOverDay({
    limitTimestamp: futureStart.timestamp + MAX_FORECAST_DAYS * DAY_MS,
    overallDelta,
    startState: futureStart,
    targetValue,
    weekdayDeltas,
  });

  return {
    bridgeSeries,
    futureSeries: futureProjection.reachedTarget === null ? [] : futureProjection.points,
    nowPoint,
  };
}

function buildSimpleSeries(
  actualPoints: ForecastChartPoint[],
  nowTimestamp: number,
  targetValue: number,
): ForecastSeries {
  const firstActualPoint = actualPoints[0];
  const lastActualPoint = actualPoints.at(-1) ?? null;
  if (
    firstActualPoint === undefined ||
    lastActualPoint === null ||
    lastActualPoint.timestamp <= firstActualPoint.timestamp
  ) {
    return emptyForecastSeries();
  }

  return buildLinearForecastSeries({
    lastActualPoint,
    nowTimestamp,
    slopePerMs:
      (lastActualPoint.value - firstActualPoint.value) /
      (lastActualPoint.timestamp - firstActualPoint.timestamp),
    targetValue,
  });
}

function buildWeightedWeekOverWeekSeries(
  actualPoints: ForecastChartPoint[],
  nowTimestamp: number,
  targetValue: number,
): ForecastSeries {
  const lastActualPoint = actualPoints.at(-1) ?? null;
  if (lastActualPoint === null) {
    return emptyForecastSeries();
  }

  const dailyPoints = buildDailyPoints(actualPoints, { nowTimestamp });
  if (dailyPoints.length < 2) {
    return emptyForecastSeries();
  }

  const firstDayIndex = dailyPoints[0]?.dayIndex;
  if (firstDayIndex === undefined) {
    return emptyForecastSeries();
  }

  const weeklyBuckets = new Map<number, { count: number; sum: number }>();
  for (const point of dailyPoints) {
    const weekIndex = Math.floor((point.dayIndex - firstDayIndex) / 7);
    const bucket = weeklyBuckets.get(weekIndex);
    if (bucket === undefined) {
      weeklyBuckets.set(weekIndex, { count: 1, sum: point.averageValue });
      continue;
    }
    bucket.count += 1;
    bucket.sum += point.averageValue;
  }

  const weeklyAverages = [...weeklyBuckets.entries()]
    .sort(([leftWeekIndex], [rightWeekIndex]) => leftWeekIndex - rightWeekIndex)
    .map(([weekIndex, bucket]) => ({
      averageValue: bucket.sum / bucket.count,
      weekIndex,
    }));

  const weeklyDiffs: number[] = [];
  for (let index = 1; index < weeklyAverages.length; index += 1) {
    const previousAverage = weeklyAverages[index - 1];
    const currentAverage = weeklyAverages[index];
    if (previousAverage === undefined || currentAverage === undefined) {
      continue;
    }
    if (currentAverage.weekIndex !== previousAverage.weekIndex + 1) {
      continue;
    }
    weeklyDiffs.push(currentAverage.averageValue - previousAverage.averageValue);
  }

  const weeklyDelta = weightedAverage(weeklyDiffs);
  const slopePerMs =
    weeklyDelta === null || !Number.isFinite(weeklyDelta) ? null : weeklyDelta / WEEK_MS;

  return buildLinearForecastSeries({
    lastActualPoint,
    nowTimestamp,
    slopePerMs,
    targetValue,
  });
}

export function buildGoalForecastSeries(
  {
    actualPoints,
    algorithm,
    nowTimestamp,
    targetValue,
  }: {
    actualPoints: ForecastChartPoint[];
    algorithm: ForecastAlgorithm;
    nowTimestamp: number;
    targetValue: number;
  },
): ForecastSeries {
  const lastActualPoint = actualPoints.at(-1) ?? null;
  if (lastActualPoint === null) {
    return emptyForecastSeries();
  }

  if (algorithm === "weighted_day_over_day") {
    const dayOverDaySeries = buildWeightedDayOverDaySeries({
      actualPoints,
      lastActualPoint,
      nowTimestamp,
      targetValue,
    });
    if (dayOverDaySeries.futureSeries.length > 0) {
      return dayOverDaySeries;
    }

    const weekOverWeekSeries = buildWeightedWeekOverWeekSeries(
      actualPoints,
      nowTimestamp,
      targetValue,
    );
    if (weekOverWeekSeries.futureSeries.length > 0) {
      return weekOverWeekSeries;
    }

    return buildSimpleSeries(actualPoints, nowTimestamp, targetValue);
  }

  if (algorithm === "weighted_week_over_week") {
    const weekOverWeekSeries = buildWeightedWeekOverWeekSeries(
      actualPoints,
      nowTimestamp,
      targetValue,
    );
    if (weekOverWeekSeries.futureSeries.length > 0) {
      return weekOverWeekSeries;
    }

    return buildSimpleSeries(actualPoints, nowTimestamp, targetValue);
  }

  return buildSimpleSeries(actualPoints, nowTimestamp, targetValue);
}
