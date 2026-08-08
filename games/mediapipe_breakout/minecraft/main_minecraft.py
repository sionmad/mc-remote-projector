import cv2
import mediapipe as mp
import numpy as np
import os
import time

try:
    from handchecksamples.mediapipe_breakout.minecraft.stages_minecraft import STAGE_1
except ModuleNotFoundError:
    from stages_minecraft import STAGE_1

# =====================
# 画面設定
# =====================
WIDTH, HEIGHT = 800, 600
PIXEL_SCALE = 6

# =====================
# Minecraft Remote API
# =====================
MC_REMOTE_ENABLE = os.environ.get("MC_REMOTE_ENABLE", "0") == "1"
MC_REMOTE_HOST = os.environ.get("MC_REMOTE_HOST", "mc-remote.xgames.jp")


def env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def env_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


MC_REMOTE_PORT = env_int("MC_REMOTE_PORT", 25575)
MC_REMOTE_ORIGIN_X = env_int("MC_REMOTE_ORIGIN_X", 1000)
MC_REMOTE_ORIGIN_Y = env_int("MC_REMOTE_ORIGIN_Y", 100)
MC_REMOTE_ORIGIN_Z = env_int("MC_REMOTE_ORIGIN_Z", 1000)
MC_REMOTE_PLAYER_NAME = os.environ.get(
    "MC_REMOTE_PLAYER_NAME",
    os.environ.get("MINECRAFT_PLAYER_NAME", os.environ.get("USERNAME", "")),
)
MC_REMOTE_WIDTH = env_int("MC_REMOTE_WIDTH", 64)
MC_REMOTE_HEIGHT = env_int("MC_REMOTE_HEIGHT", 48)
MC_REMOTE_SYNC_INTERVAL = max(0.05, env_float("MC_REMOTE_SYNC_INTERVAL", 0.15))
MC_REMOTE_CLEAR_ON_EXIT = os.environ.get("MC_REMOTE_CLEAR_ON_EXIT", "0") == "1"

# =====================
# パドル
# =====================
PADDLE_W = 120
PADDLE_H = 15
PADDLE_Y = HEIGHT - 40

# =====================
# ボール
# =====================
BALL_R = 8
BALL_SPEED = 5

# =====================
# MediaPipe
# =====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# =====================
# ステージAPI
# =====================
def load_stage(stage):
    blocks = []
    bw, bh = stage["block_size"]
    pad = stage["padding"]
    ox, oy = stage["offset"]

    for ry, row in enumerate(stage["layout"]):
        for rx, ch in enumerate(row):
            info = stage["block_types"].get(ch)
            if info is None:
                continue

            blocks.append({
                "x": ox + rx * (bw + pad),
                "y": oy + ry * (bh + pad),
                "w": bw,
                "h": bh,
                "hp": info["hp"],
                "color": info["color"],
                "effect": info.get("effect")
            })
    return blocks

# =====================
# ボール効果API
# =====================
def apply_block_effect(effect):
    global ball_vx, ball_vy

    if effect == "speed_up":
        ball_vx *= 1.2
        ball_vy *= 1.2
    elif effect == "slow_down":
        ball_vx *= 0.8
        ball_vy *= 0.8

