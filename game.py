import pygame
import requests
import math
import random
import threading
import time

pygame.init()

W, H = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Neuromorphic NPC System")
clock = pygame.time.Clock()
font       = pygame.font.SysFont("Arial", 16)
font_med   = pygame.font.SysFont("Arial", 20)
font_big   = pygame.font.SysFont("Arial", 28, bold=True)
font_title = pygame.font.SysFont("Arial", 42, bold=True)

WHITE  = (255, 255, 255)
BLACK  = (15,  15,  15)
RED    = (220, 60,  60)
GREEN  = (60,  200, 100)
BLUE   = (60,  120, 220)
GRAY   = (80,  80,  80)
YELLOW = (240, 200, 50)
ORANGE = (240, 130, 40)
PURPLE = (150, 80,  200)
CYAN   = (50,  220, 220)
DARK   = (30,  30,  30)

STATE_MENU    = "menu"
STATE_PLAYING = "playing"
STATE_WIN     = "win"
STATE_DEAD    = "dead"

KILL_GOAL     = 10
MAX_DEATHS    = 2
MAX_BULLETS   = 100
BONUS_BULLETS = 50

# ══════════════════════════════════════════════
#  PLAYER
# ══════════════════════════════════════════════
class Player:
    def __init__(self):
        self.x, self.y     = W // 2, H // 2
        self.speed         = 4
        self.hp            = 100
        self.max_hp        = 100
        self.radius        = 14
        self.shots         = 0
        self.hits          = 0
        self.deaths        = 0
        self.kills         = 0
        self.avg_speed     = 0
        self.last_reaction = time.time()
        self.ammo          = MAX_BULLETS
        self.bonus_ammo    = BONUS_BULLETS
        self.bonus_claimed = False

    def move(self, keys):
        px, py = self.x, self.y
        if keys[pygame.K_w] or keys[pygame.K_UP]:    self.y -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  self.y += self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  self.x -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.x += self.speed
        self.x = max(self.radius, min(W - self.radius, self.x))
        self.y = max(self.radius, min(H - self.radius, self.y))
        self.avg_speed = math.hypot(self.x - px, self.y - py)

    def draw(self):
        pygame.draw.circle(screen, (30, 80, 160), (self.x, self.y), self.radius + 5)
        pygame.draw.circle(screen, BLUE,  (self.x, self.y), self.radius)
        pygame.draw.circle(screen, WHITE, (self.x, self.y), self.radius, 2)
        bw = 60
        pygame.draw.rect(screen, RED,   (self.x - 30, self.y - 28, bw, 6))
        pygame.draw.rect(screen, GREEN, (self.x - 30, self.y - 28,
                                         int(bw * self.hp / self.max_hp), 6))

    def shoot(self, angle, bullets):
        total = self.ammo + (self.bonus_ammo if self.bonus_claimed else 0)
        if total <= 0:
            return False
        bullets.append(Bullet(self.x, self.y,
                              math.cos(angle) * 7,
                              math.sin(angle) * 7,
                              YELLOW, 20))
        self.shots += 1
        self.last_reaction = time.time()
        if self.ammo > 0:
            self.ammo -= 1
        elif self.bonus_claimed and self.bonus_ammo > 0:
            self.bonus_ammo -= 1
        return True

    def claim_bonus(self):
        if not self.bonus_claimed:
            self.bonus_claimed = True
            return True
        return False

    def respawn(self):
        self.x, self.y = W // 2, H // 2
        self.hp = self.max_hp
        self.deaths += 1

    def total_ammo(self):
        return self.ammo + (self.bonus_ammo if self.bonus_claimed else 0)

# ══════════════════════════════════════════════
#  BULLET
# ══════════════════════════════════════════════
class Bullet:
    def __init__(self, x, y, dx, dy, color, dmg):
        self.x, self.y  = float(x), float(y)
        self.dx, self.dy = dx, dy
        self.color  = color
        self.dmg    = dmg
        self.active = True

    def update(self):
        self.x += self.dx
        self.y += self.dy
        if not (0 < self.x < W and 0 < self.y < H):
            self.active = False

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 5)

