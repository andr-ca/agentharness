# Sample Quality Plugin

A minimal demonstration plugin for the agentharness bootstrap policy system.

## Purpose

This plugin shows every required public interface for a bootstrap plugin:

- `metadata` — a `PluginMetadata` instance with a stable `plugin_id`, `version`,
  and declared `capabilities`
- `check(context)` — returns a `CheckResult` with typed `Finding` objects

This is **not** production language support. It exists to help plugin authors
understand the contract before building their own plugins.

## Running the contract tests

```bash
cd examples/plugins/sample-quality
python3 -m pytest test_contract.py -v
```

## Trust and version pinning

Before a third-party plugin can run in a production project, an operator must:

1. Run `agentharness plugins trust sample.quality 1.0.0` to generate a profile plan.
2. Commit that plan to `.agentharness-policy/trust.yaml`.
3. Merge the commit through the normal PR process.

The sample plugin is pre-trusted by the test harness for demonstration purposes only.
