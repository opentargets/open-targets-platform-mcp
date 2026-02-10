"""GraphQL schema introspection and parsing for RLM-based exploration."""

import asyncio
import time
from typing import Any

from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    get_named_type,
)

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema

# Cache TTL: 1 hour (synchronized with schema cache)
_SCHEMA_CACHE_TTL = 3600

# Module-level cache for SchemaExplorer instance
_explorer_cache: dict[str, Any] = {}
_explorer_cache_lock = asyncio.Lock()


class SchemaExplorer:
    """GraphQL schema introspection and parsing utility.

    Provides methods to explore GraphQL schema structure without loading
    the entire schema SDL text, enabling RLM-based incremental discovery.
    """

    def __init__(self, schema: GraphQLSchema):
        """Initialize with GraphQLSchema object.

        Args:
            schema: The GraphQLSchema object to explore
        """
        self.schema = schema

    def list_query_fields(self) -> list[dict]:
        """Extract all Query root fields.

        Returns:
            List of query fields with names, descriptions, arguments, and return types.
            Example:
                [
                    {
                        "name": "target",
                        "description": "Get information about a gene...",
                        "args": ["ensemblId: String!"],
                        "return_type": "Target"
                    },
                    ...
                ]
        """
        if not self.schema.query_type:
            return []

        fields = []
        for field_name, field in self.schema.query_type.fields.items():
            fields.append({
                "name": field_name,
                "description": field.description,
                "args": [
                    f"{arg_name}: {self._format_type(arg.type)}"
                    for arg_name, arg in field.args.items()
                ],
                "return_type": self._format_type(field.type),
            })

        return sorted(fields, key=lambda x: x["name"])

    def list_object_types(self) -> list[dict]:
        """Extract all object types (excluding Query, Mutation, Subscription).

        Returns:
            List of object types with names, descriptions, and field counts.
            Example:
                [
                    {
                        "name": "Target",
                        "description": "Target represents a gene or protein",
                        "field_count": 47
                    },
                    ...
                ]
        """
        object_types = []

        for type_name, type_obj in self.schema.type_map.items():
            # Skip introspection types, query/mutation/subscription types
            if self._is_introspection_type(type_name):
                continue

            if type_name in ("Query", "Mutation", "Subscription"):
                continue

            if isinstance(type_obj, GraphQLObjectType):
                object_types.append({
                    "name": type_name,
                    "description": type_obj.description,
                    "field_count": len(type_obj.fields),
                })

        return sorted(object_types, key=lambda x: x["name"])

    def list_input_types(self) -> list[dict]:
        """Extract all input types.

        Returns:
            List of input types with names and descriptions.
        """
        input_types = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            if isinstance(type_obj, GraphQLInputObjectType):
                input_types.append({
                    "name": type_name,
                    "description": type_obj.description,
                    "field_count": len(type_obj.fields),
                })

        return sorted(input_types, key=lambda x: x["name"])

    def list_enum_types(self) -> list[dict]:
        """Extract all enum types.

        Returns:
            List of enum types with names, descriptions, and values.
        """
        enum_types = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            if isinstance(type_obj, GraphQLEnumType):
                enum_types.append({
                    "name": type_name,
                    "description": type_obj.description,
                    "values": list(type_obj.values.keys()),
                })

        return sorted(enum_types, key=lambda x: x["name"])

    def list_scalar_types(self) -> list[dict]:
        """Extract custom scalar types (excludes built-in scalars).

        Returns:
            List of custom scalar types with names and descriptions.
        """
        scalar_types = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            if self._is_built_in_scalar(type_name):
                continue

            if isinstance(type_obj, GraphQLScalarType):
                scalar_types.append({
                    "name": type_name,
                    "description": type_obj.description,
                })

        return sorted(scalar_types, key=lambda x: x["name"])

    def get_type_info(self, type_name: str) -> dict:
        """Get detailed information about a specific type.

        Args:
            type_name: Name of the type (e.g., "Target", "Disease")

        Returns:
            Dictionary with comprehensive type information including fields,
            arguments, and interface implementations.

        Raises:
            ValueError: If type doesn't exist in schema
        """
        type_obj = self.schema.type_map.get(type_name)

        if not type_obj:
            msg = f"Type '{type_name}' not found in schema"
            raise ValueError(msg)

        result: dict[str, Any] = {
            "name": type_name,
            "kind": type_obj.__class__.__name__.replace("GraphQL", "").replace("Type", "").upper(),
            "description": getattr(type_obj, "description", None),
        }

        # Handle different type kinds
        if isinstance(type_obj, (GraphQLObjectType, GraphQLInterfaceType)):
            result["fields"] = self._extract_object_fields(type_obj)

            # Add interface implementations for object types
            if isinstance(type_obj, GraphQLObjectType):
                result["implements_interfaces"] = [
                    iface.name for iface in type_obj.interfaces
                ]

        elif isinstance(type_obj, GraphQLInputObjectType):
            result["fields"] = self._extract_input_fields(type_obj)

        elif isinstance(type_obj, GraphQLEnumType):
            result["values"] = [
                {
                    "name": value_name,
                    "description": value.description,
                }
                for value_name, value in type_obj.values.items()
            ]

        elif isinstance(type_obj, GraphQLScalarType):
            # Scalars don't have fields, just description
            pass

        return result

    def search_types(self, pattern: str) -> list[dict]:
        """Search for types whose names match the pattern.

        Args:
            pattern: Search pattern (case-insensitive substring match)

        Returns:
            List of matching types with names, kinds, and descriptions.
        """
        pattern_lower = pattern.lower()
        matches = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            if pattern_lower in type_name.lower():
                matches.append({
                    "name": type_name,
                    "kind": type_obj.__class__.__name__.replace("GraphQL", "").replace("Type", "").upper(),
                    "description": getattr(type_obj, "description", None),
                    "match_reason": "type_name",
                })

        return matches

    def search_fields(self, pattern: str) -> list[dict]:
        """Search for fields whose names match the pattern.

        Args:
            pattern: Search pattern (case-insensitive substring match)

        Returns:
            List of matching fields across all types.
        """
        pattern_lower = pattern.lower()
        matches = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            # Check object and interface types
            if isinstance(type_obj, (GraphQLObjectType, GraphQLInterfaceType)):
                for field_name, field in type_obj.fields.items():
                    if pattern_lower in field_name.lower():
                        matches.append({
                            "type_name": type_name,
                            "field_name": field_name,
                            "field_type": self._format_type(field.type),
                            "description": field.description,
                            "match_reason": "field_name",
                        })

            # Check input types
            elif isinstance(type_obj, GraphQLInputObjectType):
                for field_name, field in type_obj.fields.items():
                    if pattern_lower in field_name.lower():
                        matches.append({
                            "type_name": type_name,
                            "field_name": field_name,
                            "field_type": self._format_type(field.type),
                            "description": getattr(field, "description", None),
                            "match_reason": "field_name",
                        })

        return matches

    def search_descriptions(self, pattern: str) -> list[dict]:
        """Search for types and fields whose descriptions match the pattern.

        Args:
            pattern: Search pattern (case-insensitive substring match)

        Returns:
            List of matching types and fields.
        """
        pattern_lower = pattern.lower()
        matches = []

        for type_name, type_obj in self.schema.type_map.items():
            if self._is_introspection_type(type_name):
                continue

            # Check type description
            type_desc = getattr(type_obj, "description", None)
            if type_desc and pattern_lower in type_desc.lower():
                matches.append({
                    "name": type_name,
                    "kind": type_obj.__class__.__name__.replace("GraphQL", "").replace("Type", "").upper(),
                    "description": type_desc,
                    "match_reason": "description",
                })

            # Check field descriptions
            if isinstance(type_obj, (GraphQLObjectType, GraphQLInterfaceType)):
                for field_name, field in type_obj.fields.items():
                    if field.description and pattern_lower in field.description.lower():
                        matches.append({
                            "type_name": type_name,
                            "field_name": field_name,
                            "field_type": self._format_type(field.type),
                            "description": field.description,
                            "match_reason": "description",
                        })

        return matches

    def _format_type(self, graphql_type: GraphQLType) -> str:
        """Format GraphQL type as string.

        Handles wrapped types (NonNull, List) and returns readable format.

        Examples:
            String! (non-null string)
            [Int] (list of ints)
            [Target!]! (non-null list of non-null targets)

        Args:
            graphql_type: The GraphQL type to format

        Returns:
            Formatted type string
        """
        if isinstance(graphql_type, GraphQLNonNull):
            return f"{self._format_type(graphql_type.of_type)}!"

        if isinstance(graphql_type, GraphQLList):
            return f"[{self._format_type(graphql_type.of_type)}]"

        # Base type
        named_type = get_named_type(graphql_type)
        return named_type.name

    def _extract_object_fields(self, type_obj: GraphQLObjectType | GraphQLInterfaceType) -> list[dict]:
        """Extract field information from an object or interface type.

        Args:
            type_obj: The object or interface type

        Returns:
            List of field dictionaries with names, types, arguments, and descriptions
        """
        fields = []

        for field_name, field in type_obj.fields.items():
            field_info = {
                "name": field_name,
                "type": self._format_type(field.type),
                "description": field.description,
                "args": [],
            }

            # Extract arguments
            for arg_name, arg in field.args.items():
                arg_info = {
                    "name": arg_name,
                    "type": self._format_type(arg.type),
                    "description": arg.description,
                }

                # Add default value if present
                if arg.default_value is not None:
                    arg_info["default_value"] = arg.default_value

                field_info["args"].append(arg_info)

            fields.append(field_info)

        return sorted(fields, key=lambda x: x["name"])

    def _extract_input_fields(self, type_obj: GraphQLInputObjectType) -> list[dict]:
        """Extract field information from an input type.

        Args:
            type_obj: The input type

        Returns:
            List of field dictionaries
        """
        fields = []

        for field_name, field in type_obj.fields.items():
            field_info = {
                "name": field_name,
                "type": self._format_type(field.type),
                "description": getattr(field, "description", None),
            }

            # Add default value if present
            if hasattr(field, "default_value") and field.default_value is not None:
                field_info["default_value"] = field.default_value

            fields.append(field_info)

        return sorted(fields, key=lambda x: x["name"])

    def _is_introspection_type(self, type_name: str) -> bool:
        """Check if type is a GraphQL introspection type.

        Args:
            type_name: The type name to check

        Returns:
            True if introspection type (starts with __)
        """
        return type_name.startswith("__")

    def _is_built_in_scalar(self, type_name: str) -> bool:
        """Check if type is a built-in GraphQL scalar.

        Args:
            type_name: The type name to check

        Returns:
            True if built-in scalar (String, Int, Float, Boolean, ID)
        """
        return type_name in ("String", "Int", "Float", "Boolean", "ID")


async def get_schema_explorer() -> SchemaExplorer:
    """Get cached SchemaExplorer instance or create new one.

    Implements two-level caching:
    1. GraphQLSchema object (in tools/schema/schema.py)
    2. SchemaExplorer instance (here)

    Both synchronized to same TTL (1 hour).

    Returns:
        Cached or new SchemaExplorer instance
    """
    async with _explorer_cache_lock:
        current_time = time.time()

        # Check cache
        if "explorer" in _explorer_cache and "timestamp" in _explorer_cache:
            if (current_time - _explorer_cache["timestamp"]) < _SCHEMA_CACHE_TTL:
                return _explorer_cache["explorer"]

        # Cache miss - fetch schema and create explorer
        schema_obj = await fetch_graphql_schema()  # Uses its own cache
        explorer = SchemaExplorer(schema_obj)

        _explorer_cache["explorer"] = explorer
        _explorer_cache["timestamp"] = current_time

        return explorer
