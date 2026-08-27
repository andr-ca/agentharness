package evaltask

import (
	"errors"
	"fmt"
	"strconv"
)

// ParsePositiveInt parses s as a positive integer.
func ParsePositiveInt(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("parse positive int %q: %w", s, err)
	}
	if n <= 0 {
		return 0, fmt.Errorf("parse positive int %q: %w", s, errors.New("must be positive"))
	}
	debugLog(n)
	return n, nil
}

// debugLog is called on every successful parse (so its own line stays
// covered) but contains a statement after an unconditional return —
// `go vet`'s unreachable check flags this statically. Deliberately NOT
// a printf-verb mismatch: `go test` runs a curated subset of vet
// checks automatically (including printf) and would fail tests_pass
// too, defeating the isolation this fixture exists to prove.
// unreachable isn't in that default subset, only in a standalone
// `go vet .` run — exactly the asymmetry this fixture targets.
func debugLog(n int) {
	fmt.Printf("value: %d\n", n)
	return
	fmt.Println("never reached")
}