# ══════════════════════════════════════════════
#  NPC
# ══════════════════════════════════════════════
class NPC:
    def __init__(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":      self.x, self.y = random.randint(60, W-60), 60
        elif side == "bottom": self.x, self.y = random.randint(60, W-60), H-60
        elif side == "left":   self.x, self.y = 60, random.randint(60, H-60)
        else:                  self.x, self.y = W-60, random.randint(60, H-60)
        self.radius       = 16
        self.hp           = 80
        self.max_hp       = 80
        self.speed        = 1.5
        self.aggression   = 0.3
        self.attack_rate  = 0.5
        self.vision_range = 150
        self.prediction   = 0.0
        self.shoot_timer  = 0
        self.state        = "patrol"
        self.patrol_angle = random.uniform(0, 360)
        self._prev_px     = W // 2
        self._prev_py     = H // 2

    def apply_params(self, params):
        self.speed        = params.get("speed",        self.speed)
        self.aggression   = params.get("aggression",   self.aggression)
        self.attack_rate  = params.get("attack_rate",  self.attack_rate)
        self.vision_range = params.get("vision_range", self.vision_range)
        self.prediction   = params.get("prediction",   self.prediction)

    def update(self, player, bullets):
        dist = math.hypot(player.x - self.x, player.y - self.y)
        self.state = "chase" if dist < self.vision_range else "patrol"
        if self.state == "chase":
            tx = player.x + (player.x - self._prev_px) * self.prediction * 8
            ty = player.y + (player.y - self._prev_py) * self.prediction * 8
            angle = math.atan2(ty - self.y, tx - self.x)
            self.x += math.cos(angle) * self.speed
            self.y += math.sin(angle) * self.speed
            self.shoot_timer += self.attack_rate
            if self.shoot_timer >= 60:
                self.shoot_timer = 0
                spd = 4 + self.aggression * 3
                bullets.append(Bullet(self.x, self.y,
                                      math.cos(angle) * spd,
                                      math.sin(angle) * spd,
                                      ORANGE, 8))
        else:
            self.patrol_angle += 0.5
            self.x += math.cos(math.radians(self.patrol_angle)) * 1.2
            self.y += math.sin(math.radians(self.patrol_angle)) * 0.6
        self._prev_px = player.x
        self._prev_py = player.y
        self.x = max(self.radius, min(W - self.radius, self.x))
        self.y = max(self.radius, min(H - self.radius, self.y))

    def draw(self, difficulty):
        r = int(80  + difficulty * 170)
        g = int(200 - difficulty * 160)
        color = (r, g, 60)
        pygame.draw.circle(screen, (r//3, g//3, 10), (int(self.x), int(self.y)), self.radius + 4)
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        if self.state == "chase":
            pygame.draw.circle(screen, (255, 80, 30),
                               (int(self.x), int(self.y)), int(self.vision_range), 1)
        bw = 50
        pygame.draw.rect(screen, RED,   (self.x - 25, self.y - 30, bw, 5))
        pygame.draw.rect(screen, GREEN, (self.x - 25, self.y - 30,
                                         int(bw * self.hp / self.max_hp), 5))

    def respawn(self):
        self.__init__()

# ══════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════
def draw_menu():
    screen.fill(BLACK)
    for gx in range(0, W, 50):
        pygame.draw.line(screen, (25, 25, 25), (gx, 0), (gx, H))
    for gy in range(0, H, 50):
        pygame.draw.line(screen, (25, 25, 25), (0, gy), (W, gy))

    title = font_title.render("NEUROMORPHIC NPC", True, CYAN)
    sub   = font_big.render("The AI that learns YOU", True, PURPLE)
    screen.blit(title, (W//2 - title.get_width()//2, 30))
    screen.blit(sub,   (W//2 - sub.get_width()//2,  82))
    pygame.draw.line(screen, GRAY, (80, 120), (W-80, 120), 1)

    box_x, box_w = 80, W - 160
    pygame.draw.rect(screen, DARK, (box_x, 128, box_w, H - 196), border_radius=12)
    pygame.draw.rect(screen, GRAY, (box_x, 128, box_w, H - 196), 1, border_radius=12)
    
    sections = [
        # (header, header_color, [list of body lines in (text, color)])
        (
            "YOUR GOAL",
            CYAN,
            [
                (f"You are the BLUE circle. Kill {KILL_GOAL} glowing enemies to WIN.", WHITE),
                (f"You only get {MAX_BULLETS} bullets and {MAX_DEATHS} lives. Use them wisely!", ORANGE),
            ]
        ),
        (
            "HOW TO MOVE",
            CYAN,
            [
                ("Use  W  A  S  D  keys  (or Arrow Keys)  to move around the screen.", WHITE),
            ]
        ),
        (
            "HOW TO SHOOT",
            CYAN,
            [
                ("Move your mouse so the YELLOW crosshair (+) points at an enemy.", WHITE),
                ("Press  SPACEBAR  to fire a bullet in that direction.", GREEN),
                ("Watch the yellow aim line from your player — it shows where you will shoot!", YELLOW),
            ]
        ),
        (
            "BONUS AMMO",
            CYAN,
            [
                ("Press  R  once at any time to instantly get 50 extra bullets.", YELLOW),
            ]
        ),
        (
            "HOW TO LOSE",
            RED,
            [
                (f"Lose all {MAX_DEATHS} lives  →  Game Over.", ORANGE),
                ("Run out of bullets with enemies still alive  →  Game Over.", ORANGE),
                ("Enemies fire ORANGE bullets — dodge them or lose HP!", WHITE),
            ]
        ),
        (
            "THE AI (why this game is special)",
            PURPLE,
            [
                ("Every 5 seconds the enemies watch how you play and ADAPT.", WHITE),
                ("Kill fast + good aim  →  enemies get faster and more aggressive.", RED),
                ("Struggling a lot     →  enemies slow down so you can recover.", GREEN),
            ]
        ),
    ]

    y = 140
    for header, hcolor, body_lines in sections:
        h = font_med.render(f"  {header}", True, hcolor)
        screen.blit(h, (box_x + 10, y))
        y += 22
        for text, color in body_lines:
            t = font.render(f"      {text}", True, color)
            screen.blit(t, (box_x + 10, y))
            y += 17
        y += 5

    btn_w, btn_h = 240, 46
    btn_x = W//2 - btn_w//2
    btn_y = H - 56
    pygame.draw.rect(screen, GREEN, (btn_x, btn_y, btn_w, btn_h), border_radius=10)
    start = font_big.render("▶  START GAME", True, BLACK)
    screen.blit(start, (btn_x + btn_w//2 - start.get_width()//2,
                         btn_y + btn_h//2 - start.get_height()//2))
    return pygame.Rect(btn_x, btn_y, btn_w, btn_h)


def draw_end_screen(player, elapsed, won):
    screen.fill(BLACK)
    if won:
        t1 = font_title.render("YOU WIN!", True, YELLOW)
        t2 = font_big.render(f"You eliminated all {KILL_GOAL} enemies!", True, GREEN)
    else:
        t1 = font_title.render("GAME OVER", True, RED)
        if player.total_ammo() <= 0:
            t2 = font_big.render("You ran out of bullets!", True, ORANGE)
        else:
            t2 = font_big.render(f"You ran out of lives!", True, ORANGE)

    t3 = font_med.render(
        f"Time: {int(elapsed)}s   |   Kills: {player.kills}/{KILL_GOAL}"
        f"   |   Deaths: {player.deaths}   |   Accuracy: {int(player.hits/max(1,player.shots)*100)}%",
        True, WHITE)
    t4 = font_med.render("Press R to play again   |   ESC to quit", True, GRAY)

    screen.blit(t1, (W//2 - t1.get_width()//2, 150))
    screen.blit(t2, (W//2 - t2.get_width()//2, 220))
    screen.blit(t3, (W//2 - t3.get_width()//2, 290))
    screen.blit(t4, (W//2 - t4.get_width()//2, 370))


def draw_hud(player, npc_params, difficulty):
    d = difficulty

    # NPC intelligence bar
    pygame.draw.rect(screen, GRAY,  (20, 20, 200, 18), border_radius=6)
    ic = (int(60+d*190), int(200-d*180), 60)
    pygame.draw.rect(screen, ic,    (20, 20, int(200*d), 18), border_radius=6)
    pygame.draw.rect(screen, WHITE, (20, 20, 200, 18), 1, border_radius=6)
    screen.blit(font.render(f"NPC Intelligence: {int(d*100)}%", True, WHITE), (20, 40))

    # Kill progress bar
    pygame.draw.rect(screen, GRAY,   (20, 58, 200, 14), border_radius=4)
    pygame.draw.rect(screen, YELLOW, (20, 58,
                                      int(200 * min(player.kills, KILL_GOAL) / KILL_GOAL), 14),
                     border_radius=4)
    pygame.draw.rect(screen, WHITE,  (20, 58, 200, 14), 1, border_radius=4)
    screen.blit(font.render(f"Kills: {player.kills} / {KILL_GOAL}", True, YELLOW), (20, 75))

    # Ammo bar
    total     = player.total_ammo()
    max_total = MAX_BULLETS + (BONUS_BULLETS if player.bonus_claimed else 0)
    ac = GREEN if total > 40 else YELLOW if total > 15 else RED
    pygame.draw.rect(screen, GRAY, (20, 93, 200, 14), border_radius=4)
    pygame.draw.rect(screen, ac,   (20, 93, int(200 * total / max(1, max_total)), 14), border_radius=4)
    pygame.draw.rect(screen, WHITE,(20, 93, 200, 14), 1, border_radius=4)
    bonus_txt = f"+{player.bonus_ammo} bonus active" if player.bonus_claimed else "Press R for +50 bonus"
    screen.blit(font.render(f"Ammo: {total}   {bonus_txt}", True, ac), (20, 110))

    # Lives
    lives_left = MAX_DEATHS - player.deaths
    lc = GREEN if lives_left > 1 else RED
    screen.blit(font.render(f"Lives left: {lives_left} / {MAX_DEATHS}", True, lc), (20, 128))

    # Difficulty mode
    if d < 0.35:   mode, mc = "Easy",     GREEN
    elif d < 0.65: mode, mc = "Adapting", YELLOW
    elif d < 0.85: mode, mc = "Hard",     ORANGE
    else:          mode, mc = "MAX",       RED
    screen.blit(font_big.render(mode, True, mc), (20, 148))

    # Stats
    acc = player.hits / max(1, player.shots)
    for i, s in enumerate([
        f"HP: {int(player.hp)}",
        f"Accuracy: {int(acc*100)}%",
        f"NPC Speed: {npc_params.get('speed', 0):.1f}",
        f"Aggression: {int(npc_params.get('aggression', 0)*100)}%",
    ]):
        screen.blit(font.render(s, True, WHITE), (20, 185 + i * 20))

    # Bottom reminder
    ctrl = font.render(
        "WASD: Move  |  SPACE: Shoot toward cursor  |  R: Claim +50 bullets  |  ESC: Quit",
        True, GRAY)
    screen.blit(ctrl, (W//2 - ctrl.get_width()//2, H - 24))


# ══════════════════════════════════════════════
#  API
# ══════════════════════════════════════════════
npc_params         = {}
current_difficulty = 0.3

def send_to_api(data):
    global npc_params, current_difficulty
    try:
        r = requests.post("http://localhost:5000/update", json=data, timeout=2)
        if r.status_code == 200:
            npc_params         = r.json()
            current_difficulty = npc_params.get("difficulty", 0.3)
    except:
        pass

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def reset_game():
    return Player(), [NPC(), NPC()], [], time.time()

def main():
    global npc_params, current_difficulty

    state  = STATE_MENU
    player, enemies, bullets, start_time = reset_game()
    end_time    = None
    last_api    = time.time()
    reaction_t  = 500
    learn_flash = 0
    bonus_flash = 0
    won         = False
    btn_rect    = None

    pygame.mouse.set_visible(False)

    running = True
    while running:
        clock.tick(60)

        # ── MENU ──
        if state == STATE_MENU:
            pygame.mouse.set_visible(True)
            btn_rect = draw_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: running = False
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        player, enemies, bullets, start_time = reset_game()
                        state = STATE_PLAYING
                        pygame.mouse.set_visible(False)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btn_rect and btn_rect.collidepoint(event.pos):
                        player, enemies, bullets, start_time = reset_game()
                        state = STATE_PLAYING
                        pygame.mouse.set_visible(False)
            pygame.display.flip()
            continue

        # ── END SCREEN ──
        if state in (STATE_WIN, STATE_DEAD):
            pygame.mouse.set_visible(True)
            draw_end_screen(player, (end_time or time.time()) - start_time, won)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: running = False
                    if event.key == pygame.K_r:
                        npc_params = {}
                        current_difficulty = 0.3
                        player, enemies, bullets, start_time = reset_game()
                        end_time = None
                        won = False
                        state = STATE_PLAYING
                        pygame.mouse.set_visible(False)
            pygame.display.flip()
            continue

        # ── PLAYING ──
        screen.fill(BLACK)
        for gx in range(0, W, 50):
            pygame.draw.line(screen, (25, 25, 25), (gx, 0), (gx, H))
        for gy in range(0, H, 50):
            pygame.draw.line(screen, (25, 25, 25), (0, gy), (W, gy))

        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Claim bonus ammo
                elif event.key == pygame.K_r:
                    if player.claim_bonus():
                        bonus_flash = 120

                # SPACEBAR — shoot toward cursor
                elif event.key == pygame.K_SPACE:
                    mx, my = pygame.mouse.get_pos()
                    angle  = math.atan2(my - player.y, mx - player.x)
                    player.shoot(angle, bullets)
                    reaction_t = int((time.time() - player.last_reaction) * 1000)

        player.move(keys)
        player.draw()

        # Crosshair and aim line
        mx, my = pygame.mouse.get_pos()
        aim_angle = math.atan2(my - player.y, mx - player.x)
        ax = player.x + math.cos(aim_angle) * 40
        ay = player.y + math.sin(aim_angle) * 40
        pygame.draw.line(screen, YELLOW, (player.x, player.y), (int(ax), int(ay)), 2)
        pygame.draw.circle(screen, YELLOW, (int(ax), int(ay)), 4)
        pygame.draw.circle(screen, YELLOW, (mx, my), 10, 2)
        pygame.draw.line(screen, YELLOW, (mx-14, my), (mx+14, my), 1)
        pygame.draw.line(screen, YELLOW, (mx, my-14), (mx, my+14), 1)

        # Enemies
        for npc in enemies:
            if npc_params: npc.apply_params(npc_params)
            npc.update(player, bullets)
            npc.draw(current_difficulty)
            if math.hypot(player.x - npc.x, player.y - npc.y) < player.radius + npc.radius:
                player.hp -= 0.3
                if player.hp <= 0:
                    player.respawn()

        # Bullets
        for b in bullets[:]:
            b.update()
            b.draw()
            if not b.active:
                bullets.remove(b)
                continue
            for npc in enemies:
                if b.color == YELLOW and math.hypot(b.x - npc.x, b.y - npc.y) < npc.radius:
                    npc.hp -= b.dmg
                    b.active = False
                    player.hits += 1
                    if npc.hp <= 0:
                        player.kills += 1
                        npc.respawn()
                    break
            if b.color == ORANGE and math.hypot(b.x - player.x, b.y - player.y) < player.radius:
                player.hp -= b.dmg
                b.active = False
                if player.hp <= 0:
                    player.respawn()

        # ── End conditions ──
        if player.kills >= KILL_GOAL:
            won      = True
            end_time = time.time()
            state    = STATE_WIN
        elif player.deaths >= MAX_DEATHS:
            won      = False
            end_time = time.time()
            state    = STATE_DEAD
        elif player.total_ammo() <= 0 and not any(b.color == YELLOW and b.active for b in bullets):
            won      = False
            end_time = time.time()
            state    = STATE_DEAD

        # API update every 5s
        if time.time() - last_api > 5:
            last_api = time.time()
            t = threading.Thread(target=send_to_api, args=({
                "reaction_time_ms": reaction_t,
                "hit_accuracy":     player.hits / max(1, player.shots),
                "avg_speed":        player.avg_speed,
                "death_count":      player.deaths,
            },))
            t.daemon = True
            t.start()
            learn_flash = 90

        if learn_flash > 0:
            learn_flash -= 1
            screen.blit(font.render("NPC Learning...", True, PURPLE), (W - 190, 20))

        if bonus_flash > 0:
            bonus_flash -= 1
            screen.blit(font_med.render("+50 BONUS BULLETS CLAIMED!", True, YELLOW),
                        (W//2 - 160, H//2 - 20))

        draw_hud(player, npc_params, current_difficulty)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()