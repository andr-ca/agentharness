# Comparison & Migration

You already have *something* — a `CLAUDE.md`, a plugin, a submodule of
markdown, an org template. This page answers two questions plainly:
should you switch to agentharness, and if so, what does the smallest
possible migration from your current setup actually look like.

## When to use agentharness

You have **more than one project** with a coding agent attached, and
their conventions have already started to drift — a different coverage
bar here, a branch-naming rule that contradicts another repo's, a
logging convention nobody remembers deciding. See README's ["Why not
just CLAUDE.md?"](../README.md#why-not-just-claudemd) for the concrete
before/after. If that sentence doesn't describe you yet, it probably
will the day project #2 starts.

## When *not* to use agentharness

Be honest with yourself here — adopting a harness you don't need is
pure overhead:

- **One repo, no plan for a second.** There's nothing to keep from
  drifting. Write a good `CLAUDE.md` by hand; you'll spend less time on
  it than integrating and maintaining a harness.
- **No coding agent in the loop.** This project is entirely about
  making agent behavior consistent and enforced. If nothing here reads
  `CLAUDE.md`/`AGENTS.md`, none of the enforcement mechanisms (hooks,
  completion gate, lock protocol) have anything to attach to.
- **Windows, outside WSL.** Untested — see README's "Supported
  platforms." The install scripts are Bash + POSIX shell + Python;
  nothing here has been verified on native Windows.
- **You need it to be *your* voice, not a shared one.** agentharness's
  whole premise is *one* source of truth referenced everywhere. If your
  team explicitly wants divergent, hand-tuned conventions per project —
  that's a legitimate choice, just the opposite of what this solves.

## agentharness vs. the alternatives

