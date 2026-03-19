"""ratchet CLI — scaffold, generate, setup, and manage agents and modules.

Usage:
    ratchet init <name>
    ratchet new module <name>
    ratchet generate module "<description>"
    ratchet setup openclaw [--workspace <path>]
    ratchet --help
"""

import argparse
import sys

from ratchet.factory.scaffold import scaffold_agent, scaffold_module


def main():
    parser = argparse.ArgumentParser(
        prog="ratchet",
        description="Ratchet — the accountability layer for AI agents",
    )
    sub = parser.add_subparsers(dest="command")

    # ratchet init
    init_parser = sub.add_parser("init", help="Create a new Ratchet agent")
    init_parser.add_argument("name", help="Agent name")
    init_parser.add_argument("--timezone", default="America/New_York")
    init_parser.add_argument("--dir", default=None)

    # ratchet new module
    new_parser = sub.add_parser("new", help="Create a new component (stub)")
    new_sub = new_parser.add_subparsers(dest="new_type")
    mod_parser = new_sub.add_parser("module", help="Scaffold a module package (empty stub)")
    mod_parser.add_argument("name", help="Module name")
    mod_parser.add_argument("--description", default="")
    mod_parser.add_argument("--dir", default=None)

    # ratchet generate module
    gen_parser = sub.add_parser("generate", help="Generate a component with AI")
    gen_sub = gen_parser.add_subparsers(dest="gen_type")
    gen_mod_parser = gen_sub.add_parser("module", help="Generate a module with LLM-written implementation")
    gen_mod_parser.add_argument("description", help="Natural language description")
    gen_mod_parser.add_argument("--name", dest="mod_name", default=None, help="Module name")
    gen_mod_parser.add_argument("--dir", default=None)
    gen_mod_parser.add_argument("--model", default="claude-sonnet-4-20250514")
    gen_mod_parser.add_argument("--dry-run", action="store_true", help="Print code without writing files")
    gen_mod_parser.add_argument("--no-test", action="store_true", help="Skip auto-testing")
    gen_mod_parser.add_argument("--no-review", action="store_true", help="Skip code review")
    gen_mod_parser.add_argument("--force", action="store_true", help="Accept even if tests fail")

    # ratchet setup <platform>
    setup_parser = sub.add_parser("setup", help="Wire Ratchet into an existing agent platform")
    setup_sub = setup_parser.add_subparsers(dest="platform")

    oc_parser = setup_sub.add_parser("openclaw", help="Set up Ratchet in an OpenClaw workspace")
    oc_parser.add_argument("--workspace", default=None, help="OpenClaw workspace path (auto-detect if not set)")
    oc_parser.add_argument("--force", action="store_true", help="Overwrite existing config files")
    oc_parser.add_argument("--no-wrappers", action="store_true", help="Skip bin/ wrapper installation")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        try:
            path = scaffold_agent(args.name, target_dir=args.dir, timezone_str=args.timezone)
            print(f"\n🔩 Agent '{args.name}' created at {path}/\n")
            print("  Next steps:")
            print(f"    cd {path}")
            print(f"    pip install ratchet-core ratchet-memory ratchet-pilot")
            print(f"    python {path.name}.py")
            print()
        except FileExistsError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "new":
        if args.new_type == "module":
            try:
                path = scaffold_module(args.name, description=args.description, target_dir=args.dir)
                print(f"\n🔩 Module 'ratchet-{args.name}' created at {path}/\n")
                print("  Next steps:")
                print(f"    pip install -e {path}")
                print()
            except FileExistsError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            new_parser.print_help()
            sys.exit(1)

    elif args.command == "generate":
        if args.gen_type == "module":
            _handle_generate_module(args)
        else:
            gen_parser.print_help()
            sys.exit(1)

    elif args.command == "setup":
        if args.platform == "openclaw":
            _handle_setup_openclaw(args)
        else:
            setup_parser.print_help()
            sys.exit(1)


