"""
Run the DSL-to-B generation pipeline.

Pipeline stages:
1. Read the chosen DSL source file from disk.
2. Parse the source text with the Lark grammar.
3. Run the static type checker on the parse tree.
4. Transform the checked tree into classical B machine text.
5. Write the generated machine to a `.mch` file.
"""

import argparse
from pathlib import Path

from lark import Lark
from lark.exceptions import LarkError

from dsl_grammar import grammar
from dsl_typecheck import DSLTypeError, DSLTypeChecker
from dsl_transpiler import EventBGenerator


DSL_FILENAME = "my_token.dsl"
OUTPUT_FILENAME = "MyToken_Machine.mch"


def _resolve_cli_path(path_text):
    """Resolve a CLI path relative to the caller's working directory."""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a DSL contract and generate a classical B machine."
    )
    parser.add_argument(
        "dsl_path",
        nargs="?",
        help="Optional path to the input .dsl file. Defaults to the built-in my_token example.",
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        help="Optional path to the generated .mch file. Defaults beside a custom input file.",
    )
    parser.add_argument(
        "--defensive",
        action="store_true",
        help="Generate defensive-style B operations with top-level IF guards.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    if args.dsl_path:
        dsl_path = _resolve_cli_path(args.dsl_path)
        output_path = (
            _resolve_cli_path(args.output_path)
            if args.output_path
            else dsl_path.with_suffix(".mch")
        )
    else:
        dsl_path = base_dir / DSL_FILENAME
        output_path = base_dir / OUTPUT_FILENAME

    try:
        # Step 1: read DSL source text.
        input_code = dsl_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: Could not find file '{dsl_path.name}'")
        raise SystemExit(1)

    # Step 2: construct the parser from the grammar specification.
    parser = Lark(grammar, parser="lalr", propagate_positions=True)

    try:
        # Step 3: parse and type-check the DSL before B generation.
        tree = parser.parse(input_code)
        DSLTypeChecker().check(tree)
        generator = EventBGenerator(defensive=args.defensive)
        b_machine_code = generator.transform(tree)
        # Step 4: write generated machine to disk.
        output_path.write_text(b_machine_code, encoding="utf-8")
        style = "defensive" if args.defensive else "offensive"
        print(f"OK: Generated {style}-style classical B machine saved to: {output_path.name}")
    except DSLTypeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
    except LarkError as exc:
        print(f"ERROR: DSL parsing failed: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        print(f"ERROR: DSL transpiling failed: {exc}")
        raise SystemExit(1)
