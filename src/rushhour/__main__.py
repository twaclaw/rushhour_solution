import argparse
import json

from .game import Game


def main():
    parser = argparse.ArgumentParser(description="Run a Rush Hour game.")
    parser.add_argument("--conf", type=str, help="File with game initial configuration and solution (optional)", required=True)
    parser.add_argument("--algorithm", type=str, help="Algorithm to use (bfs or a_star)", default="a_star", choices=["bfs", "a_star"])
    parser.add_argument("--draw-steps", action="store_true", help="Draw the board at each step of the solution")

    args = parser.parse_args()

    with open(args.conf, "r") as f:
        config = json.load(f)

    g = Game(config["initial_state"])

    print("Initial board:\n")
    g.draw()

    solution, nodes_visited = g.solve(solver=args.algorithm.lower())

    print(f"\nSolution of {len(solution)} moves found by {args.algorithm} visiting {nodes_visited} nodes:\n\n {solution}\n")

    if args.draw_steps:
        g2 = Game(config["initial_state"])
        g2.move_sequence(solution, draw_steps=True, boards_per_row=5)
    else:
        print("Final board:\n")
        g.draw()


if __name__ == "__main__":
    main()
