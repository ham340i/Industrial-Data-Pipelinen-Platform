# AI contribution: 50% or more AI-generated
"""Parser, type checker, and Polars compiler for derived-column expressions."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import NoReturn

import polars as pl

from app.blocks.contracts import DataSchema
from app.blocks.tabular import DType, POLARS_TYPES

_MAX_LENGTH = 2048
_MAX_NODES = 256
_MAX_DEPTH = 32
_MIN_INT = -(2**63)
_MAX_INT = 2**63 - 1
_NUMERIC = {"integer", "number"}
_COLUMN_FUNCTION_ERROR = 'col() requires one string literal, e.g. col("amount").'
_ALLOWED_FUNCTIONS = {
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
_NULL_FUNCTIONS = {"is_null", "is_not_null"}
_STRING_UNARY_FUNCTIONS = {"lower", "upper", "trim", "length", "year", "month", "day"}
_STRING_MATCH_FUNCTIONS = {"contains", "starts_with", "ends_with"}


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
    invalid: pl.Expr | None = None


@dataclass(frozen=True)
class _TypedExpression:
    expression: pl.Expr
    dtype: DType | None
    nullable: bool
    invalid: pl.Expr | None = None


def _character_position(source: str, line: int, byte_column: int) -> int:
    """Convert an AST UTF-8 byte column to a 1-based source character offset."""
    lines = source.splitlines(keepends=True)
    preceding = sum(len(part) for part in lines[: line - 1])
    current = lines[line - 1] if line <= len(lines) else ""
    prefix = current.encode("utf-8")[:byte_column].decode("utf-8", errors="ignore")
    return preceding + len(prefix) + 1


def _syntax_position(source: str, line: int, character_column: int) -> int:
    """Convert SyntaxError's 1-based character column to a source offset."""
    lines = source.splitlines(keepends=True)
    preceding = sum(len(part) for part in lines[: line - 1])
    return preceding + max(character_column, 1)


def _combined_invalid(
    values: tuple[_TypedExpression, ...],
    additional: pl.Expr | None = None,
) -> pl.Expr | None:
    checks = [
        value.invalid.fill_null(False) for value in values if value.invalid is not None
    ]
    if additional is not None:
        checks.append(additional.fill_null(False))
    if not checks:
        return None

    combined = checks[0]
    for check in checks[1:]:
        combined = combined | check
    return combined


