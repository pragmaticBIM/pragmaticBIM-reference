"""Evaluate a German element applicability expression against one product."""

from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.util.element

_MISSING = object()
_ENTITY_ATTRIBUTES = {"entity_ifc4", "entity_ifc2x3", "entity_ifc4_3"}


def german_applicability(element: dict[str, Any]) -> str:
    """German applicability text. A localised mapping uses the ``de`` entry."""
    applicability = element.get("applicability")
    if isinstance(applicability, dict):
        applicability = applicability.get("de")
    return str(applicability or "").strip()


def matches_applicability(
    product: ifcopenshell.entity_instance,
    expression: str,
    *,
    entity_schema: str | None = None,
    exact_entity: bool = False,
) -> bool:
    """Return whether ``product`` satisfies ``expression``.

    ``entity_schema`` limits ``entity_ifc*`` clauses to that file schema, so an
    IFC4 example is not selected by an ``entity_ifc2x3`` fallback.
    ``exact_entity`` compares the product's class name, so an ``IfcFlowTerminal``
    rule does not also collect ``IfcSpaceHeater`` context from the same file.
    """
    psets = ifcopenshell.util.element.get_psets(product)
    return _Parser(
        expression,
        product,
        psets,
        entity_schema=entity_schema,
        exact_entity=exact_entity,
    ).parse()


class _Parser:
    def __init__(
        self,
        expression: str,
        product: ifcopenshell.entity_instance,
        psets: dict[str, dict[str, Any]],
        *,
        entity_schema: str | None,
        exact_entity: bool,
    ) -> None:
        self.tokens = _tokenize(expression)
        self.product = product
        self.psets = psets
        self.entity_schema = entity_schema
        self.exact_entity = exact_entity
        self.index = 0

    def parse(self) -> bool:
        value = self._parse_or()
        if self._peek() is not None:
            raise ValueError(f"trailing token {self._peek()!r}")
        return value

    def _parse_or(self) -> bool:
        value = self._parse_and()
        while self._peek() == "OR":
            self.index += 1
            right = self._parse_and()
            value = value or right
        return value

    def _parse_and(self) -> bool:
        value = self._parse_factor()
        while self._peek() == "AND":
            self.index += 1
            right = self._parse_factor()
            value = value and right
        return value

    def _parse_factor(self) -> bool:
        token = self._peek()
        if token == "(":
            self.index += 1
            value = self._parse_or()
            if self._peek() != ")":
                raise ValueError("missing closing parenthesis")
            self.index += 1
            return value
        if isinstance(token, tuple) and token[0] == "cmp":
            self.index += 1
            return self._compare(token[1], token[2])
        raise ValueError(f"unexpected token {token!r}")

    def _peek(self) -> Any:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _compare(self, attribute: str, expected: str) -> bool:
        if attribute in _ENTITY_ATTRIBUTES:
            if self.entity_schema is not None and not _clause_applies(
                self.entity_schema, attribute
            ):
                return False
            if self.exact_entity:
                return self.product.is_a() == expected
            return self.product.is_a(expected)
        if "." in attribute:
            pset_name, prop = attribute.split(".", 1)
            return _eq((self.psets.get(pset_name) or {}).get(prop), expected)
        actual = _entity_value(self.product, attribute)
        if actual is not _MISSING:
            return _eq(actual, expected)
        for props in self.psets.values():
            if attribute in props and _eq(props[attribute], expected):
                return True
        return False


def _clause_applies(file_schema: str, attribute: str) -> bool:
    schema = file_schema.upper()
    if attribute == "entity_ifc2x3":
        return schema.startswith("IFC2X3")
    if attribute == "entity_ifc4_3":
        return schema.startswith("IFC4X3")
    if attribute == "entity_ifc4":
        return schema.startswith("IFC4") and not schema.startswith("IFC4X3")
    return False


def _entity_value(product: ifcopenshell.entity_instance, name: str) -> Any:
    try:
        if not hasattr(product, name):
            return _MISSING
        value = getattr(product, name)
    except (AttributeError, RuntimeError):
        return _MISSING
    if value is None or value == "":
        return _MISSING
    return value


def _eq(actual: Any, expected: str) -> bool:
    if actual is None:
        return False
    if hasattr(actual, "wrappedValue"):
        actual = actual.wrappedValue
    if expected.upper() in {"TRUE", "FALSE"}:
        return _as_bool(actual) == (expected.upper() == "TRUE")
    return str(actual) == expected


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().upper() in {"TRUE", "1", "YES", "T"}


def _tokenize(expression: str) -> list[Any]:
    tokens: list[Any] = []
    index = 0
    length = len(expression)
    while index < length:
        if expression[index].isspace():
            index += 1
            continue
        if expression[index] in "()":
            tokens.append(expression[index])
            index += 1
            continue
        if expression.startswith("AND", index) and _boundary(expression, index + 3):
            tokens.append("AND")
            index += 3
            continue
        if expression.startswith("OR", index) and _boundary(expression, index + 2):
            tokens.append("OR")
            index += 2
            continue
        start = index
        while index < length and (expression[index].isalnum() or expression[index] in "._"):
            index += 1
        attribute = expression[start:index]
        if not attribute or index >= length or expression[index] != "=":
            raise ValueError(f"expected comparison at {expression[index:index + 24]!r}")
        index += 1
        if index < length and expression[index] == '"':
            index += 1
            value_start = index
            while index < length and expression[index] != '"':
                index += 1
            value = expression[value_start:index]
            index += 1
        else:
            value_start = index
            while index < length and not expression[index].isspace() and expression[index] not in "()":
                index += 1
            value = expression[value_start:index]
        tokens.append(("cmp", attribute, value))
    return tokens


def _boundary(expression: str, index: int) -> bool:
    return index >= len(expression) or not (
        expression[index].isalnum() or expression[index] == "_"
    )
