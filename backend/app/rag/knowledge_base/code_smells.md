# Common Code Smells and Design Issues

## Long method / large class
A function that does too many things is hard to test and reason about.
Split it by responsibility. A class with many unrelated fields and methods
usually signals a violation of the single-responsibility principle.

## Duplicate code
The same logic repeated in multiple places should be extracted into a
shared function — duplication means every future fix has to be applied in
several places, and they drift out of sync.

## Deep nesting
Several levels of nested `if`/`for` make control flow hard to follow.
Prefer guard clauses and early returns over deeply nested conditionals.

## Magic numbers and strings
Unexplained literal values (`if status == 3`) should be replaced with named
constants or enums so the intent is clear and the value is defined once.

## God object / tight coupling
A single class or module that knows about and controls too many other
parts of the system is fragile and hard to change safely. Favor small,
loosely coupled components with clear interfaces.

## Poor naming
Single-letter or ambiguous names (`data`, `tmp`, `x`) make code harder to
review. Names should describe intent.

## Missing error handling
Ignoring return values or exceptions, or catching and discarding errors
silently, hides bugs until they surface unpredictably in production.

## High cyclomatic complexity
Many independent branches through a function (nested conditionals, loops,
switch statements) make it hard to test every path and easy to introduce
regressions.