class _Compiler:
    def __init__(self, source: str, schema: DataSchema) -> None:
        self.source = source
        self.columns = {column.name: column for column in schema.columns}
        self.node_count = 0

    def fail(self, node: ast.AST, reason: str) -> NoReturn:
        line = getattr(node, "lineno", 1)
        byte_column = getattr(node, "col_offset", 0)
        if not isinstance(line, int) or not isinstance(byte_column, int):
            line, byte_column = 1, 0
        self.fail_at(
            _character_position(self.source, line, byte_column),
            reason,
        )

    @staticmethod
    def fail_at(position: int, reason: str) -> NoReturn:
        raise ExpressionError(position, reason)

    def compile(self, node: ast.AST, depth: int = 0) -> _TypedExpression:
        self.node_count += 1
        if self.node_count > _MAX_NODES:
            self.fail(node, "Expression is too complex.")
        if depth > _MAX_DEPTH:
            self.fail(node, "Expression is nested too deeply.")

        if isinstance(node, ast.Constant):
            return self._constant(node)
        if isinstance(node, ast.Name):
            return self._column(node)
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
            if not _MIN_INT <= value <= _MAX_INT:
                self.fail(node, "Integer literal is outside the supported range.")
            return _TypedExpression(pl.lit(value, dtype=pl.Int64), "integer", False)
        if type(value) is float:
            if not math.isfinite(value):
                self.fail(node, "Number literal must be finite.")
            return _TypedExpression(pl.lit(value, dtype=pl.Float64), "number", False)
        if type(value) is str:
            return _TypedExpression(pl.lit(value), "string", False)

        self.fail(
            node,
            "Only string, numeric, boolean, and null literals are allowed.",
        )

    def _column(self, node: ast.Name) -> _TypedExpression:
        column = self.columns.get(node.id)
        if column is None:
            self.fail(node, "Unknown column.")
        else:
            return _TypedExpression(
                pl.selectors.by_name(column.name).as_expr(),
                column.dtype,
                column.nullable,
            )

    def _unary(self, node: ast.UnaryOp, depth: int) -> _TypedExpression:
        if (
            isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and type(node.operand.value) is int
            and node.operand.value == 2**63
        ):
            return _TypedExpression(
                pl.lit(_MIN_INT, dtype=pl.Int64),
                "integer",
                False,
            )

        value = self.compile(node.operand, depth + 1)

        if isinstance(node.op, ast.Not):
            self._require(node, value, "boolean")
            return _TypedExpression(
                ~value.expression,
                "boolean",
                value.nullable,
                value.invalid,
            )

        if isinstance(node.op, ast.UAdd):
            if value.dtype not in _NUMERIC:
                self.fail(node, "Unary arithmetic requires a numeric value.")
            return value

        if isinstance(node.op, ast.USub):
            if value.dtype not in _NUMERIC:
                self.fail(node, "Unary arithmetic requires a numeric value.")
            if value.dtype == "integer":
                wide = -value.expression.cast(pl.Int128)
                return self._checked_integer(wide, (value,), value.nullable)
            return _TypedExpression(
                -value.expression,
                value.dtype,
                value.nullable,
                value.invalid,
            )

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
                _combined_invalid((left, right)),
            )

        left, right, dtype = self._numeric_pair(node, left, right)
        nullable = left.nullable or right.nullable

        if isinstance(node.op, ast.Div):
            expression = left.expression.cast(pl.Float64) / right.expression.cast(
                pl.Float64
            )
            return _TypedExpression(
                expression,
                "number",
                nullable,
                _combined_invalid((left, right)),
            )

        if dtype == "integer":
            left_wide = left.expression.cast(pl.Int128)
            right_wide = right.expression.cast(pl.Int128)
            if isinstance(node.op, ast.Add):
                wide = left_wide + right_wide
            elif isinstance(node.op, ast.Sub):
                wide = left_wide - right_wide
            elif isinstance(node.op, ast.Mult):
                wide = left_wide * right_wide
            else:
                wide = left_wide % right_wide
            return self._checked_integer(wide, (left, right), nullable)

        if isinstance(node.op, ast.Add):
            expression = left.expression + right.expression
        elif isinstance(node.op, ast.Sub):
            expression = left.expression - right.expression
        elif isinstance(node.op, ast.Mult):
            expression = left.expression * right.expression
        else:
            expression = left.expression % right.expression

        return _TypedExpression(
            expression,
            dtype,
            nullable,
            _combined_invalid((left, right)),
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

        if left.dtype != dtype:
            left = self._cast_numeric(left, dtype)
        if right.dtype != dtype:
            right = self._cast_numeric(right, dtype)

        return left, right, dtype

    @staticmethod
    def _cast_numeric(value: _TypedExpression, dtype: DType) -> _TypedExpression:
        return _TypedExpression(
            value.expression.cast(POLARS_TYPES[dtype]),
            dtype,
            value.nullable,
            value.invalid,
        )

    def _checked_integer(
        self,
        wide: pl.Expr,
        operands: tuple[_TypedExpression, ...],
        nullable: bool,
    ) -> _TypedExpression:
        overflow = (
            (wide < pl.lit(_MIN_INT, dtype=pl.Int128))
            | (wide > pl.lit(_MAX_INT, dtype=pl.Int128))
        ).fill_null(False)
        return _TypedExpression(
            wide.cast(pl.Int64),
            "integer",
            nullable,
            _combined_invalid(operands, overflow),
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
            _combined_invalid(tuple(values)),
        )

    def _compare(self, node: ast.Compare, depth: int) -> _TypedExpression:
        values = [self.compile(node.left, depth + 1)] + [
            self.compile(value, depth + 1) for value in node.comparators
        ]
        comparisons = []

        for index, operation in enumerate(node.ops):
            left, right = self._comparison_operands(
                node,
                operation,
                values[index],
                values[index + 1],
            )
            comparisons.append(
                self._compare_pair(operation, left.expression, right.expression)
            )

        if not comparisons:
            self.fail(node, "Comparison requires at least one operator.")

        expression = comparisons[0]
        for comparison in comparisons[1:]:
            expression = expression & comparison

        return _TypedExpression(
            expression,
            "boolean",
            any(value.nullable for value in values),
            _combined_invalid(tuple(values)),
        )

    def _comparison_operands(
        self,
        node: ast.Compare,
        operation: ast.cmpop,
        left: _TypedExpression,
        right: _TypedExpression,
    ) -> tuple[_TypedExpression, _TypedExpression]:
        if not isinstance(
            operation,
            (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE),
        ):
            self.fail(node, "Comparison operator is not allowed.")
        if left.dtype is None or right.dtype is None:
            self.fail(node, "Compare nulls with is_null() or is_not_null().")

        if left.dtype != right.dtype:
            if left.dtype in _NUMERIC and right.dtype in _NUMERIC:
                self.fail(
                    node,
                    "Mixed integer and number comparisons are unsupported.",
                )
            self.fail(node, "Comparison operands have incompatible types.")

        if not isinstance(operation, (ast.Eq, ast.NotEq)) and left.dtype == "boolean":
            self.fail(node, "Boolean values support equality comparisons only.")

        return left, right

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
            return self._column_call(node, arguments)
        if name not in _ALLOWED_FUNCTIONS:
            self.fail(node.func, "Unknown function.")

        if name == "replace":
            return self._replace_call(node, arguments, depth)

        compiled = [self.compile(argument, depth + 1) for argument in arguments]
        return self._call_function(node, name, compiled)

    def _column_call(
        self,
        node: ast.Call,
        arguments: list[ast.expr],
    ) -> _TypedExpression:
        if len(arguments) != 1:
            self.fail(node, _COLUMN_FUNCTION_ERROR)

        argument = arguments[0]
        if not isinstance(argument, ast.Constant):
            self.fail(node, _COLUMN_FUNCTION_ERROR)
        if not isinstance(argument.value, str):
            self.fail(node, _COLUMN_FUNCTION_ERROR)

        column = self.columns.get(argument.value)
        if column is None:
            self.fail(argument, "Unknown column.")
        else:
            return _TypedExpression(
                pl.selectors.by_name(column.name).as_expr(),
                column.dtype,
                column.nullable,
            )

    def _replace_call(
        self,
        node: ast.Call,
        arguments: list[ast.expr],
        depth: int,
    ) -> _TypedExpression:
        if len(arguments) != 3:
            self.fail(node, "replace() expects 3 argument(s).")

        pattern_node = arguments[1]
        if not isinstance(pattern_node, ast.Constant) or not isinstance(
            pattern_node.value, str
        ):
            self.fail(
                pattern_node,
                "replace() pattern must be a string literal.",
            )

        compiled = [self.compile(argument, depth + 1) for argument in arguments]
        return self._replace(node, compiled, pattern_node.value)

    def _call_function(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        if name in _NULL_FUNCTIONS:
            return self._null_function(node, name, arguments)
        if name == "coalesce":
            return self._coalesce(node, arguments)
        if name in _STRING_UNARY_FUNCTIONS:
            return self._string_unary(node, name, arguments)
        if name in _STRING_MATCH_FUNCTIONS:
            return self._string_match(node, name, arguments)
        if name == "concat":
            return self._concat(node, arguments)
        if name == "replace":
            self.fail(node, "replace() requires a literal pattern.")
        if name == "date_diff":
            return self._date_diff(node, arguments)
        return self._math_function(node, name, arguments)

    def _null_function(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        self._arity(node, name, arguments, 1)
        value = arguments[0]
        expression = (
            value.expression.is_null()
            if name == "is_null"
            else value.expression.is_not_null()
        )
        return _TypedExpression(expression, "boolean", False, value.invalid)

    def _coalesce(
        self,
        node: ast.Call,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        if len(arguments) < 2:
            self.fail(node, "coalesce() requires at least two arguments.")

        typed = [value.dtype for value in arguments if value.dtype is not None]
        if not typed:
            self.fail(node, "coalesce() requires a value with an inferable type.")

        coalesce_dtype = typed[0]
        for other in typed[1:]:
            if other != coalesce_dtype and not (
                other in _NUMERIC and coalesce_dtype in _NUMERIC
            ):
                self.fail(node, "coalesce() arguments have incompatible types.")
            if other == "number":
                coalesce_dtype = "number"

        expressions = []
        for value in arguments:
            if value.dtype is None or (
                value.dtype != coalesce_dtype and value.dtype in _NUMERIC
            ):
                expressions.append(value.expression.cast(POLARS_TYPES[coalesce_dtype]))
            else:
                expressions.append(value.expression)

        return _TypedExpression(
            pl.coalesce(expressions),
            coalesce_dtype,
            all(value.nullable for value in arguments),
            _combined_invalid(tuple(arguments)),
        )

    def _string_unary(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        self._arity(node, name, arguments, 1)
        value = arguments[0]
        self._require(node, value, "string")

        if name == "lower":
            expression = value.expression.str.to_lowercase()
            result_dtype: DType = "string"
        elif name == "upper":
            expression = value.expression.str.to_uppercase()
            result_dtype = "string"
        elif name == "trim":
            expression = value.expression.str.strip_chars()
            result_dtype = "string"
        elif name == "length":
            expression = value.expression.str.len_chars()
            result_dtype = "integer"
        else:
            parsed = value.expression.str.to_date(
                format="%Y-%m-%d",
                strict=True,
            )
            expression = getattr(parsed.dt, name)()
            result_dtype = "integer"

        return _TypedExpression(
            expression,
            result_dtype,
            value.nullable,
            value.invalid,
        )

    def _string_match(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
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
            _combined_invalid((text, fragment)),
        )

    def _concat(
        self,
        node: ast.Call,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
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
            _combined_invalid(tuple(arguments)),
        )

    def _replace(
        self,
        node: ast.Call,
        arguments: list[_TypedExpression],
        pattern: str,
    ) -> _TypedExpression:
        for value in arguments:
            self._require(node, value, "string")

        text, _, replacement = arguments
        return _TypedExpression(
            text.expression.str.replace_all(
                pattern,
                replacement.expression,
                literal=True,
            ),
            "string",
            any(value.nullable for value in arguments),
            _combined_invalid(tuple(arguments)),
        )

    def _date_diff(
        self,
        node: ast.Call,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        self._arity(node, "date_diff", arguments, 2)
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
            _combined_invalid(tuple(arguments)),
        )

    def _math_function(
        self,
        node: ast.Call,
        name: str,
        arguments: list[_TypedExpression],
    ) -> _TypedExpression:
        self._arity(node, name, arguments, 1)
        value = arguments[0]
        if value.dtype not in _NUMERIC:
            self.fail(node, f"{name}() requires a numeric argument.")

        if name == "abs" and value.dtype == "integer":
            return self._checked_integer(
                value.expression.cast(pl.Int128).abs(),
                (value,),
                value.nullable,
            )
        if name == "abs":
            return _TypedExpression(
                value.expression.abs(),
                value.dtype,
                value.nullable,
                value.invalid,
            )
        if name == "round":
            return _TypedExpression(
                value.expression.round(),
                value.dtype,
                value.nullable,
                value.invalid,
            )
        if name == "sqrt":
            expression = value.expression.sqrt()
            result_dtype: DType = "number"
        elif name == "log":
            expression = value.expression.log()
            result_dtype = "number"
        elif name == "floor":
            expression = value.expression.floor().cast(pl.Int64)
            result_dtype = "integer"
        elif name == "ceil":
            expression = value.expression.ceil().cast(pl.Int64)
            result_dtype = "integer"
        else:
            self.fail(node, "Unknown function.")

        return _TypedExpression(
            expression,
            result_dtype,
            value.nullable,
            value.invalid,
        )

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
    """Parse, type check, and compile an expression without evaluating data."""
    if len(source) > _MAX_LENGTH:
        raise ExpressionError(_MAX_LENGTH + 1, "Expression is too long.")

    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        line = exc.lineno or 1
        character_column = exc.offset or 1
        raise ExpressionError(
            _syntax_position(source, line, character_column),
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
        invalid=result.invalid,
    )