# =====================
# ゲーム状態描画
# =====================
def draw_gameover(frame):
    cv2.putText(frame, "GAME OVER",
                (WIDTH // 2 - 180, HEIGHT // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.0, (0, 0, 255), 5)
    cv2.putText(frame, "Press R to Restart",
                (WIDTH // 2 - 180, HEIGHT // 2 + 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2)

def draw_clear(frame):
    cv2.putText(frame, "GAME CLEAR!!!",
                (WIDTH // 2 - 200, HEIGHT // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.0, (0, 255, 0), 5)
    cv2.putText(frame, "Press R to Restart",
                (WIDTH // 2 - 180, HEIGHT // 2 + 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2)


def pixelate_frame(frame, scale):
    small_w = max(1, WIDTH // scale)
    small_h = max(1, HEIGHT // scale)
    small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)


mc = None
mc_block = None
mc_prev = None
mc_palette = []
mc_color_cache = {}
mc_last_sync = 0.0
mc_remote_active = False


def _build_mc_palette():
    return [
        ((0, 0, 0), getattr(mc_block, "BLACK_CONCRETE", "black_concrete")),
        ((255, 255, 255), getattr(mc_block, "WHITE_CONCRETE", "white_concrete")),
        ((0, 255, 255), getattr(mc_block, "YELLOW_CONCRETE", "yellow_concrete")),
        ((0, 0, 255), getattr(mc_block, "RED_CONCRETE", "red_concrete")),
        ((0, 255, 0), getattr(mc_block, "LIME_CONCRETE", "lime_concrete")),
        ((0, 120, 255), getattr(mc_block, "ORANGE_CONCRETE", "orange_concrete")),
        ((0, 60, 200), getattr(mc_block, "BLUE_CONCRETE", "blue_concrete")),
        ((255, 200, 0), getattr(mc_block, "LIGHT_BLUE_CONCRETE", "light_blue_concrete")),
    ]


def _bgr_to_block_id(bgr):
    key = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
    cached = mc_color_cache.get(key)
    if cached is not None:
        return cached

    best_block = mc_palette[0][1]
    best_dist = 10**9
    for color, block_id in mc_palette:
        db = key[0] - color[0]
        dg = key[1] - color[1]
        dr = key[2] - color[2]
        dist = db * db + dg * dg + dr * dr
        if dist < best_dist:
            best_dist = dist
            best_block = block_id

    mc_color_cache[key] = best_block
    return best_block


def init_mc_remote():
    global mc, mc_block, mc_prev, mc_palette, mc_remote_active

    if not MC_REMOTE_ENABLE:
        return

    try:
        from mc_remote.minecraft import Minecraft
        from mc_remote import block_id as block_id
    except ModuleNotFoundError:
        print("[MC_REMOTE] minecraft-remote-api is not installed.")
        print("[MC_REMOTE] Install with: python -m pip install minecraft-remote-api")
        return

    if not MC_REMOTE_PLAYER_NAME:
        print("[MC_REMOTE] player name is empty. Set MC_REMOTE_PLAYER_NAME.")
        return

    try:
        mc = Minecraft.create(address=MC_REMOTE_HOST, port=MC_REMOTE_PORT)
        # mc-remote requires selecting an in-game player first.
        mc.setPlayer(
            MC_REMOTE_PLAYER_NAME,
            MC_REMOTE_ORIGIN_X,
            0,
            MC_REMOTE_ORIGIN_Z,
        )
        mc_block = block_id
        mc_palette = _build_mc_palette()
        mc_prev = np.full((MC_REMOTE_HEIGHT, MC_REMOTE_WIDTH), "", dtype=object)
        mc_remote_active = True

        black = getattr(mc_block, "BLACK_CONCRETE", "black_concrete")
        mc.setBlocks(
            0,
            MC_REMOTE_ORIGIN_Y - (MC_REMOTE_HEIGHT - 1),
            0,
            MC_REMOTE_WIDTH - 1,
            MC_REMOTE_ORIGIN_Y,
            0,
            black,
        )
        mc.postToChat(
            f"[Hand Block Breaker] connected as {MC_REMOTE_PLAYER_NAME}"
        )
        print(
            "[MC_REMOTE] connected "
            f"host={MC_REMOTE_HOST}:{MC_REMOTE_PORT} player={MC_REMOTE_PLAYER_NAME} "
            f"origin=({MC_REMOTE_ORIGIN_X},0,{MC_REMOTE_ORIGIN_Z})"
        )
    except Exception as e:
        mc_remote_active = False
        print(f"[MC_REMOTE] connection failed: {e}")
    except SystemExit as e:
        mc_remote_active = False
        print(f"[MC_REMOTE] setup failed: {e}")


def sync_mc_remote(canvas):
    global mc_last_sync, mc_remote_active

    if not mc_remote_active:
        return

    now = time.time()
    if now - mc_last_sync < MC_REMOTE_SYNC_INTERVAL:
        return
    mc_last_sync = now

    small = cv2.resize(
        canvas,
        (MC_REMOTE_WIDTH, MC_REMOTE_HEIGHT),
        interpolation=cv2.INTER_NEAREST
    )

    try:
        for y in range(MC_REMOTE_HEIGHT):
            wy = MC_REMOTE_ORIGIN_Y - y
            for x in range(MC_REMOTE_WIDTH):
                block_id = _bgr_to_block_id(small[y, x])
                if mc_prev[y, x] != block_id:
                    mc.setBlock(
                        x,
                        wy,
                        0,
                        block_id
                    )
                    mc_prev[y, x] = block_id
    except Exception as e:
        mc_remote_active = False
        print(f"[MC_REMOTE] sync stopped: {e}")


def close_mc_remote():
    if mc is None:
        return

    try:
        if MC_REMOTE_CLEAR_ON_EXIT and mc_remote_active:
            air = getattr(mc_block, "AIR", "air")
            mc.setBlocks(
                0,
                MC_REMOTE_ORIGIN_Y - (MC_REMOTE_HEIGHT - 1),
                0,
                MC_REMOTE_WIDTH - 1,
                MC_REMOTE_ORIGIN_Y,
                0,
                air,
            )
        mc.close()
    except Exception:
        pass

# =====================
# リセット
# =====================
def reset_game():
    global blocks, ball_x, ball_y, ball_vx, ball_vy, game_state
    blocks = load_stage(STAGE_1)
    ball_x = WIDTH // 2
    ball_y = HEIGHT // 2
    ball_vx = BALL_SPEED
    ball_vy = -BALL_SPEED
    game_state = "PLAY"

# =====================
# 初期化
# =====================
blocks = load_stage(STAGE_1)

paddle_x = WIDTH // 2 - PADDLE_W // 2

ball_x = WIDTH // 2
ball_y = HEIGHT // 2
ball_vx = BALL_SPEED
ball_vy = -BALL_SPEED

game_state = "PLAY"  # PLAY / GAMEOVER / CLEAR

# =====================
# カメラ
# =====================
cap = cv2.VideoCapture(0)
cv2.namedWindow("Hand Block Breaker")
cv2.resizeWindow("Hand Block Breaker", WIDTH, HEIGHT)
init_mc_remote()

# =====================
# メインループ
# =====================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (WIDTH, HEIGHT))
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    results = hands.process(rgb)

    # =====================
    # PLAY状態
    # =====================
    if game_state == "PLAY":

        # 手入力 → パドル
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0].landmark
            wrist_x = lm[mp_hands.HandLandmark.WRIST].x
            paddle_x = int(wrist_x * WIDTH - PADDLE_W / 2)
            paddle_x = max(0, min(WIDTH - PADDLE_W, paddle_x))

        # ボール移動
        ball_x += ball_vx
        ball_y += ball_vy

        # 壁反射
        if ball_x < BALL_R or ball_x > WIDTH - BALL_R:
            ball_vx *= -1
        if ball_y < BALL_R:
            ball_vy *= -1

        # パドル反射
        if (PADDLE_Y < ball_y + BALL_R < PADDLE_Y + PADDLE_H and
            paddle_x < ball_x < paddle_x + PADDLE_W):
            ball_vy *= -1
            ball_y = PADDLE_Y - BALL_R

        # ブロック衝突
        for block in blocks[:]:
            if (block["x"] < ball_x < block["x"] + block["w"] and
                block["y"] < ball_y < block["y"] + block["h"]):

                block["hp"] -= 1
                ball_vy *= -1

                if block.get("effect"):
                    apply_block_effect(block["effect"])

                if block["hp"] <= 0:
                    blocks.remove(block)
                break

        # ゲームオーバー
        if ball_y > HEIGHT:
            game_state = "GAMEOVER"

        # ゲームクリア
        if len(blocks) == 0:
            game_state = "CLEAR"

    # =====================
    # 描画
    # =====================
    if game_state == "PLAY":
        cv2.rectangle(
            canvas,
            (paddle_x, PADDLE_Y),
            (paddle_x + PADDLE_W, PADDLE_Y + PADDLE_H),
            (255, 255, 255),
            -1
        )

        cv2.circle(
            canvas,
            (int(ball_x), int(ball_y)),
            BALL_R,
            (0, 255, 255),
            -1
        )

        for block in blocks:
            cv2.rectangle(
                canvas,
                (block["x"], block["y"]),
                (block["x"] + block["w"], block["y"] + block["h"]),
                block["color"],
                -1
            )

    elif game_state == "GAMEOVER":
        draw_gameover(canvas)

    elif game_state == "CLEAR":
        draw_clear(canvas)

    sync_mc_remote(canvas)
    pixel_frame = pixelate_frame(canvas, PIXEL_SCALE)
    cv2.imshow("Hand Block Breaker", pixel_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    if key == ord("r") and game_state != "PLAY":
        reset_game()

# =====================
# 終了
# =====================
cap.release()
cv2.destroyAllWindows()
hands.close()
close_mc_remote()
