"""AST allowlist compiler for manual and AI-authored strategy rules."""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeAlias, cast

from src.lxl_quantaxis.strategy.base import ParameterValue, StrategySpec

RuleValue: TypeAlias = ParameterValue | None
RuleFunction: TypeAlias = Callable[..., RuleValue]


class StrategyRuleError(ValueError):
    """Raised when a rule is unsafe or cannot be evaluated."""


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[object, object], object]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_COMPARE_OPERATORS: dict[type[ast.cmpop], Callable[[object, object], bool]] = {
    ast.Eq: cast(Callable[[object, object], bool], operator.eq),
    ast.NotEq: cast(Callable[[object, object], bool], operator.ne),
    ast.Gt: cast(Callable[[object, object], bool], operator.gt),
    ast.GtE: cast(Callable[[object, object], bool], operator.ge),
    ast.Lt: cast(Callable[[object, object], bool], operator.lt),
    ast.LtE: cast(Callable[[object, object], bool], operator.le),
}


@dataclass(frozen=True, slots=True)
class CompiledRule:
    source: str
    tree: ast.Expression
    allowed_names: frozenset[str]
    functions: Mapping[str, RuleFunction]

    def evaluate(self, context: Mapping[str, RuleValue]) -> bool:
        unexpected = set(context) - self.allowed_names
        if unexpected:
            raise StrategyRuleError(f"unexpected rule input(s): {', '.join(sorted(unexpected))}")
        missing = self.allowed_names - set(context) - set(self.functions)
        if missing:
            raise StrategyRuleError(f"missing rule input(s): {', '.join(sorted(missing))}")
        return bool(_evaluate(self.tree.body, context, self.functions))


@dataclass(frozen=True, slots=True)
class CompiledStrategy:
    spec: StrategySpec
    entry: CompiledRule | None
    exit: CompiledRule | None

    def should_enter(self, context: Mapping[str, RuleValue]) -> bool:
        return self.entry.evaluate(context) if self.entry is not None else False

    def should_exit(self, context: Mapping[str, RuleValue]) -> bool:
        return self.exit.evaluate(context) if self.exit is not None else False


class StrategyCompiler:
    """Compile expressions without eval, imports, attributes, or subscripts."""

    def __init__(self, functions: Mapping[str, RuleFunction] | None = None, *, max_nodes: int = 64) -> None:
        self._functions = dict(functions or {})
        self._max_nodes = max_nodes
        for name in self._functions:
            if not name.isidentifier() or name.startswith("_"):
                raise StrategyRuleError(f"unsafe function name: {name}")

    def compile(self, spec: StrategySpec) -> CompiledStrategy:
        parameter_names = {item.name for item in spec.parameters}
        names = frozenset((*spec.data_requirements, *parameter_names, *self._functions))
        return CompiledStrategy(
            spec=spec,
            entry=self._compile_rule(spec.entry_rule, names),
            exit=self._compile_rule(spec.exit_rule, names),
        )

    def _compile_rule(self, source: str, allowed_names: frozenset[str]) -> CompiledRule | None:
        if not source.strip():
            return None
        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise StrategyRuleError("strategy rule is not a valid expression") from exc
        nodes = tuple(ast.walk(tree))
        if len(nodes) > self._max_nodes:
            raise StrategyRuleError("strategy rule is too complex")
        for node in nodes:
            _validate_node(node, allowed_names, frozenset(self._functions))
        return CompiledRule(source, tree, allowed_names, self._functions)


def _validate_node(node: ast.AST, allowed_names: frozenset[str], function_names: frozenset[str]) -> None:
    allowed_nodes = (
        ast.Expression,
        ast.BoolOp,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Not,
        ast.USub,
        ast.UAdd,
        *tuple(_BINARY_OPERATORS),
        *tuple(_COMPARE_OPERATORS),
    )
    if not isinstance(node, allowed_nodes):
        raise StrategyRuleError(f"operator is not allowed: {type(node).__name__}")
    if isinstance(node, ast.Name) and (node.id not in allowed_names or node.id.startswith("_")):
        raise StrategyRuleError(f"unknown or unsafe name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in function_names:
            raise StrategyRuleError("only allowlisted functions may be called")
        if node.keywords:
            raise StrategyRuleError("keyword arguments are not allowed in strategy rules")
    if isinstance(node, ast.Constant) and not isinstance(node.value, (bool, int, float)):
        raise StrategyRuleError("only numeric and boolean constants are allowed")


def _evaluate(node: ast.AST, context: Mapping[str, RuleValue], functions: Mapping[str, RuleFunction]) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in functions:
            return functions[node.id]
        return context[node.id]
    if isinstance(node, ast.BoolOp):
        values = (_evaluate(item, context, functions) for item in node.values)
        return (
            all(bool(item) for item in values) if isinstance(node.op, ast.And) else any(bool(item) for item in values)
        )
    if isinstance(node, ast.UnaryOp):
        value = _evaluate(node.operand, context, functions)
        if isinstance(node.op, ast.Not):
            return not bool(value)
        if isinstance(node.op, ast.USub):
            return -_number(value)
        return _number(value)
    if isinstance(node, ast.BinOp):
        operation = _BINARY_OPERATORS[type(node.op)]
        return operation(
            _number(_evaluate(node.left, context, functions)), _number(_evaluate(node.right, context, functions))
        )
    if isinstance(node, ast.Compare):
        left = _evaluate(node.left, context, functions)
        for operation_node, comparator in zip(node.ops, node.comparators, strict=True):
            right = _evaluate(comparator, context, functions)
            if not _COMPARE_OPERATORS[type(operation_node)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = functions[node.func.id]
        return function(*(_evaluate(item, context, functions) for item in node.args))
    raise StrategyRuleError(f"unsupported expression: {type(node).__name__}")


def _number(value: object) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StrategyRuleError("numeric operation requires numeric values")
    return value
