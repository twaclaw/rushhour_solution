import argparse
import ast
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

CAR_COLORS = {
    'X': '#FF0000',    # bright_red
    'A': '#00FF00',    # bright_green
    'B': '#FF8C00',    # dark_orange
    'C': '#00BFFF',    # deep_sky_blue1
    'D': '#FF1493',    # deep_pink1
    'E': '#8A2BE2',    # purple
    'F': '#006400',    # dark_green
    'G': '#808080',    # gray
    'H': '#FFFF99',    # light_yellow3
    'I': '#FFD700',    # light_goldenrod1
    'J': '#8B4513',    # orange4
    'K': '#FFFF00',    # yellow
    'O': '#FFD700',    # gold1
    'P': '#9370DB',    # medium_purple
    'Q': '#0000FF',    # blue1
    'R': '#008000',    # green
}

CAR_SIZES = {
    'X': 2, 'A': 2, 'B': 2, 'C': 2, 'D': 2, 'E': 2, 'F': 2, 'G': 2, 'H': 2, 'I': 2, 'J': 2, 'K': 2,
    'O': 3, 'P': 3, 'Q': 3, 'R': 3
}

BOARD_SIZE = 6


def parse_car_string(car_str):
    if len(car_str) != 4:
        raise ValueError(f"Invalid car string format: {car_str}")

    car_name = car_str[0]
    orientation = car_str[1]  # 'H' or 'V'
    x = int(car_str[2])
    y = int(car_str[3])

    return car_name, orientation, x, y


def draw_grid(car_list:list[str], title:str="", filename:str=None):
    """
    Draw a Rush Hour grid with the specified cars.

    Args:
        car_list: List of car strings in format ["AV00", "BV01", ...]
        title: Title for the grid
        filename: Filename to save the SVG file (without extension)
    """
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    ax.set_xlim(0, BOARD_SIZE)
    ax.set_ylim(0, BOARD_SIZE)
    ax.set_aspect('equal')

    for i in range(BOARD_SIZE + 1):
        ax.axhline(y=i, color='#808080', linewidth=0.5)
        ax.axvline(x=i, color='#808080', linewidth=0.5)

    # exit_rect = Rectangle((BOARD_SIZE, 2), 0.3, 1,
    #                      linewidth=2, edgecolor='red', facecolor='lightcoral', alpha=0.7)
    # ax.add_patch(exit_rect)
    # ax.text(BOARD_SIZE + 0.15, 2.5, 'EXIT', rotation=90, ha='center', va='center',
            # fontweight='bold', color='#808080')

    for car_str in car_list:
        car_name, orientation, x, y = parse_car_string(car_str)

        if car_name not in CAR_COLORS:
            print(f"Warning: Unknown car '{car_name}', skipping...")
            continue

        color = CAR_COLORS[car_name]
        size = CAR_SIZES[car_name]

        if orientation == 'H':  # Horizontal
            rect = Rectangle((y, x), size, 1,
                           linewidth=0, facecolor=color, alpha=0.6)
            ax.add_patch(rect)
            # ax.text(y + 0.8, x + 0.2, car_name,
                #    ha='center', va='center', fontweight='normal', fontsize=12)

        elif orientation == 'V':  # Vertical
            rect = Rectangle((y, x), 1, size,
                           linewidth=0, facecolor=color, alpha=0.6)
            ax.add_patch(rect)
            # ax.text(y + 0.8, x + 0.2, car_name,
                #    ha='center', va='center', fontweight='normal', fontsize=12)

    ax.set_title(title, fontsize=16, fontweight='bold')

    # Hide all ticks and tick labels
    ax.set_xticks([])
    ax.set_yticks([])

    # Set border (spines) color to match grid lines
    for spine in ax.spines.values():
        spine.set_color('#808080')

    ax.invert_yaxis()

    plt.tight_layout()

    # Save as SVG
    if filename:
        plt.savefig(f"{filename}.svg", format='svg', bbox_inches='tight')
        print(f"Grid saved as {filename}.svg")

    return fig, ax


def parse_car_list(input_str):
    """
    Args:
        input_str: String like "['AV00', 'XH32']"
    """
    try:
        # Use ast.literal_eval for safe evaluation of the list string
        return ast.literal_eval(input_str)
    except (ValueError, SyntaxError) as e:
        raise ValueError(f"Invalid list format: {input_str}. Expected format: \"['AV00', 'XH32']\"") from e


def main():
    parser = argparse.ArgumentParser(description="Draw Rush Hour grid from car list.")
    parser.add_argument("--input", type=str, required=True,
                       help="List of car strings, e.g., \"['AV00', 'XH32']\"")
    parser.add_argument("--title", type=str, help="Image title", default="")

    parser.add_argument("--output", type=str, required=True,
                       help="Output filename for SVG (without .svg extension)")

    args = parser.parse_args()

    try:
        car_list = parse_car_list(args.input)

        if not isinstance(car_list, list):
            raise ValueError("Input must be a list of strings")

        for item in car_list:
            if not isinstance(item, str):
                raise ValueError(f"All car specifications must be strings, got: {item}")

        draw_grid(car_list, filename=args.output, title=args.title)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
