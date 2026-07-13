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
const KNOWN_SUBCOMMANDS = new Set([
  'init', 'plan', 'status', 'doctor', 'audit', 'enforce-profile', 'update', 'uninstall',
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

const forwardedArgs = process.argv.slice(2);
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
