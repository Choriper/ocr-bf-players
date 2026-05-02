import os
import re
import shutil
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import pytesseract


def configure_tesseract():
    """
    No Docker/Linux normalmente o tesseract fica no PATH.
    No Windows local, tenta achar automaticamente também.
    """
    env_path = os.getenv("TESSERACT_CMD")

    possible_paths = [
        env_path,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in possible_paths:
        if path and os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return


configure_tesseract()


def ensure_bgr(img):
    """
    Garante imagem BGR com 3 canais.
    PNG pode vir com alpha/BGRA.
    """
    if img is None:
        return None

    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    return img


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    # agora mantém [ ] também
    text = re.sub(r"[^A-Za-z0-9_\-\[\]\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def prepare_name_variants(crop, scale: int = 10):
    """
    Prepara o nome para OCR em fundos diferentes:
    cinza, verde, azul, preto, etc.
    O foco é destacar texto claro/branco.
    """
    crop = ensure_bgr(crop)

    big = cv2.resize(
        crop,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8),
    )

    gray_contrast = clahe.apply(gray)

    variants = []

    # 1. cinza com contraste
    variants.append(("name_gray", gray_contrast))

    # 2. threshold para texto claro
    _, white_text = cv2.threshold(
        gray_contrast,
        135,
        255,
        cv2.THRESH_BINARY,
    )
    variants.append(("name_white_text", white_text))

    # 3. invertido
    variants.append(("name_white_text_inv", cv2.bitwise_not(white_text)))

    # 4. HSV: pega texto claro/branco mesmo em fundo verde/azul/vermelho
    hsv = cv2.cvtColor(big, cv2.COLOR_BGR2HSV)

    # baixa saturação + alto brilho costuma pegar branco/cinza claro
    lower_white = np.array([0, 0, 120])
    upper_white = np.array([179, 100, 255])

    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    variants.append(("name_hsv_white", mask_white))
    variants.append(("name_hsv_white_inv", cv2.bitwise_not(mask_white)))

    ready_variants = []

    for name, img in variants:
        img = cv2.copyMakeBorder(
            img,
            20,
            20,
            20,
            20,
            cv2.BORDER_CONSTANT,
            value=0,
        )

        ready_variants.append((name, img))

    return ready_variants

def ocr_image(img, whitelist: str, psm: int = 7) -> str:
    config = (
        f"--oem 3 --psm {psm} "
        f"-c tessedit_char_whitelist={whitelist}"
    )

    text = pytesseract.image_to_string(
        img,
        lang="eng",
        config=config,
    )

    return clean_text(text)


def prepare_crop(crop, scale: int = 10):
    crop = ensure_bgr(crop)

    big = cv2.resize(
        crop,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8),
    )
    gray = clahe.apply(gray)

    gray = cv2.copyMakeBorder(
        gray,
        20,
        20,
        20,
        20,
        cv2.BORDER_CONSTANT,
        value=0,
    )

    return gray


def find_level_box(img):
    """
    Tenta achar automaticamente a área do level.

    Suporta:
    - caixa clara com número escuro
    - caixa escura/preta com número branco
    """
    img = ensure_bgr(img)

    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # O level quase sempre fica no começo da imagem
    left_w = int(w * 0.45)
    left = gray[:, :left_w]

    # ==========================================================
    # 1) Tenta achar caixa clara do level
    # Ex: fundo branco/cinza com número preto
    # ==========================================================
    _, bright_mask = cv2.threshold(left, 145, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        bright_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)

        area = bw * bh
        if area <= 0:
            continue

        fill_ratio = cv2.contourArea(cnt) / area

        if (
            bw >= 18
            and bh >= 12
            and bw <= 70
            and bh <= 40
            and fill_ratio > 0.40
        ):
            candidates.append((x, y, bw, bh, area, fill_ratio))

    if candidates:
        candidates.sort(key=lambda item: item[4], reverse=True)
        x, y, bw, bh, _, _ = candidates[0]

        pad = 2

        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        return x1, y1, x2, y2

    # ==========================================================
    # 2) Tenta achar números brancos em caixa escura
    # Ex: seu caso: "64" branco no fundo preto
    # ==========================================================
    _, white_digits_mask = cv2.threshold(left, 170, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        white_digits_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    digit_boxes = []

    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)

        area = bw * bh
        if area <= 0:
            continue

        # filtra pedaços pequenos de letra/número
        if (
            bw >= 2
            and bh >= 6
            and bw <= 20
            and bh <= 25
            and x < left_w * 0.75
        ):
            digit_boxes.append((x, y, x + bw, y + bh))

    if digit_boxes:
        x1 = min(box[0] for box in digit_boxes)
        y1 = min(box[1] for box in digit_boxes)
        x2 = max(box[2] for box in digit_boxes)
        y2 = max(box[3] for box in digit_boxes)

        # aumenta para pegar a caixa inteira do level
        x1 = max(0, x1 - 7)
        y1 = max(0, y1 - 5)
        x2 = min(w, x2 + 10)
        y2 = min(h, y2 + 6)

        return x1, y1, x2, y2

    # ==========================================================
    # 3) Fallback dinâmico
    # Não usa mais valor fixo 24,15,56,37 porque quebrava imagens pequenas
    # ==========================================================
    x1 = max(0, int(w * 0.01))
    y1 = max(0, int(h * 0.05))
    x2 = min(w, int(w * 0.27))
    y2 = min(h, int(h * 0.92))

    return x1, y1, x2, y2


