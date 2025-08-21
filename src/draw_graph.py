import argparse
from io import BytesIO
from PIL import Image
from rich import get_console

from dotenv import load_dotenv

def main():
    parser = argparse.ArgumentParser(description='Graph generator')
    parser.add_argument('--output', choices=['console', 'image'], help='Output type. Choose "console" to print the graph to the console or "image" to save it as an image.')
    parser.add_argument('--image_path', help='Path to save the image (required when --output is "image")')
    #parser.add_argument('--env_path', help='Path to the environment file (e.g. .env)')

    args = parser.parse_args()

    if not args.output and not args.image_path:
        parser.print_help()
        return

    if args.output == 'image' and not args.image_path:
        parser.error('Error: --image_path is required when --output is "image"')

    load_dotenv()

    from edwards.graph import graph

    if args.output == 'console':
        get_console().print(graph.get_graph(xray=1))
    elif args.output == 'image':
        img_bytes = graph.get_graph(xray=True).draw_mermaid_png()
        img = Image.open(BytesIO(img_bytes))
        img.save(args.image_path)
        print(f'Image saved to {args.image_path}')

if __name__ == '__main__':
    main()