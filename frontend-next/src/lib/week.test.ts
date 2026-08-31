import { describe, expect, it } from "vitest";

import {
  addDays,
  businessDaysOfWeek,
  calendarDaysOfWeek,
  isBusinessDay,
  mondayOfCalendarWeek,
  mondayOfWeek,
  shortDateLabel,
  todayInTimeZone,
  weekdayLabel,
} from "./week";

describe("addDays", () => {
  it("crosses month and year boundaries", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("survives a DST change in the local timezone", () => {
    // Brazil no longer observes DST, but the host machine may. Day arithmetic
    // must not shift regardless of where the app runs.
    expect(addDays("2026-11-01", 1)).toBe("2026-11-02");
    expect(addDays("2026-03-08", 1)).toBe("2026-03-09");
  });
});

describe("calendar week", () => {
  it("treats Sunday as the last day of the current calendar week", () => {
    expect(mondayOfCalendarWeek("2026-08-09")).toBe("2026-08-03");
  });

  it("returns Monday through Sunday for menu publishing", () => {
    expect(calendarDaysOfWeek("2026-08-06")).toEqual([
      "2026-08-03",
      "2026-08-04",
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
      "2026-08-08",
      "2026-08-09",
    ]);
  });
});

describe("mondayOfWeek", () => {
  it("returns the same Monday for every day of that week", () => {
    // 2026-08-03 is a Monday.
    for (const date of [
      "2026-08-03",
      "2026-08-04",
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
      "2026-08-08", // Saturday
    ]) {
      expect(mondayOfWeek(date)).toBe("2026-08-03");
    }
  });

  it("treats Sunday as the start of the next week", () => {
    // 2026-08-09 is a Sunday; its business week starts the next day.
    expect(mondayOfWeek("2026-08-09")).toBe("2026-08-10");
  });
});

describe("businessDaysOfWeek", () => {
  it("returns Monday to Friday", () => {
    expect(businessDaysOfWeek("2026-08-06")).toEqual([
      "2026-08-03",
      "2026-08-04",
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
    ]);
  });

  it("never includes a weekend day", () => {
    for (const date of businessDaysOfWeek("2026-08-09")) {
      expect(isBusinessDay(date)).toBe(true);
    }
  });
});

describe("isBusinessDay", () => {
  it("rejects Saturday and Sunday", () => {
    expect(isBusinessDay("2026-08-08")).toBe(false);
    expect(isBusinessDay("2026-08-09")).toBe(false);
    expect(isBusinessDay("2026-08-07")).toBe(true);
  });
});

describe("todayInTimeZone", () => {
  it("uses the app timezone, not the host timezone", () => {
    // 2026-08-06T02:00:00Z is still 2026-08-05 in São Paulo (UTC-3).
    const instant = new Date("2026-08-06T02:00:00Z");
    expect(todayInTimeZone("America/Sao_Paulo", instant)).toBe("2026-08-05");
    expect(todayInTimeZone("UTC", instant)).toBe("2026-08-06");
  });
});

describe("labels", () => {
  it("names weekdays in pt-BR", () => {
    expect(weekdayLabel("2026-08-03")).toBe("Segunda-feira");
    expect(weekdayLabel("2026-08-07")).toBe("Sexta-feira");
  });

  it("formats the short date as DD/MM", () => {
    expect(shortDateLabel("2026-08-03")).toBe("03/08");
  });
});