def choose_best_level(level_texts):
    """
    Escolhe o melhor número lido no OCR.

    Corrige caso comum:
    a borda esquerda da caixa vira número 1.
    Exemplo:
      OCR: 176
      Real: 76
    """
    candidates = []

    for text in level_texts:
        text = clean_text(text)

        for match in re.findall(r"\d{1,3}", text):
            num = int(match)

            if 0 <= num <= 500:
                candidates.append(str(num))

            # Correção comum do seu caso: 76 vira 176
            if len(match) == 3 and match.startswith("1"):
                fixed = int(match[1:])

                if 0 <= fixed <= 99:
                    candidates.append(str(fixed))

    if not candidates:
        return None

    counter = Counter(candidates)

    # Mais repetido ganha.
    # Em empate, prefere o menor texto.
    # Isso ajuda quando "176" e "76" aparecem juntos.
    best = sorted(
        counter.items(),
        key=lambda item: (item[1], -len(item[0])),
        reverse=True,
    )[0][0]

    return int(best)


def normalize_clan_ocr_text(text: str) -> str:
    text = clean_text(text)

    # Casos comuns do OCR:
    # TSTF]Peacock -> [STF]Peacock
    # ISTF]Peacock -> [STF]Peacock
    # ITSTF]Peacock -> [STF]Peacock
    text = re.sub(
        r"^[I1T]{0,2}([A-Za-z0-9_\-]{2,10})\]",
        r"[\1]",
        text,
    )

    # STFjJPeacock -> [STF]Peacock
    text = re.sub(
        r"^([A-Za-z0-9_\-]{2,10})[jJ]+([A-Za-z][A-Za-z0-9_\-]{2,})",
        r"[\1]\2",
        text,
    )

    # STF [Peacock-atomic -> [STF]Peacock-atomic
    text = re.sub(
        r"^([A-Za-z0-9_\-]{2,10})\s+\[([A-Za-z][A-Za-z0-9_\-]{2,})",
        r"[\1]\2",
        text,
    )

    # TSTF]Peacock -> [STF]Peacock
    text = re.sub(
        r"^T([A-Za-z0-9_\-]{2,10})\]",
        r"[\1]",
        text,
    )

    return text


def choose_best_name(name_texts):
    """
    Escolhe o melhor nome lido.
    Dá prioridade para nome com clan tag: [STF]Peacock-atomic
    """

    tagged_candidates = []
    plain_candidates = []

    for raw in name_texts:
        text = normalize_clan_ocr_text(raw)

        # Primeiro tenta pegar nome completo com clan tag
        tagged_matches = re.findall(
            r"\[[A-Za-z0-9_\-]{1,10}\][A-Za-z][A-Za-z0-9_\-]{2,}",
            text,
        )

        for name in tagged_matches:
            name = name.strip("_-")

            if len(name) >= 5:
                tagged_candidates.append(name)

        # Depois tenta pegar nome sem clan tag
        plain_matches = re.findall(
            r"[A-Za-z][A-Za-z0-9_\-]{2,}",
            text,
        )

        for name in plain_matches:
            name = name.strip("_-")

            # Ignora tag solta tipo STF
            if len(name) >= 4 and not re.fullmatch(r"[A-Z0-9]{2,5}", name):
                plain_candidates.append(name)

    # Se encontrou qualquer candidato com clan tag, ele ganha prioridade
    if tagged_candidates:
        counter = Counter(tagged_candidates)

        best = sorted(
            counter.items(),
            key=lambda item: (item[1], len(item[0])),
            reverse=True,
        )[0][0]

        return best

    if plain_candidates:
        counter = Counter(plain_candidates)

        best = sorted(
            counter.items(),
            key=lambda item: (item[1], len(item[0])),
            reverse=True,
        )[0][0]

        return best

    return None


