#!/usr/bin/env bats

setup_file() {
    ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    export ROOT
    python3 "$ROOT/tools/tests/helpers/make-runtime-fixtures.py"
    TLS="$ROOT/.tool-cache/runtime-bootstrap-fixtures/tls"
    mkdir -p "$TLS"
    openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
        -keyout "$TLS/key.pem" -out "$TLS/cert.pem" \
        -subj '/CN=127.0.0.1' -addext 'subjectAltName=IP:127.0.0.1' >/dev/null 2>&1
    python3 "$ROOT/tools/tests/helpers/make-runtime-fixtures.py" --serve \
        "$ROOT/.tool-cache/runtime-bootstrap-fixtures" "$TLS/port" \
        "$TLS/cert.pem" "$TLS/key.pem" &
    FIXTURE_SERVER_PID=$!
    export FIXTURE_SERVER_PID TLS
    for _ in {1..50}; do
        [ -s "$TLS/port" ] && break
        sleep 0.1
    done
    [ -s "$TLS/port" ]
}

teardown_file() {
    kill "$FIXTURE_SERVER_PID"
    wait "$FIXTURE_SERVER_PID" 2>/dev/null || true
}

setup() {
    FIXTURES="$ROOT/.tool-cache/runtime-bootstrap-fixtures"
    SCRIPT="$ROOT/templates/bootstrap/verify-runtime.mjs"
    CACHE="$BATS_TEST_TMPDIR/cache"
    export AGENTHARNESS_BOOTSTRAP_TEST_MODE=1
    export AGENTHARNESS_FIXTURE_LAUNCH_LOG="$BATS_TEST_TMPDIR/hostile-launch.log"
}

run_network_case() {
    run node "$SCRIPT" --lock "$FIXTURES/valid/runtime.lock.json" \
        --cache "$CACHE" --verify-only
}

run_case() {
    local name="$1"
    shift
    run node "$SCRIPT" --lock "$FIXTURES/$name/runtime.lock.json" \
        --cache "$CACHE" --npm-archive "$FIXTURES/$name/npm.tgz" \
        --runtime-archive "$FIXTURES/$name/runtime.tar.gz" "$@"
}

@test "valid fixture launches exactly once and verified cache reuse launches once more" {
    export AGENTHARNESS_FIXTURE_LAUNCH_LOG="$BATS_TEST_TMPDIR/launch.log"
    fixture_copy="$BATS_TEST_TMPDIR/valid-copy"
    cp -R "$FIXTURES/valid" "$fixture_copy"
    run node "$SCRIPT" --lock "$fixture_copy/runtime.lock.json" \
        --cache "$CACHE" --npm-archive "$fixture_copy/npm.tgz" \
        --runtime-archive "$fixture_copy/runtime.tar.gz" -- first
    [ "$status" -eq 0 ]
    [ "$(wc -l < "$AGENTHARNESS_FIXTURE_LAUNCH_LOG")" -eq 1 ]
    rm "$fixture_copy/npm.tgz" "$fixture_copy/runtime.tar.gz"
    run node "$SCRIPT" --lock "$fixture_copy/runtime.lock.json" \
        --cache "$CACHE" --npm-archive "$fixture_copy/npm.tgz" \
        --runtime-archive "$fixture_copy/runtime.tar.gz" -- second
    [ "$status" -eq 0 ]
    [ "$(wc -l < "$AGENTHARNESS_FIXTURE_LAUNCH_LOG")" -eq 2 ]
}

@test "wrong npm and runtime digests fail before promotion" {
    for name in wrong-npm-digest wrong-runtime-digest; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"digest"* ]]
    done
    [ ! -e "$CACHE/npm" ]
    [ -z "$(find "$CACHE/runtime" -mindepth 1 -maxdepth 1 -print 2>/dev/null)" ]
}

@test "unsafe absolute traversal drive UNC and invalid UTF-8 paths fail" {
    for name in absolute traversal drive unc invalid-utf8 nul-path; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"archive"* || "$output" == *"path"* || "$output" == *"TAR"* ]]
    done
}

@test "strict per-file PAX path and size metadata is accepted" {
    run_case valid-pax --verify-only
    [ "$status" -eq 0 ]
}

@test "escaping dangling cyclic and deep link graphs fail" {
    for name in escaping-link dangling-link cyclic-link deep-link hardlink-directory; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"link"* ]]
    done
}

@test "special and extension TAR types fail" {
    for name in fifo device unknown-type global-pax gnu-longname gnu-longlink pax-metadata; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"TAR"* || "$output" == *"metadata"* || "$output" == *"type"* ]]
    done
}