def _handle_setup_openclaw(args):
    """Handle: ratchet setup openclaw"""
    from ratchet.factory.setup import setup_openclaw

    print("\n🔩 Setting up Ratchet in OpenClaw workspace...\n")

    try:
        results = setup_openclaw(
            workspace=args.workspace,
            skip_existing=not args.force,
            install_wrappers=not args.no_wrappers,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Workspace: {results['workspace']}")
    print()

    if results["created"]:
        print(f"  Created ({len(results['created'])}):")
        for f in results["created"]:
            print(f"    + {f}")

    if results["skipped"]:
        print(f"\n  Skipped ({len(results['skipped'])}):")
        for f in results["skipped"]:
            print(f"    - {f}")

    if results["wrappers"]:
        print(f"\n  Wrappers installed: {results['wrappers']}")
        print(f"  Old scripts backed up as *.pre-ratchet")

    print(f"\n✅ Ratchet is wired into OpenClaw.\n")
    print("  Available commands:")
    print("    python3 bin/memory-extract       # Extract facts from session")
    print("    python3 bin/memory-retrieve      # Retrieve relevant facts")
    print("    python3 bin/trust-check --summary  # Check trust tier")
    print("    python3 bin/preflight-check 'action'  # Guardrail check")
    print("    python3 bin/research 'question'   # Deep research")
    print("    python3 bin/cost-report           # API cost summary")
    print()


def _handle_generate_module(args):
    """Handle: ratchet generate module '<description>'"""
    from ratchet.factory.codegen import generate_module_code

    print(f"\n🏭 Generating module from description...")
    print(f"   \"{args.description}\"\n")

    try:
        result = generate_module_code(
            description=args.description,
            module_name=args.mod_name,
            model=args.model,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    code = result["code"]
    class_name = result["class_name"]
    module_name = result["module_name"]

    print(f"   Generated: {class_name} (module name: {module_name})")
    print(f"   Lines: {len(code.splitlines())}")

    if args.dry_run:
        print(f"\n{'='*60}")
        print(code)
        print(f"{'='*60}")
        print(f"\n   (dry run — no files written)")
        return

    # Layer 3: Quality Check
    run_tests = not args.no_test
    run_review = not args.no_review

    if run_tests or run_review:
        from ratchet.factory.review import quality_check

        print(f"\n🔍 Running quality checks...")
        report = quality_check(
            module_code=code, class_name=class_name, module_name=module_name,
            model=args.model, skip_tests=not run_tests, skip_review=not run_review,
        )

        if run_tests:
            tr = report.test_result
            if tr.passed:
                print(f"   ✅ Tests: {tr.tests_run} passed")
            else:
                print(f"   ❌ Tests: FAILED")
                for line in tr.output.strip().splitlines()[-15:]:
                    print(f"      {line}")

        if run_review:
            rv = report.review_result
            icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(rv.verdict, "?")
            print(f"   {icon} Review: {rv.verdict.upper()} — {rv.summary}")
            if rv.bugs:
                for b in rv.bugs:
                    print(f"        - {b}")

        if not report.passed and not args.force:
            print(f"\n   Quality check {report.verdict.upper()}. Use --force to accept anyway.")
            sys.exit(1)

    # Scaffold and write
    from ratchet.factory.scaffold import scaffold_module, _slugify
    slug = _slugify(args.mod_name or module_name)

    try:
        path = scaffold_module(name=slug, description=args.description[:100], target_dir=args.dir)
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    module_dir = slug.replace("-", "_")
    (path / "src" / "ratchet" / module_dir / "module.py").write_text(code, encoding="utf-8")
    init_content = f'"""{args.description[:100]}"""\n\nfrom ratchet.{module_dir}.module import {class_name}\n\n__all__ = ["{class_name}"]\n'
    (path / "src" / "ratchet" / module_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    print(f"\n🔩 Module 'ratchet-{slug}' generated at {path}/\n")


if __name__ == "__main__":
    main()