def read_player_image_from_cv2(img, save_debug: bool = False) -> dict:
    img = ensure_bgr(img)

    if img is None:
        raise ValueError("Imagem inválida ou vazia.")

    h, w = img.shape[:2]

    lx1, ly1, lx2, ly2 = find_level_box(img)

    # Variações do crop do level.
    # O objetivo é remover a borda esquerda que estava virando "1".
    level_crops = [
        img[
            max(0, ly1 + 1):max(0, ly2 - 1),
            min(w, lx1 + 4):max(0, lx2 - 1),
        ],
        img[
            max(0, ly1 + 2):max(0, ly2 - 1),
            min(w, lx1 + 5):max(0, lx2 - 2),
        ],
        img[
            max(0, ly1 + 1):max(0, ly2),
            min(w, lx1 + 6):max(0, lx2),
        ],
        img[
            max(0, ly1 + 2):max(0, ly2 - 2),
            min(w, lx1 + 7):max(0, lx2 - 1),
        ],
    ]

    # Crop do nome começa depois da caixa do level
    name_x1 = min(w, lx2 + 4)
    name_y1 = max(0, ly1 - 5)
    name_x2 = max(name_x1 + 1, w - 5)
    name_y2 = min(h, ly2 + 6)

    name_crop = img[name_y1:name_y2, name_x1:name_x2]

    level_ready_list = [
        prepare_crop(crop, scale=12)
        for crop in level_crops
        if crop is not None and crop.size > 0
    ]

    name_ready_list = prepare_name_variants(name_crop, scale=10)

    if save_debug:
        debug_dir = Path("debug_ocr")
        debug_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(debug_dir / "01_original.png"), img)

        for idx, crop in enumerate(level_crops):
            if crop is not None and crop.size > 0:
                cv2.imwrite(str(debug_dir / f"02_level_crop_{idx}.png"), crop)

        cv2.imwrite(str(debug_dir / "03_name_crop.png"), name_crop)

        for idx, ready in enumerate(level_ready_list):
            cv2.imwrite(str(debug_dir / f"04_level_ready_{idx}.png"), ready)

        for idx, (variant_name, ready) in enumerate(name_ready_list):
            cv2.imwrite(str(debug_dir / f"05_{variant_name}_{idx}.png"), ready)

    level_texts = []
    name_texts = []

    for psm in [7, 8, 13]:
        for level_ready in level_ready_list:
            level_texts.append(
                ocr_image(
                    level_ready,
                    whitelist="0123456789",
                    psm=psm,
                )
            )

        for variant_name, name_ready in name_ready_list:
            name_texts.append(
                ocr_image(
                    name_ready,
                    whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-[]",
                    psm=psm,
                )
            )

    level = choose_best_level(level_texts)
    name = choose_best_name(name_texts)

    raw_text = f"{level or ''} {name or ''}".strip()
    cleaned_text = clean_text(raw_text)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "level": level,
        "name": name,
        "level_ocr_attempts": level_texts,
        "name_ocr_attempts": name_texts,
        "crop": {
            "level": [lx1, ly1, lx2, ly2],
            "name": [name_x1, name_y1, name_x2, name_y2],
        },
    }


def read_player_image(image_path: str, save_debug: bool = False) -> dict:
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    return read_player_image_from_cv2(img, save_debug=save_debug)


def read_player_image_from_bytes(
    image_bytes: bytes,
    filename: str = "image.png",
    save_debug: bool = False,
) -> dict:
    if not image_bytes:
        raise ValueError("Bytes da imagem estão vazios.")

    np_arr = np.frombuffer(image_bytes, np.uint8)

    img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise ValueError(f"Não foi possível decodificar a imagem: {filename}")

    return read_player_image_from_cv2(img, save_debug=save_debug)