@test "duplicates collisions and cross-artifact layouts fail" {
    for name in duplicate collision unexpected-layout cross-artifact; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
    done
}

@test "resource bounds fail under guarded compact test limits" {
    export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_member_bytes":2048}'
    run_case member-limit --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"member-size limit"* ]]
    export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_expanded_bytes":4096}'
    run_case expanded-limit --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"expanded-size limit"* ]]
    export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_members":10}'
    run_case count-limit --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"member-count limit"* ]]
    export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_path_bytes":128}'
    run_case path-limit --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"path length limit"* ]]
}

@test "corrupt checksums numerics and truncation fail" {
    for name in invalid-checksum invalid-numeric invalid-pax truncated-header truncated-data trailing-data; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
    done
}

@test "package and all zipapp internal identity mismatches fail" {
    for name in package-identity-mismatch identity-mismatch schema-identity-mismatch plugin-identity-mismatch provider-identity-mismatch; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"identity"* ]]
    done
}

@test "duplicate JSON keys and schema mismatches fail before artifact parsing" {
    for name in duplicate-lock schema-mismatch; do
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"JSON"* || "$output" == *"schema_version"* ]]
    done
}

@test "compressed artifact limit is enforced on actual bytes" {
    export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_compressed_bytes":64}'
    run_case valid --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"compressed-size limit"* ]]
}

@test "test limits cannot raise or add production archive bounds" {
    for limits in '{"max_members":100001}' '{"unknown":1}'; do
        export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS="$limits"
        run_case valid --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"only tighten"* ]]
    done
}

@test "acquisition parses and promotes one authenticated descriptor snapshot" {
    export AGENTHARNESS_FIXTURE_LAUNCH_LOG="$BATS_TEST_TMPDIR/snapshot-launch.log"
    fixture_copy="$BATS_TEST_TMPDIR/snapshot-copy"
    cp -R "$FIXTURES/valid" "$fixture_copy"
    export AGENTHARNESS_BOOTSTRAP_TEST_SWAP_RUNTIME_AFTER_AUTH="$fixture_copy/malicious-runtime.tar.gz"
    run node "$SCRIPT" --lock "$fixture_copy/runtime.lock.json" \
        --cache "$CACHE" --npm-archive "$fixture_copy/npm.tgz" \
        --runtime-archive "$fixture_copy/runtime.tar.gz" -- expected
    [ "$status" -eq 0 ]
    [[ "$(cat "$AGENTHARNESS_FIXTURE_LAUNCH_LOG")" == *" expected" ]]
    [[ "$(cat "$AGENTHARNESS_FIXTURE_LAUNCH_LOG")" != *"MALICIOUS"* ]]
}

@test "runtime entrypoint terminal must be a regular executable file" {
    for name in entrypoint-directory entrypoint-non-executable; do
        rm -rf "$CACHE"
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [[ "$output" == *"entrypoint"* || "$output" == *"executable"* ]]
        [ -z "$(find "$CACHE" -mindepth 2 -print 2>/dev/null)" ]
    done
    [ ! -s "$AGENTHARNESS_FIXTURE_LAUNCH_LOG" ]
}

@test "canonical cache containment accepts a symlinked cache ancestor" {
    real_cache="$BATS_TEST_TMPDIR/real-cache"
    mkdir "$real_cache"
    ln -s "$real_cache" "$BATS_TEST_TMPDIR/cache-link"
    CACHE="$BATS_TEST_TMPDIR/cache-link"
    run_case valid --verify-only
    [ "$status" -eq 0 ]
}

@test "decoded untrusted keys cannot inject terminal controls" {
    run_case duplicate-control-lock --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"duplicate JSON key"* ]]
    [[ "$output" != *$'\033'* ]]
}

@test "verified cache substitution is rejected before a second launch" {
    export AGENTHARNESS_FIXTURE_LAUNCH_LOG="$BATS_TEST_TMPDIR/cache-launch.log"
    run_case valid -- first
    [ "$status" -eq 0 ]
    zipapp="$(find "$CACHE/npm" -type f -name agentharness.pyz)"
    printf 'changed' > "$zipapp"
    run_case valid -- second
    [ "$status" -ne 0 ]
    [[ "$output" == *"cache"* || "$output" == *"changed"* ]]
    [ "$(wc -l < "$AGENTHARNESS_FIXTURE_LAUNCH_LOG")" -eq 1 ]
}

