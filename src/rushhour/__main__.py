import argparse
import json

from .game import Game


def main():
    parser = argparse.ArgumentParser(description="Run a Rush Hour game.")
    parser.add_argument("--conf", type=str, help="File with game initial configuration and solution (optional)", required=True)
    parser.add_argument("--algorithm", type=str, help="Algorithm to use (bfs or a_star)", default="a_star", choices=["bfs", "a_star"])

    args = parser.parse_args()

    with open(args.conf, "r") as f:
        config = json.load(f)

    g = Game(config["initial_state"])

    print("Initial board:\n")
    print(g)

    solution, nodes_visited = g.solve(solver=args.algorithm.lower())

    print(f"\nSolution found by {args.algorithm} visiting {nodes_visited} nodes:\n\n {solution}\n")
    print("Final board:\n")
    print(g)


if __name__ == "__main__":
    main()
