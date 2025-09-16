import argparse
import json

from rich.columns import Columns
from rich.console import Console

from .game import CarName, Game


def do_solve(args):
    with open(args.conf, "r") as f:
        config = json.load(f)

    g = Game(config["initial_state"])

    initial_board = g.draw(print_table=False, title="Initial Board")

    solution, nodes_visited = g.solve(solver=args.algorithm.lower())

    console = Console()
    if solution is None:
        console.print(initial_board)
        console.print("\n[bold red]Solution found![/bold green]")
        return

    individual_steps = 1 + 5 - g.cars[CarName.X].end[1]
    for move in solution:
        individual_steps += int(move[2])

    final_board = g.draw(print_table=False, title="Final Board")
    console.print(Columns([initial_board, final_board], equal=True, expand=True))

    console.print("\n[bold green]Solution found![/bold green]")
    console.print(f"[cyan]Algorithm:[/cyan] {args.algorithm}")
    console.print(f"[cyan]Moves:[/cyan] {len(solution)} ({individual_steps})")
    console.print(f"[cyan]Nodes visited:[/cyan] {nodes_visited}")
    console.print(f"[cyan]Solution:[/cyan] {solution}\n")

    if args.draw_steps:
        g2 = Game(config["initial_state"])
        g2.move_sequence(solution, draw_steps=True, boards_per_row=5)


def do_verify(args):
    with open(args.conf, "r") as f:
        config = json.load(f)

    g = Game(config["initial_state"])
    print("Initial board:\n")
    g.draw()
    solution = config.get("solution", [])
    if not solution:
        print("No solution found in the configuration file.")
        return
    print(f"\nVerifying solution of {len(solution)} moves:\n\n {solution}\n")
    g.move_sequence(solution, draw_steps=args.draw_steps, boards_per_row=5)

    g.draw()


def main():
    parser = argparse.ArgumentParser(description="Run a Rush Hour game.")
    parser.add_argument(
        "--conf",
        type=str,
        help="File with game initial configuration and solution (optional)",
        required=True,
    )
    parser.add_argument(
        "--draw-steps",
        action="store_true",
        help="Draw the board at each step of the solution",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # Solve subcommand
    solve_parser = subparsers.add_parser("solve", help="Solve the Rush Hour puzzle")
    solve_parser.add_argument(
        "--algorithm",
        type=str,
        help="Algorithm to use (bfs or a_star)",
        default="a_star",
        choices=["bfs", "a_star"],
    )
    solve_parser.set_defaults(func=do_solve)

    # Verify subcommand
    verify_parser = subparsers.add_parser(
        "verify", help="Verify a solution from the configuration file"
    )
    verify_parser.set_defaults(func=do_verify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