@test "offline cache rejects unexpected injected files before launch" {
    run_case valid --verify-only
    [ "$status" -eq 0 ]
    runtime_root="$(find "$CACHE/runtime" -mindepth 1 -maxdepth 1 -type d)"
    printf 'injected' > "$runtime_root/python/lib/injected-startup.py"
    run_case valid --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"unexpected"* || "$output" == *"inventory"* ]]
    [ ! -s "$AGENTHARNESS_FIXTURE_LAUNCH_LOG" ]
}

@test "offline cache rejects archive symlink and non-regular substitutions" {
    run_case valid --verify-only
    [ "$status" -eq 0 ]
    runtime_root="$(find "$CACHE/runtime" -mindepth 1 -maxdepth 1 -type d)"
    cached_archive="$runtime_root/.artifact.tar.gz"
    rm "$cached_archive"
    ln -s "$FIXTURES/valid/runtime.tar.gz" "$cached_archive"
    run_case valid --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"cache"* || "$output" == *"regular file"* ]]
    rm "$cached_archive"
    mkdir "$cached_archive"
    run_case valid --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"cache"* || "$output" == *"regular file"* ]]
    [ ! -s "$AGENTHARNESS_FIXTURE_LAUNCH_LOG" ]
}

@test "every hostile archive leaves no outside cache or launch effects" {
    hostile_cases="$(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["hostile_archives"]))' "$FIXTURES/manifest.json")"
    for name in $hostile_cases; do
        rm -rf "$CACHE"
        rm -f "$FIXTURES/outside-sentinel" "$AGENTHARNESS_FIXTURE_LAUNCH_LOG"
        unset AGENTHARNESS_BOOTSTRAP_TEST_LIMITS
        case "$name" in
            member-limit) export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_member_bytes":2048}' ;;
            expanded-limit) export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_expanded_bytes":4096}' ;;
            count-limit) export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_members":10}' ;;
            path-limit) export AGENTHARNESS_BOOTSTRAP_TEST_LIMITS='{"max_path_bytes":128}' ;;
        esac
        run_case "$name" --verify-only
        [ "$status" -ne 0 ]
        [ ! -e "$FIXTURES/outside-sentinel" ]
        [ ! -s "$AGENTHARNESS_FIXTURE_LAUNCH_LOG" ]
        [ -z "$(find "$CACHE" -mindepth 2 -print 2>/dev/null)" ]
        [ -z "$(find "$BATS_TEST_TMPDIR" -name '.agentharness-download-*' -print)" ]
    done
}

@test "local artifact arguments are unavailable outside explicit test mode" {
    unset AGENTHARNESS_BOOTSTRAP_TEST_MODE
    run_case valid --verify-only
    [ "$status" -ne 0 ]
    [[ "$output" == *"test mode"* ]]
}

@test "HTTPS downloads and an approved relative redirect verify successfully" {
    port="$(cat "$TLS/port")"
    export NODE_EXTRA_CA_CERTS="$TLS/cert.pem"
    export AGENTHARNESS_BOOTSTRAP_TEST_NPM_URL="https://127.0.0.1:$port/redirect-npm"
    export AGENTHARNESS_BOOTSTRAP_TEST_RUNTIME_URL="https://127.0.0.1:$port/runtime"
    run_network_case
    [ "$status" -eq 0 ]
}

@test "non-HTTPS and unapproved redirects fail without promotion" {
    port="$(cat "$TLS/port")"
    export NODE_EXTRA_CA_CERTS="$TLS/cert.pem"
    export AGENTHARNESS_BOOTSTRAP_TEST_RUNTIME_URL="https://127.0.0.1:$port/runtime"
    for route in redirect-http redirect-unapproved; do
        export AGENTHARNESS_BOOTSTRAP_TEST_NPM_URL="https://127.0.0.1:$port/$route"
        run_network_case
        [ "$status" -ne 0 ]
        [[ "$output" == *"approved HTTPS"* ]]
    done
    [ ! -e "$CACHE/npm" ]
}

@test "redirect limit and partial response fail with temporary cleanup" {
    port="$(cat "$TLS/port")"
    export NODE_EXTRA_CA_CERTS="$TLS/cert.pem"
    export AGENTHARNESS_BOOTSTRAP_TEST_RUNTIME_URL="https://127.0.0.1:$port/runtime"
    for route in redirect-loop/0 partial; do
        export AGENTHARNESS_BOOTSTRAP_TEST_NPM_URL="https://127.0.0.1:$port/$route"
        run_network_case
        [ "$status" -ne 0 ]
    done
    [ -z "$(find "$BATS_TEST_TMPDIR" -name '.agentharness-download-*' -print)" ]
}
