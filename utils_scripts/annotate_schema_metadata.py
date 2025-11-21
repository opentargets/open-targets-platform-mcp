# usage: uv run scripts/annotate_schema_metadata.py schema.graphql <query_path>

import sys

from graphql import (
    TypeInfo,
    TypeInfoVisitor,
    Visitor,
    build_schema,
    parse,
    visit,
)


def annotate_query(schema_path, query_path):  # noqa: C901
    print(f"Processing {query_path} using schema {schema_path}")

    # Load Schema
    try:
        with open(schema_path) as f:
            schema_content = f.read()

        # Patch missing scalars
        if "scalar Long" not in schema_content:
            schema_content = "scalar Long\n" + schema_content
        # Add other common scalars if needed
        if "scalar Object" not in schema_content:
            schema_content = "scalar Object\n" + schema_content

        schema = build_schema(schema_content)
    except Exception as e:
        print(f"Error loading schema: {e}")
        sys.exit(1)

    # Load Query
    try:
        with open(query_path) as f:
            query_content = f.read()
        document_ast = parse(query_content)
    except Exception as e:
        print(f"Error loading query: {e}")
        sys.exit(1)

    type_info = TypeInfo(schema)

    # Store annotations
    annotations = []

    class AnnotationVisitor(Visitor):
        def enter_field(self, node, key, parent, path, ancestors):
            field_def = type_info.get_field_def()
            if field_def and field_def.description:
                line = node.loc.start_token.line
                annotations.append({"line": line, "description": field_def.description})

    visitor = TypeInfoVisitor(type_info, AnnotationVisitor())
    visit(document_ast, visitor)

    # Group annotations by line (in case of multiple fields on one line)
    anns_by_line = {}
    for ann in annotations:
        line_number = ann["line"]
        if line_number not in anns_by_line:
            anns_by_line[line_number] = []
        # Avoid duplicates if same field visited twice? (unlikely)
        if ann["description"] not in anns_by_line[line_number]:
            anns_by_line[line_number].append(ann["description"])

    lines = query_content.splitlines()

    # We will reconstruct the file content
    # It is easier to process from top to bottom if we just rebuild the list of lines
    # BUT matching existing comments requires looking ahead or behind.
    # Let's do the edits approach.

    # Sort lines that have annotations in descending order to apply edits from bottom up
    sorted_lines = sorted(anns_by_line.keys(), reverse=True)

    edits = []  # list of (start_idx, end_idx, new_lines)

    # We need to keep track of lines we've already touched to avoid overlap
    touched_indices = set()

    for line_num in sorted_lines:
        # 0-based index of the field line
        field_idx = line_num - 1

        descriptions = anns_by_line[line_num]
        full_desc = "\n".join(descriptions)

        # Get indentation
        current_line_content = lines[field_idx]
        indent = current_line_content[: len(current_line_content) - len(current_line_content.lstrip())]

        new_comment_lines = [f"{indent}# {line}" for line in full_desc.split("\n")]

        # Find existing comment block immediately above
        start_comment_idx = field_idx
        idx = field_idx - 1

        while idx >= 0:
            if idx in touched_indices:
                # Stop if we hit a line processed by another annotation (shouldn't happen if sorted desc and fields are distinct)
                break

            line = lines[idx].strip()
            if line.startswith("#"):
                start_comment_idx = idx
                idx -= 1
            else:
                break

        # Mark these lines as touched
        # range [start_comment_idx, field_idx) are the comment lines
        # We don't touch the field line itself in terms of replacement, but we conceptually "own" the space above it

        # However, if we have adjacent fields, the comment for the lower field might eat the comment for the upper field?
        # Example:
        # Field A
        # Field B
        # If Field B has no comment, idx scans up to Field A. Field A is not a comment. Stop. Correct.
        # If Field A has a comment:
        # # Comment A
        # Field A
        # Field B
        # Visitor B (Field B): Scans up. Field A is not comment. Stop. Start=Field B idx. Insert.
        # Visitor A (Field A): Scans up. Found Comment A. Start=Comment A idx. Replace.

        # Logic holds.

        edits.append({"start": start_comment_idx, "end": field_idx, "lines": new_comment_lines})

    # Apply edits from top to bottom? Or bottom to top?
    # Edits are (start, end) ranges in ORIGINAL lines.
    # If we apply from bottom to top (sorted_lines is desc), the indices remain valid.

    new_file_lines = list(lines)

    for edit in edits:
        s = edit["start"]
        e = edit["end"]
        repl = edit["lines"]

        # Replace slice
        new_file_lines[s:e] = repl

    # Write back
    with open(query_path, "w") as f:
        output = "\n".join(new_file_lines)
        if query_content.endswith("\n"):
            output += "\n"
        f.write(output)

    print(f"Successfully annotated {query_path} (updated existing)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python annotate_schema_metadata.py <schema_path> <query_path>")
        sys.exit(1)

    schema_file = sys.argv[1]
    query_file = sys.argv[2]

    annotate_query(schema_file, query_file)
