import argparse
import json
from pathlib import Path

from app.ocr_reader import read_player_image


def main():
    parser = argparse.ArgumentParser(description="OCR simples para ler level e nome de jogador em imagem.")
    parser.add_argument("--image", "-i", default="exemplos/player.png", help="Caminho da imagem")
    parser.add_argument("--scale", type=int, default=4, help="Fator de aumento da imagem")
    parser.add_argument("--threshold", type=int, default=145, help="Valor de threshold 0-255")
    parser.add_argument("--debug", action="store_true", help="Salvar imagem preprocessada em saida/debug_preprocess.png")
    args = parser.parse_args()

    result = read_player_image(
        args.image,
        scale=args.scale,
        threshold_value=args.threshold,
        save_debug=args.debug,
    )

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.debug:
        print("Debug salvo em: saida/debug_preprocess.png")


if __name__ == "__main__":
    main()
