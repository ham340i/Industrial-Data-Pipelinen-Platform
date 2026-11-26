# ADR-0006: Safe derived-column expressions

- Status: Proposed
- Issue: #138
- Date: 2026-11-25

## Context

Process specialists need to calculate a new column from existing table values.
Expressions must be checked before execution and must not execute Python code.
The table contract currently supports string, integer, number, and boolean
columns; it does not define a date type.

## Decision

Implement a small expression language parsed into a syntax tree and compiled
directly to Polars expressions. Never use `eval`, `exec`, or Python compilation
to evaluate user input.

Column references use `col("column name")`, allowing names that are not valid
Python identifiers. The initial grammar supports:

- String, finite numeric, boolean, and null literals.
- Parentheses and unary `+`, `-`, and `not`.
- Arithmetic `+`, `-`, `*`, `/`, and `%`.
- Comparisons `==`, `!=`, `<`, `<=`, `>`, and `>=`.
- Boolean `and` and `or`.
- Positional calls to an explicit whitelist of functions.

The initial function whitelist is:

- String: `concat`, `contains`, `ends_with`, `length`, `lower`, `replace`,
  `starts_with`, `trim`, `upper`.
- Math: `abs`, `ceil`, `floor`, `log`, `round`, `sqrt`.
- Null handling: `coalesce`, `is_null`, `is_not_null`.
- Dates: `date_diff`, `day`, `month`, `year`.

Date functions accept ISO `YYYY-MM-DD` strings and return integer results.
They do not add date or datetime types to the table contract. `date_diff(a, b)`
returns the number of days from `b` to `a`.

The compiler infers one of the existing SDK scalar types and nullability.
Arithmetic requires numeric operands, except string concatenation with `+`.
Mixed integer/number arithmetic produces a number. Comparisons require compatible
types; boolean values support equality comparisons only. Null comparisons use
`is_null()` or `is_not_null()`. Type and syntax errors include a 1-based
character position in the expression.

The compiler rejects unknown names and functions, attribute access, indexing,
keyword arguments, and every syntax-tree node outside the documented grammar.
Input length, syntax-tree node count, and nesting depth are bounded.

A derived-column transform appends one new column and rejects a name that
already exists. It validates the expression against the input schema before
execution. Runtime evaluation uses only the compiled Polars expression and
returns a structured error if evaluation fails.

## Alternatives considered

- **Python `eval` or `exec`:** rejected because expressions would execute
  arbitrary Python rather than a bounded calculation language.
- **String rewriting into Polars code:** rejected because substitutions are
  difficult to validate reliably and can introduce unintended syntax.
- **Adding date types to the table contract:** deferred because it changes the
  shared schema, serialization, and source/sink contracts beyond this issue.
- **A third-party expression parser:** deferred to avoid adding a dependency for
  the intentionally small initial grammar.

## Consequences

The language is deliberately smaller than Python and documents its operators,
functions, type rules, and date-string format. Adding a function or syntax form
requires updating the compiler, type-checking tests, and this decision record.
