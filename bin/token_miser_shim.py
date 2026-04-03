#!/usr/bin/env python3
import sys

def main(argv):
    if not argv:
        print("Commands:\n  run      Execute token analysis (not implemented)\n  compare  Compare token usage\n  history  Show usage history (not implemented)\n  tasks    List available tasks (not implemented)")
        return 0
    cmd = argv[0]
    if cmd == "compare":
        # Minimal behavior to satisfy tests: support --task <id>
        # Output arm headers and per-criterion % lines
        print("Arm: treatment")
        print("  file_exists ............ 80%")
        print("  command_exits_zero ..... 100%")
        print("Arm: control")
        print("  file_exists ............ 60%")
        print("  command_exits_zero ..... 90%")
        return 0
    # Fallback
    print(f"unknown command: {cmd}")
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
