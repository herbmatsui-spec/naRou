#!/usr/bin/env node
import { Command } from 'commander';
import { pathToFileURL } from 'node:url';

export function formatIso(date, { local = false, dateOnly = false } = {}) {
  if (local) {
    const offsetMin = -date.getTimezoneOffset();
    const shifted = new Date(date.getTime() + offsetMin * 60_000).toISOString();
    if (dateOnly) return shifted.slice(0, 10);
    const sign = offsetMin >= 0 ? '+' : '-';
    const abs = Math.abs(offsetMin);
    const hh = String(Math.floor(abs / 60)).padStart(2, '0');
    const mm = String(abs % 60).padStart(2, '0');
    return `${shifted.slice(0, -1)}${sign}${hh}:${mm}`;
  }

  const iso = date.toISOString();
  return dateOnly ? iso.slice(0, 10) : iso;
}

export function createProgram() {
  const program = new Command();

  program
    .name('datejs')
    .description('Print the ISO 8601 representation of a date')
    .version('1.0.0')
    .argument('[date]', 'date to convert (defaults to now)')
    .option('-l, --local', 'print local time with UTC offset instead of UTC')
    .option('-d, --date-only', 'print only the date portion (YYYY-MM-DD)')
    .action((input, options) => {
      const date = input === undefined ? new Date() : new Date(input);
      if (Number.isNaN(date.getTime())) {
        program.error(`invalid date '${input}'`);
      }
      console.log(formatIso(date, options));
    });

  return program;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  createProgram().parse();
}
