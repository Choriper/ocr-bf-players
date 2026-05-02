@echo off
docker build -t ocr-bfv .
docker run --rm ocr-bfv python main.py --image exemplos/player.png --debug
pause