| Approach | What it is | Strong when | Weak when |
|---|---|---|---|
| **Single `CLAUDE.md`/`AGENTS.md` per project** | Hand-written, project-local, no shared source | One project, or a team that wants each repo's conventions independent by design | N projects — drift is guaranteed the moment two people (or two agents) write similar-but-not-identical rules in different repos |
| **Native agent plugin** (e.g. a Claude Code plugin, a Codex-native skill bundle) | Ecosystem-specific packaging, installed through that tool's own plugin mechanism | You only ever use one agent tool and want the most native possible install experience for it | Ties your conventions to one vendor's plugin format; nothing to reference from a second tool your team also uses. agentharness explicitly does *not* compete here (see README's Non-goals) — it generates per-client files instead of shipping as a plugin itself; see [ROADMAP.md](../ROADMAP.md)'s P2-06 for the open question of whether a native-plugin *distribution channel* for agentharness's own content is worth building later |
| **Dotfiles / a git submodule of markdown** | Your own hand-rolled version of "one source, N projects" | You already have this working and don't need enforcement, generated multi-client output, or a completion gate — just shared text | You're rebuilding agentharness's `--mode submodule` by hand, without the collision-safe installer, `doctor`/`audit`, the completion gate, or the multi-agent lock protocol — see "Advisory vs. enforced" in the [README](../README.md#product-contract) for what a plain submodule doesn't give you |
| **Organization template repository** | GitHub's own "generate from template" feature | New repos created inside one org, where copy-once-then-diverge is acceptable | Copy-once means drift starts the moment the template repo changes — a template has no `update` command. It also doesn't touch *agent* behavior specifically; it's a generic scaffold, not something an agent reads and follows |
| **agentharness** | One source, referenced (not copied) into every project; generated per-client; enforced by hooks and a completion gate | 2+ projects, at least one coding agent, conventions you want to *stay* in sync as they evolve | Single-project, single-tool, or a team that wants deliberately divergent per-repo rules |

## The smallest migration

Starting point: one existing project with its own hand-written
`CLAUDE.md` (or `AGENTS.md`), no harness installed.

### 1. Install

```bash
npx agentharness-toolkit init /path/to/your-project --mode npm --skills committing,branching
```

`--mode npm` (the default under `npx`) copies the package into a
durable `.agentharness-pkg/` inside your project rather than symlinking
into the ephemeral `npx` cache — see the [README](../README.md#quick-start)
for why `--mode link` isn't safe there. `--skills` is optional; omit it
to install every skill, or start narrow and widen later with `update
--skills`.

`init` does not run `agentharness bootstrap`. That is a separate,
optional first-run tailoring step (`bootstrap plan` is read-only) —
see [docs/INTEGRATION.md](INTEGRATION.md#first-run-bootstrap) if you
want it after the install lands.

### 2. What lands

This is the default `--client codex` path. A selected client that
owns one of the four always-on files generates that file whole-file
instead of splicing a block into it:

| Selected client | Owns (whole-file, not a block) |
|---|---|
| `codex` (default) | `AGENTS.md` |
| `gemini` | `GEMINI.md` |
| `copilot` | `.github/copilot-instructions.md` |

Qwen → `QWEN.md`, Cursor → `.cursor/rules/*.mdc`, and Kilo →
`.kilo/rules/agentharness.md` are extra whole-file surfaces; they do
not take over one of the four. Pass `--client none` to skip every
generated client surface (all four files then get a block).

- `.claude/skills/<name>/`, `.agents/skills/<name>/` (the
  Agent-Skills-standard path most non-Claude clients also read), and
  `.qwen/skills/<name>/` (Qwen Code's own discovery directory) for
  each selected skill. The three directories get the same `SKILL.md`;
  `.qwen/skills/` is populated even when `--client qwen` is not
  selected.
- A managed block spliced into whichever of the four always-on files
  the selected client does *not* own — on the default `--client
  codex` path that is `CLAUDE.md`, `GEMINI.md`, and
  `.github/copilot-instructions.md` (created fresh if you don't have
  them). Your file's other content is left alone; see
  [docs/DEMO.md](DEMO.md) for exactly what that block looks like.
  `GEMINI.md` / `.github/copilot-instructions.md` stay block-spliced
  only while `--client gemini` / `--client copilot` are not selected;
  pick either and that file is generated whole-file instead, so an
  existing file hits a collision prompt (keep/overwrite/backup), not
  a silent splice. The same collision applies to `AGENTS.md` on this
  default path — pass `--client none` if you'd rather have every one
  of the four treated as a block splice.
- `.agentharness-state.json`, recording mode, source revision, and
  installed skills/clients — `status`/`doctor`/`update`/`uninstall` all
  read this to know what they're managing.
- `.agentharness-bin/check` — a small consumer-local wrapper that
  runs `enforce-profile` against *this* project. Generated for
  `link`/`submodule`/`npm` (not `copy`). `doctor` soft-warns if it's
  missing; `update` regenerates it.
- A merge of `.github/.gitignore.template` into your `.gitignore`
  (additive only — nothing pre-existing is overwritten).

No telemetry, no background process, no network call beyond the one
`npm install` you already agreed to by running `npx`.

### 3. What to delete from your old `CLAUDE.md`

Any section that restates a convention agentharness already tracks
centrally — a coverage percentage, a branch-naming scheme, a logging
format, a commit-message convention. Replace it with a one-line pointer
into the harness, the same swap the README's own before/after example
shows:

```markdown
## Testing
See agentharness's `patterns/testing/COVERAGE_REQUIREMENTS.md` for the
coverage bar by rigor tier. This project is Production tier.
```

### 4. What to keep

Everything that's genuinely specific to this project and isn't a
cross-project convention: service names, deploy targets, domain
vocabulary, architectural decisions unique to this codebase, "don't
touch the legacy billing module" — anything a second project wouldn't
also need to say. agentharness's managed block lives *alongside* this,
not instead of it.

### 5. Keeping it current

```bash
npx agentharness-toolkit@latest update /path/to/your-project
```

(or `harness-link.sh update ...` if you installed via `git clone`
instead of `npx`) re-syncs the managed block and installed
skills/clients to whatever revision you're pinned to — see
[docs/RELEASING.md](RELEASING.md#pin-upgrade-rollback) for exactly when
each install mode picks up a change. `doctor` verifies the install is
healthy; `audit --json` gives a machine-readable status snapshot.

### 6. Backing out

```bash
npx agentharness-toolkit uninstall /path/to/your-project
```

(same `harness-link.sh uninstall ...` alternative as above) reverses
what `init` recorded: the managed block (restoring your original
content if the file predates the install), harness-created files,
`.agentharness-bin/check`, the durable `.agentharness-pkg/` copy in
npm mode, and `.agentharness-state.json`. See
[docs/INTEGRATION.md](INTEGRATION.md) for the full reversal list, or
[docs/DEMO.md](DEMO.md) to watch this in a scripted walkthrough first.

## Evidence this isn't just a pitch

One dated dogfood row exists for a real, non-fixture project:
[`docs/operational/reviews/dogfood-recalium-2026-08-20-status.md`](operational/reviews/dogfood-recalium-2026-08-20-status.md).
Every friction point it surfaced was filed as a GitHub issue and fixed
upstream — see that doc for the full list and what's still open.
