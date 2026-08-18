#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const path = require('node:path');

const HARNESS_ROOT = path.resolve(__dirname, '..');
const SCRIPT = path.join(HARNESS_ROOT, 'tools', 'setup', 'harness-link.sh');

function isAvailable(cmd) {
  const result = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
  return result.error === undefined;
}

if (!isAvailable('bash')) {
  console.error(
    'agentharness requires bash, which was not found on PATH.\n' +
      'This CLI wraps a Bash script and only supports Linux/macOS ' +
      '(or WSL/Git Bash for Windows).'
  );
  process.exit(1);
}

if (!isAvailable('python3')) {
  console.error(
    'agentharness requires python3, which was not found on PATH.\n' +
      'tools/setup/harness-link.sh uses it to read/write ' +
      '.agentharness-state.json.'
  );
  process.exit(1);
}

// P0-02: this shim always runs from wherever npm/npx placed the package for
// this invocation — an npx cache entry or a temp extraction, not a durable,
// user-owned location. Defaulting 'init'/'plan' (and the legacy no-subcommand
// form) to --mode npm means the CLI copies itself into a durable directory
// inside the consumer project before linking skills, instead of symlinking
// straight into a path that can vanish the next time npx cleans its cache.
// harness-link.sh's own argument parser accepts flags in any position, so
// appending is as correct as inserting anywhere else.
// Every subcommand harness-link.sh itself lists in its own --help (see
// its own KNOWN_SUBCOMMANDS-equivalent dispatch), except 'init'/'plan'
// which are handled as special cases below. 'audit-prs' and
// 'generate-clients' were missing here (found dogfooding issue #240):
// neither accepts --mode at all, so any real invocation of
// 'generate-clients --client ...' through this shim got a bogus --mode
// npm appended and died with "Unexpected argument: --mode" -- masked in
// every manual check because '--help' is exempted above, so the two
// forms anyone actually tries first (bare --help, or copying a doc
// example that happens to end in --help) never hit it.
const KNOWN_SUBCOMMANDS = new Set([
  'init', 'plan', 'status', 'doctor', 'audit', 'audit-prs', 'enforce-profile',
  'generate-clients', 'update', 'uninstall',
]);

function shouldDefaultToNpmMode(args) {
  if (args.includes('--mode') || args.includes('-h') || args.includes('--help')) {
    return false;
  }
  const first = args[0];
  if (first === undefined) return false;
  // 'init'/'plan' explicitly, or the legacy invocation where the first
  // argument is a target directory rather than a known subcommand name.
  return first === 'init' || first === 'plan' || !KNOWN_SUBCOMMANDS.has(first);
}

// Subcommands served by the Python core (dist/agentharness.pyz), not by
// harness-link.sh. Without this routing the launcher forwarded EVERY
// argument to the bash script, so `agentharness bootstrap plan` died with
// "Unexpected argument: plan" — the packaged CLI advertised a command it
// could not reach.
//
// Deliberately excludes 'status' and 'plan', which both already mean
// something in harness-link.sh. Re-pointing them at the Python core would
// silently change behaviour for existing installs; the names listed here
// are the ones with no bash-side meaning, so routing them is unambiguous.
const PYTHON_SUBCOMMANDS = new Set([
  'bootstrap', 'runtime', 'github', 'profile', 'authority',
]);

const forwardedArgs = process.argv.slice(2);

if (PYTHON_SUBCOMMANDS.has(forwardedArgs[0])) {
  const zipapp = path.join(HARNESS_ROOT, 'dist', 'agentharness.pyz');
  if (!require('node:fs').existsSync(zipapp)) {
    console.error(
      `agentharness: ${forwardedArgs[0]} requires the packaged Python core, ` +
        `which is missing from this install (${zipapp}).`
    );
    process.exit(1);
  }
  const pythonResult = spawnSync('python3', [zipapp, ...forwardedArgs], {
    stdio: 'inherit',
  });
  if (pythonResult.error) {
    console.error(`Failed to run ${zipapp}: ${pythonResult.error.message}`);
    process.exit(1);
  }
  process.exit(pythonResult.status === null ? 1 : pythonResult.status);
}

const finalArgs = shouldDefaultToNpmMode(forwardedArgs)
  ? [...forwardedArgs, '--mode', 'npm']
  : forwardedArgs;

const result = spawnSync('bash', [SCRIPT, ...finalArgs], {
  stdio: 'inherit',
});

if (result.error) {
  console.error(`Failed to run ${SCRIPT}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status === null ? 1 : result.status);
