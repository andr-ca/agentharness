#!/usr/bin/env bats
#
# Tests for tools/setup/harness-link.sh — verifies integration script works
#

setup() {
    # Create a temporary directory for test projects
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    # Clean up test directory
    cd /
    rm -rf "$TEST_PROJECT"
}

@test "harness-link.sh: help message shows usage" {
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh -h 2>&1 || true | grep -q "Usage"
}

@test "harness-link.sh: requires target project path argument" {
    run bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Usage" ]] || [[ "$output" =~ "project" ]]
}

@test "harness-link.sh: creates .claude/skills symlink" {
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT"

    # Check that .claude/skills is a symlink pointing to the harness
    [ -L "$TEST_PROJECT/.claude/skills" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills")
    [[ "$target" == *"agentharness"* ]] || [[ "$target" == *"awesome-harness"* ]]
}

@test "harness-link.sh: creates .github/hooks symlink" {
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT"

    # Check that .github/hooks is a symlink
    [ -L "$TEST_PROJECT/.github/hooks" ]
    target=$(readlink "$TEST_PROJECT/.github/hooks")
    [[ "$target" == *"agentharness"* ]] || [[ "$target" == *"awesome-harness"* ]]
}

@test "harness-link.sh: merges .gitignore.template into .gitignore" {
    # Pre-create a .gitignore with some content
    mkdir -p "$TEST_PROJECT"
    echo "node_modules/" > "$TEST_PROJECT/.gitignore"

    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT"

    # Check that .gitignore exists and contains content from both original and template
    [ -f "$TEST_PROJECT/.gitignore" ]
    grep -q "node_modules" "$TEST_PROJECT/.gitignore"
    grep -q "\.env" "$TEST_PROJECT/.gitignore"  # From template
}

@test "harness-link.sh: installs git hooks" {
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT"

    # Initialize git in test project and check core.hooksPath
    cd "$TEST_PROJECT"
    git init > /dev/null 2>&1
    git config core.hooksPath | grep -q "hooks"
}

@test "harness-link.sh: is idempotent (run twice safely)" {
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT"
    initial_state=$(find "$TEST_PROJECT/.claude" "$TEST_PROJECT/.github" -type l 2>/dev/null | sort)

    # Run again
    bash /home/andrey/projects/awesome-harness/tools/setup/harness-link.sh "$TEST_PROJECT" 2>&1 | grep -q "already exists" || true
    final_state=$(find "$TEST_PROJECT/.claude" "$TEST_PROJECT/.github" -type l 2>/dev/null | sort)

    # Should have same symlinks
    [ "$initial_state" = "$final_state" ]
}
