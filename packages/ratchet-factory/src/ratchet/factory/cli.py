"""ratchet CLI — scaffold agents and modules.

Usage:
    ratchet init <name> [--timezone <tz>]
    ratchet new module <name> [--description <desc>]
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

    # ratchet init <name>
    init_parser = sub.add_parser("init", help="Create a new Ratchet agent")
    init_parser.add_argument("name", help="Agent name (e.g., 'pawl', 'atlas', 'my-agent')")
    init_parser.add_argument("--timezone", default="America/New_York", help="Timezone (default: America/New_York)")
    init_parser.add_argument("--dir", default=None, help="Parent directory (default: current)")

    # ratchet new module <name>
    new_parser = sub.add_parser("new", help="Create a new Ratchet module or component")
    new_sub = new_parser.add_subparsers(dest="new_type")

    mod_parser = new_sub.add_parser("module", help="Scaffold a new Ratchet module package")
    mod_parser.add_argument("name", help="Module name (e.g., 'research', 'disk-monitor')")
    mod_parser.add_argument("--description", default="", help="One-line module description")
    mod_parser.add_argument("--dir", default=None, help="Parent directory (default: current)")

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
                print(f"    # Then register in your agent:")
                print(f"    # from ratchet.{args.name.replace('-', '_')} import {args.name.replace('-', ' ').title().replace(' ', '')}Module")
                print()
            except FileExistsError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            new_parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
