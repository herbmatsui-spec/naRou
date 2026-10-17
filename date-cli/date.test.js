import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { formatIso } from './date.js';

const run = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const cli = join(here, 'date.js');

test('formats a date as UTC ISO 8601', () => {
  const iso = formatIso(new Date('2026-01-02T03:04:05.000Z'));
  assert.equal(iso, '2026-01-02T03:04:05.000Z');
});

test('formats only the date portion when requested', () => {
  const iso = formatIso(new Date('2026-01-02T03:04:05.000Z'), { dateOnly: true });
  assert.equal(iso, '2026-01-02');
});

test('defaults to the current time', async () => {
  const { stdout } = await run('node', [cli]);
  assert.match(stdout.trim(), /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
});

test('converts an argument to ISO', async () => {
  const { stdout } = await run('node', [cli, '2026-01-02T03:04:05.000Z']);
  assert.equal(stdout.trim(), '2026-01-02T03:04:05.000Z');
});

test('prints the date portion with --date-only', async () => {
  const { stdout } = await run('node', [cli, '-d', '2026-01-02T03:04:05.000Z']);
  assert.equal(stdout.trim(), '2026-01-02');
});

test('exits non-zero on an invalid date', async () => {
  await assert.rejects(run('node', [cli, 'not-a-date']));
});
