# AI contribution: 50% or more AI-generated
"""Parser, type checker, and Polars compiler for derived-column expressions."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import cast

import polars as pl

from app.blocks.contracts import DataSchema
from app.blocks.tabular import DType, POLARS_TYPES

_MAX_LENGTH = 2048
_MAX_NODES = 256
_MAX_DEPTH = 32
_NUMERIC = {"integer", "number"}


class ExpressionError(ValueError):
    """An expression error with a 1-based character position."""

    def __init__(self, position: int, reason: str) -> None:
        self.position = position
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class CompiledExpression:
    expression: pl.Expr
    dtype: DType
    nullable: bool


@dataclass(frozen=True)
class _TypedExpression:
    expression: pl.Expr
    dtype: DType | None
    nullable: bool


def _character_position(source: str, line: int, byte_column: int) -> int:
    """Convert an AST UTF-8 byte column to a 1-based source character offset."""
    lines = source.splitlines(keepends=True)
    preceding = sum(len(part) for part in lines[: line - 1])
    current = lines[line - 1] if line <= len(lines) else ""
    prefix = current.encode("utf-8")[:byte_column].decode("utf-8", errors="ignore")
    return preceding + len(prefix) + 1


class _Compiler:
    def __init__(self, source: str, schema: DataSchema) -> None:
        self.source = source
        self.columns = {column.name: column for column in schema.columns}
        self.node_count = 0

    def fail(self, node: ast.AST, reason: str) -> None:
        self.fail_at(
            _character_position(self.source, node.lineno, node.col_offset),
            reason,
        )

    @staticmethod
    def fail_at(position: int, reason: str) -> None:
        raise ExpressionError(position, reason)

    def compile(self, node: ast.AST, depth: int = 0) -> _TypedExpression:
        self.node_count += 1
        if self.node_count > _MAX_NODES:
            self.fail(node, "Expression is too complex.")
        if depth > _MAX_DEPTH:
            self.fail(node, "Expression is nested too deeply.")

        if isinstance(node, ast.Constant):
            return self._constant(node)
        if isinstance(node, ast.UnaryOp):
            return self._unary(node, depth)
        if isinstance(node, ast.BinOp):
            return self._binary(node, depth)
        if isinstance(node, ast.BoolOp):
            return self._boolean(node, depth)
        if isinstance(node, ast.Compare):
            return self._compare(node, depth)
        if isinstance(node, ast.Call):
            return self._call(node, depth)

        self.fail(node, "Expression construct is not allowed.")

    def _constant(self, node: ast.Constant) -> _TypedExpression:
        value = node.value

        if value is None:
            return _TypedExpression(pl.lit(None), None, True)
        if type(value) is bool:
            return _TypedExpression(pl.lit(value), "boolean", False)
        if type(value) is int:
            if not -(2**63) <= value < 2**63:
                self.fail(node, "Integer literal is outside the supported range.")
            return _TypedExpression(pl.lit(value, dtype=pl.Int64), "integer", False)
        if type(value) is float:
            if not math.isfinite(value):
                self.fail(node, "Number literal must be finite.")
            return _TypedExpression(pl.lit(value, dtype=pl.Float64), "number", False)
        if type(value) is str:
            return _TypedExpression(pl.lit(value), "string", False)

        self.fail(node, "Only string, numeric, boolean, and null literals are allowed.")

    def _unary(self, node: ast.UnaryOp, depth: int) -> _TypedExpression:
        value = self.compile(node.operand, depth + 1)

        if isinstance(node.op, ast.Not):
            self._require(node, value, "boolean")
            return _TypedExpression(~value.expression, "boolean", value.nullable)

        if isinstance(node.op, (ast.UAdd, ast.USub)):
            if value.dtype not in _NUMERIC:
                self.fail(node, "Unary arithmetic requires a numeric value.")
            expression = (
                -value.expression if isinstance(node.op, ast.USub) else value.expression
            )
            return _TypedExpression(expression, value.dtype, value.nullable)

        self.fail(node, "Unary operator is not allowed.")

    def _binary(self, node: ast.BinOp, depth: int) -> _TypedExpression:
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            self.fail(node, "Arithmetic operator is not allowed.")

        left = self.compile(node.left, depth + 1)
        right = self.compile(node.right, depth + 1)

        if isinstance(node.op, ast.Add) and left.dtype == right.dtype == "string":
            return _TypedExpression(
                left.expression + right.expression,
                "string",
                left.nullable or right.nullable,
            )

        left, right, dtype = self._numeric_pair(node, left, right)
        if isinstance(node.op, ast.Add):
            expression = left.expression + right.expression
        elif isinstance(node.op, ast.Sub):
            expression = left.expression - right.expression
        elif isinstance(node.op, ast.Mult):
            expression = left.expression * right.expression
        elif isinstance(node.op, ast.Div):
            expression = left.expression.cast(pl.Float64) / right.expression.cast(
                pl.Float64
            )
            dtype = "number"
        else:
            expression = left.expression % right.expression

        return _TypedExpression(
            expression,
            dtype,
            left.nullable or right.nullable,
        )

    def _numeric_pair(
        self,
        node: ast.AST,
        left: _TypedExpression,
        right: _TypedExpression,
    ) -> tuple[_TypedExpression, _TypedExpression, DType]:
        if left.dtype is None and right.dtype is None:
            self.fail(node, "A null-only expression has no inferable type.")
        if left.dtype not in _NUMERIC | {None} or right.dtype not in _NUMERIC | {None}:
            self.fail(node, "Arithmetic requires numeric values.")

        dtype: DType = "number" if "number" in (left.dtype, right.dtype) else "integer"

        if left.dtype is None:
            left = self._cast_null(left, dtype)
        elif left.dtype != dtype:
            left = self._cast_numeric(left, dtype)

        if right.dtype is None:
            right = self._cast_null(right, dtype)
        elif right.dtype != dtype:
            right = self._cast_numeric(right, dtype)

        return left, right, dtype

    @staticmethod
    def _cast_null(value: _TypedExpression, dtype: DType) -> _TypedExpression:
        return _TypedExpression(
            value.expression.cast(POLARS_TYPES[dtype]),
            dtype,
            value.nullable,
        )

    @staticmethod
    def _cast_numeric(value: _TypedExpression, dtype: DType) -> _TypedExpression:
        return _TypedExpression(
            value.expression.cast(POLARS_TYPES[dtype]),
            dtype,
            value.nullable,
        )

    def _boolean(self, node: ast.BoolOp, depth: int) -> _TypedExpression:
        values = [self.compile(value, depth + 1) for value in node.values]
        for value in values:
            self._require(node, value, "boolean")

        expression = values[0].expression
        for value in values[1:]:
            if isinstance(node.op, ast.And):
                expression = expression & value.expression
            elif isinstance(node.op, ast.Or):
                expression = expression | value.expression
            else:
                self.fail(node, "Boolean operator is not allowed.")

        return _TypedExpression(
            expression,
            "boolean",
            any(value.nullable for value in values),
        )

    def _compare(self, node: ast.Compare, depth: int) -> _TypedExpression:
        values = [self.compile(node.left, depth + 1)] + [
            self.compile(value, depth + 1) for value in node.comparators
        ]

        result: pl.Expr | None = None
        for index, operation in enumerate(node.ops):
            left = values[index]
            right = values[index + 1]

            if left.dtype is None or right.dtype is None:
                self.fail(node, "Compare nulls with is_null() or is_not_null().")

            numeric_pair = left.dtype in _NUMERIC and right.dtype in _NUMERIC
            same_type = left.dtype == right.dtype
            equality = isinstance(operation, (ast.Eq, ast.NotEq))

            if not (same_type or numeric_pair):
                self.fail(node, "Comparison operands have incompatible types.")
            if not equality and left.dtype == "boolean":
                self.fail(node, "Boolean values support equality comparisons only.")

            if numeric_pair and "number" in (left.dtype, right.dtype):
                if left.dtype != "number":
                    left = self._cast_numeric(left, "number")
                if right.dtype != "number":
                    right = self._cast_numeric(right, "number")

            comparison = self._compare_pair(
                operation, left.expression, right.expression
            )
            result = comparison if result is None else result & comparison

        assert result is not None
        return _TypedExpression(
            result,
            "boolean",
            any(value.nullable for value in values),
        )

    @staticmethod
    def _compare_pair(
        operation: ast.cmpop,
        left: pl.Expr,
        right: pl.Expr,
    ) -> pl.Expr:
        if isinstance(operation, ast.Eq):
            return left == right
        if isinstance(operation, ast.NotEq):
            return left != right
        if isinstance(operation, ast.Lt):
            return left < right
        if isinstance(operation, ast.LtE):
            return left <= right
        if isinstance(operation, ast.Gt):
            return left > right
        if isinstance(operation, ast.GtE):
            return left >= right
        raise AssertionError("Unsupported comparison reached compiler")

    def _call(self, node: ast.Call, depth: int) -> _TypedExpression:
        if not isinstance(node.func, ast.Name):
            self.fail(node, "Only whitelisted function calls are allowed.")
        if node.keywords:
            self.fail(node, "Function keyword arguments are not allowed.")

        name = node.func.id
        arguments = list(node.args)

        if name == "col":
            if (
                len(arguments) != 1
                or not isinstance(arguments[0], ast.Constant)
                or type(arguments[0].value) is not str
            ):
                self.fail(
                    node, 'col() requires one string literal, e.g. col("amount").'
                )
            column = self.columns.get(cast(str, arguments[0].value))
            if column is None:
                self.fail(arguments[0], "Unknown column.")
            return _TypedExpression(
                pl.col(column.name),
                column.dtype,
                column.nullable,
            )

        allowed = {
            "abs",
            "ceil",
            "coalesce",
            "concat",
            "contains",
            "date_diff",
            "day",
            "ends_with",
            "floor",
            "is_not_null",
            "is_null",
            "length",
            "log",
            "lower",
            "month",
            "replace",
            "round",
            "sqrt",
            "starts_with",
            "trim",
            "upper",
            "year",
        }
        if name not in allowed:
            self.fail(node.func, "Unknown function.")

        compiled = [self.compile(argument, depth + 1) for argument in arguments]
        return self._call_function(node, name, compiled)

    def _call_function(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        if name in {"is_null", "is_not_null"}:
            self._arity(node, name, arguments, 1)
            expression = (
                arguments[0].expression.is_null()
                if name == "is_null"
                else arguments[0].expression.is_not_null()
            )
            return _TypedExpression(expression, "boolean", False)

        if name == "coalesce":
            if len(arguments) < 2:
                self.fail(node, "coalesce() requires at least two arguments.")
            typed = [value.dtype for value in arguments if value.dtype is not None]
            if not typed:
                self.fail(node, "coalesce() requires a value with an inferable type.")
            dtype = cast(DType, typed[0])
            if any(
                other != dtype and not (other in _NUMERIC and dtype in _NUMERIC)
                for other in typed[1:]
            ):
                self.fail(node, "coalesce() arguments have incompatible types.")
            if "number" in typed:
                dtype = "number"

            expressions = []
            for value in arguments:
                if value.dtype is None:
                    expressions.append(value.expression.cast(POLARS_TYPES[dtype]))
                elif value.dtype != dtype and value.dtype in _NUMERIC:
                    expressions.append(value.expression.cast(POLARS_TYPES[dtype]))
                else:
                    expressions.append(value.expression)

            return _TypedExpression(
                pl.coalesce(expressions),
                dtype,
                all(value.nullable for value in arguments),
            )

        if name in {"lower", "upper", "trim", "length", "year", "month", "day"}:
            self._arity(node, name, arguments, 1)
            value = arguments[0]
            self._require(node, value, "string")

            if name == "lower":
                expression = value.expression.str.to_lowercase()
                dtype: DType = "string"
            elif name == "upper":
                expression = value.expression.str.to_uppercase()
                dtype = "string"
            elif name == "trim":
                expression = value.expression.str.strip_chars()
                dtype = "string"
            elif name == "length":
                expression = value.expression.str.len_chars()
                dtype = "integer"
            else:
                parsed = value.expression.str.to_date(
                    format="%Y-%m-%d",
                    strict=True,
                )
                expression = getattr(parsed.dt, name)()
                dtype = "integer"

            return _TypedExpression(expression, dtype, value.nullable)

        if name in {"contains", "starts_with", "ends_with"}:
            self._arity(node, name, arguments, 2)
            for value in arguments:
                self._require(node, value, "string")

            text, fragment = arguments
            if name == "contains":
                expression = text.expression.str.contains(
                    fragment.expression,
                    literal=True,
                )
            elif name == "starts_with":
                expression = text.expression.str.starts_with(fragment.expression)
            else:
                expression = text.expression.str.ends_with(fragment.expression)

            return _TypedExpression(
                expression,
                "boolean",
                text.nullable or fragment.nullable,
            )

        if name == "concat":
            if not arguments:
                self.fail(node, "concat() requires at least one argument.")
            for value in arguments:
                self._require(node, value, "string")
            return _TypedExpression(
                pl.concat_str(
                    [value.expression for value in arguments],
                    separator="",
                ),
                "string",
                any(value.nullable for value in arguments),
            )

        if name == "replace":
            self._arity(node, name, arguments, 3)
            for value in arguments:
                self._require(node, value, "string")
            text, old, new = arguments
            return _TypedExpression(
                text.expression.str.replace_all(
                    old.expression,
                    new.expression,
                    literal=True,
                ),
                "string",
                any(value.nullable for value in arguments),
            )

        if name == "date_diff":
            self._arity(node, name, arguments, 2)
            for value in arguments:
                self._require(node, value, "string")
            left = arguments[0].expression.str.to_date(
                format="%Y-%m-%d",
                strict=True,
            )
            right = arguments[1].expression.str.to_date(
                format="%Y-%m-%d",
                strict=True,
            )
            return _TypedExpression(
                (left - right).dt.total_days(),
                "integer",
                arguments[0].nullable or arguments[1].nullable,
            )

        self._arity(node, name, arguments, 1)
        value = arguments[0]
        if value.dtype not in _NUMERIC:
            self.fail(node, f"{name}() requires a numeric argument.")

        if name == "abs":
            return _TypedExpression(value.expression.abs(), value.dtype, value.nullable)
        if name == "round":
            return _TypedExpression(
                value.expression.round(), value.dtype, value.nullable
            )
        if name == "sqrt":
            expression = value.expression.sqrt()
            dtype = "number"
        elif name == "log":
            expression = value.expression.log()
            dtype = "number"
        elif name == "floor":
            expression = value.expression.floor().cast(pl.Int64)
            dtype = "integer"
        elif name == "ceil":
            expression = value.expression.ceil().cast(pl.Int64)
            dtype = "integer"
        else:
            self.fail(node, "Unknown function.")

        return _TypedExpression(expression, dtype, value.nullable)

    def _arity(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
        expected: int,
    ) -> None:
        if len(arguments) != expected:
            self.fail(node, f"{name}() expects {expected} argument(s).")

    def _require(
        self,
        node: ast.AST,
        value: _TypedExpression,
        dtype: DType,
    ) -> None:
        if value.dtype != dtype:
            self.fail(node, f"Function or operator requires {dtype} values.")


def compile_expression(source: str, schema: DataSchema) -> CompiledExpression:
    """Parse, type-check, and compile an expression without evaluating data."""
    if len(source) > _MAX_LENGTH:
        raise ExpressionError(_MAX_LENGTH + 1, "Expression is too long.")

    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        line = exc.lineno or 1
        byte_column = max((exc.offset or 1) - 1, 0)
        raise ExpressionError(
            _character_position(source, line, byte_column),
            "Invalid expression syntax.",
        ) from None
    except (ValueError, RecursionError):
        raise ExpressionError(1, "Invalid expression syntax.") from None

    compiler = _Compiler(source, schema)
    result = compiler.compile(tree.body)
    if result.dtype is None:
        raise ExpressionError(1, "Expression result type cannot be inferred.")

    return CompiledExpression(
        expression=result.expression,
        dtype=result.dtype,
        nullable=result.nullable,
    )
