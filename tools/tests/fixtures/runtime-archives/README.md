# Runtime bootstrap archive fixtures

The binary fixtures used by `runtime-bootstrap.bats` are generated
deterministically into the gitignored `.tool-cache/runtime-bootstrap-fixtures/`
directory:

```bash
python3 tools/tests/helpers/make-runtime-fixtures.py
```

The generator creates separate valid npm and runtime archives, a fixture
consumer lock, and hostile TAR variants for path, link, metadata, truncation,
collision, and resource-limit failures. Large-limit cases use smaller
test-only bounds selected through the bootstrapper's explicitly guarded test
mode; production lock limits remain exact and cannot be weakened.

Pinned real `python-build-standalone` archives are not copied or committed.
When the reviewed files are present in `.tool-cache/runtime-artifacts/`, the
contract tests inspect their hashes and TAR feature inventory in place.
