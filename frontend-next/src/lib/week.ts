/**
 * Calendar helpers.
 *
 * Dates are handled as plain ISO strings (YYYY-MM-DD) so a menu for a given day
 * never shifts because of timezone conversion. The only place a real timezone
 * matters is "what day is it right now", which uses APP_TIME_ZONE.
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/** Midday UTC avoids DST edges when doing day arithmetic on a date-only value. */
function toUtcNoon(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day, 12));
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Today's calendar date in the given IANA timezone, as YYYY-MM-DD. */
export function todayInTimeZone(timeZone: string, now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function addDays(isoDate: string, days: number): string {
  return toIsoDate(new Date(toUtcNoon(isoDate).getTime() + days * MS_PER_DAY));
}

/** 0 = Sunday … 6 = Saturday */
export function weekdayOf(isoDate: string): number {
  return toUtcNoon(isoDate).getUTCDay();
}

export function isBusinessDay(isoDate: string): boolean {
  const weekday = weekdayOf(isoDate);
  return weekday >= 1 && weekday <= 5;
}

/** Monday of the week containing the given date. */
export function mondayOfWeek(isoDate: string): string {
  const weekday = weekdayOf(isoDate);
  // Sunday (0) belongs to the week that starts the next day.
  const offset = weekday === 0 ? 1 : 1 - weekday;
  return addDays(isoDate, offset);
}

/** Monday of the calendar week containing the date, including its weekend. */
export function mondayOfCalendarWeek(isoDate: string): string {
  const weekday = weekdayOf(isoDate);
  const isoWeekday = weekday === 0 ? 7 : weekday;
  return addDays(isoDate, 1 - isoWeekday);
}

/** The seven calendar days from Monday through Sunday. */
export function calendarDaysOfWeek(isoDate: string): string[] {
  const monday = mondayOfCalendarWeek(isoDate);
  return [0, 1, 2, 3, 4, 5, 6].map((offset) => addDays(monday, offset));
}

/** The five business days (Mon–Fri) of the week containing the given date. */
export function businessDaysOfWeek(isoDate: string): string[] {
  const monday = mondayOfWeek(isoDate);
  return [0, 1, 2, 3, 4].map((offset) => addDays(monday, offset));
}

const WEEKDAY_LABELS = [
  "Domingo",
  "Segunda-feira",
  "Terça-feira",
  "Quarta-feira",
  "Quinta-feira",
  "Sexta-feira",
  "Sábado",
];

export function weekdayLabel(isoDate: string): string {
  return WEEKDAY_LABELS[weekdayOf(isoDate)];
}

/** DD/MM — short form used next to the weekday name. */
export function shortDateLabel(isoDate: string): string {
  const [, month, day] = isoDate.split("-");
  return `${day}/${month}`;
}
