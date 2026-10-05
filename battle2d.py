import pygame
import math
import random
import sqlite3
import os

pygame.init()

WIDTH, HEIGHT = 960, 640
DB_FILE = "game.db"

BG_DARK = (26, 26, 46)
BG_MID = (22, 33, 62)
BG_LIGHT = (15, 52, 96)
ACCENT = (233, 69, 96)
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (160, 160, 160)
HP_GREEN = (76, 175, 80)
HP_RED = (233, 69, 96)
PLAYER_COLOR = (80, 200, 255)
ENEMY_COLOR = (255, 80, 80)
BULLET_COLOR = (255, 230, 100)

FONT_S = pygame.font.SysFont("microsoftyahei", 16)
FONT_M = pygame.font.SysFont("microsoftyahei", 22)
FONT_L = pygame.font.SysFont("microsoftyahei", 36)


def db_add_inventory(username, item_id, item_name, count=1):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT item_count FROM inventory WHERE username=? AND item_id=?",
                (username, item_id))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE inventory SET item_count=? WHERE username=? AND item_id=?",
                    (row[0] + count, username, item_id))
    else:
        cur.execute("INSERT INTO inventory (username, item_id, item_name, item_count) VALUES (?, ?, ?, ?)",
                    (username, item_id, item_name, count))
    conn.commit()
    conn.close()


def db_save_player(username, level, exp, max_hp, atk, wins):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE users SET level=?, exp=?, max_hp=?, atk=?, wins=? WHERE username=?",
                (level, exp, max_hp, atk, wins, username))
    conn.commit()
    conn.close()


class Player:
    def __init__(self, data):
        self.x = WIDTH // 2 - 150
        self.y = HEIGHT // 2
        self.radius = 18
        self.speed = 4
        self.level = int(data.get("level", 1))
        self.max_hp = int(data.get("max_hp", 100))
        self.hp = self.max_hp
        self.atk = int(data.get("atk", 15))
        self.exp = int(data.get("exp", 0))
        self.wins = int(data.get("wins", 0))
        self.attack_cd = 0
        self.skill_cd = {1: 0, 2: 0, 3: 0, 4: 0}
        self.facing = pygame.math.Vector2(1, 0)

    def update(self, keys, dt, mouse_pos):
        dx = dy = 0
        if keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_s]:
            dy += 1
        if dx or dy:
            v = pygame.math.Vector2(dx, dy).normalize()
            self.x += v.x * self.speed
            self.y += v.y * self.speed
        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))
        if self.attack_cd > 0:
            self.attack_cd -= dt
        for k in self.skill_cd:
            if self.skill_cd[k] > 0:
                self.skill_cd[k] -= dt

    def draw(self, surface):
        pygame.draw.circle(surface, PLAYER_COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, TEXT_WHITE, (int(self.x), int(self.y)), self.radius, 2)


class Enemy:
    def __init__(self, x, y, level):
        self.x = x
        self.y = y
        self.radius = 20
        self.max_hp = 60 + level * 15
        self.hp = self.max_hp
        self.atk = 8 + level * 2
        self.speed = 1.5 + level * 0.1
        self.attack_cd = 0

    def update(self, player, dt):
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy)
        if d > 0:
            self.x += dx / d * self.speed
            self.y += dy / d * self.speed
        if self.attack_cd > 0:
            self.attack_cd -= dt

    def draw(self, surface):
        pygame.draw.circle(surface, ENEMY_COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, TEXT_WHITE, (int(self.x), int(self.y)), self.radius, 2)


class Bullet:
    def __init__(self, x, y, dx, dy, dmg, color=BULLET_COLOR, speed=10, radius=6):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.dmg = dmg
        self.color = color
        self.speed = speed
        self.radius = radius
        self.alive = True

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class DamageText:
    def __init__(self, x, y, text, color=TEXT_WHITE):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 0.8

    def update(self, dt):
        self.y -= 40 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        img = FONT_S.render(self.text, True, self.color)
        surface.blit(img, (self.x, self.y))


class Battle2D:
    def __init__(self, player_data, username):
        self.username = username
        self.player = Player(player_data)
        self.enemies = []
        self.bullets = []
        self.damage_texts = []
        self.logs = []
        self.spawn_timer = 0
        self.wave = 1
        self.battle_over = False
        self.result = None
        self.kills = 0
        self.spawn_enemy()
        self.add_log("WASD移动 鼠标瞄准 左键攻击 1/2/3/4技能")

    def add_log(self, msg):
        self.logs.append(msg)
        if len(self.logs) > 6:
            self.logs.pop(0)

    def spawn_enemy(self):
        side = random.choice(["left", "right", "top", "bottom"])
        if side == "left":
            x, y = 50, random.randint(100, HEIGHT - 100)
        elif side == "right":
            x, y = WIDTH - 50, random.randint(100, HEIGHT - 100)
        elif side == "top":
            x, y = random.randint(100, WIDTH - 100), 50
        else:
            x, y = random.randint(100, WIDTH - 100), HEIGHT - 50
        self.enemies.append(Enemy(x, y, self.player.level + self.wave - 1))

    def handle_event(self, event):
        if self.battle_over:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.player_attack()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.use_skill(1)
            elif event.key == pygame.K_2:
                self.use_skill(2)
            elif event.key == pygame.K_3:
                self.use_skill(3)
            elif event.key == pygame.K_4:
                self.use_skill(4)

    def player_attack(self):
        p = self.player
        if p.attack_cd > 0:
            return
        p.attack_cd = 0.3
        mx, my = pygame.mouse.get_pos()
        dx, dy = mx - p.x, my - p.y
        d = math.hypot(dx, dy)
        if d == 0:
            return
        dmg = max(1, random.randint(p.atk - 3, p.atk + 5))
        self.bullets.append(Bullet(p.x, p.y, dx / d, dy / d, dmg))

    def use_skill(self, key):
        p = self.player
        if p.skill_cd[key] > 0:
            self.add_log(f"技能{key}冷却中")
            return

        if key == 1:
            if p.exp < 10:
                self.add_log("经验不足")
                return
            p.exp -= 10
            p.skill_cd[1] = 1.5
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx - p.x, my - p.y
            d = math.hypot(dx, dy)
            if d == 0:
                return
            dmg = random.randint(p.atk * 2, p.atk * 3)
            self.bullets.append(Bullet(p.x, p.y, dx / d, dy / d, dmg, (255, 120, 0), 12, 10))
            self.add_log(f"重击 {dmg}")

        elif key == 2:
            if p.exp < 8:
                self.add_log("经验不足")
                return
            p.exp -= 8
            p.skill_cd[2] = 2.0
            mx, my = pygame.mouse.get_pos()
            base = math.atan2(my - p.y, mx - p.x)
            for off in [-0.25, 0, 0.25]:
                a = base + off
                dmg = random.randint(p.atk - 2, p.atk + 3)
                self.bullets.append(Bullet(p.x, p.y, math.cos(a), math.sin(a), dmg, (100, 255, 180), 11, 7))
            self.add_log("散射")

        elif key == 3:
            if p.exp < 15:
                self.add_log("经验不足")
                return
            p.exp -= 15
            p.skill_cd[3] = 3.0
            heal = random.randint(20, 35)
            p.hp = min(p.max_hp, p.hp + heal)
            self.damage_texts.append(DamageText(p.x, p.y - 30, f"+{heal}", HP_GREEN))
            self.add_log(f"回复 {heal}")

        elif key == 4:
            if p.exp < 25:
                self.add_log("经验不足")
                return
            p.exp -= 25
            p.skill_cd[4] = 5.0
            for e in self.enemies:
                d = math.hypot(e.x - p.x, e.y - p.y)
                if d < 200:
                    dmg = random.randint(p.atk * 2, p.atk * 4)
                    e.hp -= dmg
                    self.damage_texts.append(DamageText(e.x, e.y - 20, str(dmg), ACCENT))
            self.add_log("爆发")

    def update(self, keys, dt):
        if self.battle_over:
            return
        self.player.update(keys, dt, pygame.mouse.get_pos())

        for e in self.enemies:
            e.update(self.player, dt)
            d = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if d < e.radius + self.player.radius + 5 and e.attack_cd <= 0:
                dmg = max(1, random.randint(e.atk - 2, e.atk + 4))
                self.player.hp -= dmg
                self.damage_texts.append(DamageText(self.player.x, self.player.y - 30, f"-{dmg}", HP_RED))
                e.attack_cd = 1.0

        for b in self.bullets:
            b.update()
            if b.dmg > 0:
                for e in self.enemies:
                    if math.hypot(b.x - e.x, b.y - e.y) < e.radius + b.radius:
                        e.hp -= b.dmg
                        self.damage_texts.append(DamageText(e.x, e.y - 20, str(b.dmg), TEXT_WHITE))
                        b.alive = False
                        break
        self.bullets = [b for b in self.bullets if b.alive]

        dead = [e for e in self.enemies if e.hp <= 0]
        for e in dead:
            self.enemies.remove(e)
            self.kills += 1
            self.player.exp += 30
            self.player.wins += 1
            self.add_log("击败敌人 +30经验")
            self.drop_loot()
            if self.player.exp >= 100:
                self.player.exp -= 100
                self.player.level += 1
                self.player.max_hp += 20
                self.player.hp = self.player.max_hp
                self.player.atk += 5
                self.add_log(f"升级 Lv.{self.player.level}")

        self.spawn_timer += dt
        if not self.enemies and self.spawn_timer > 1.5:
            self.wave += 1
            self.spawn_timer = 0
            for _ in range(min(3, 1 + self.wave // 3)):
                self.spawn_enemy()

        self.damage_texts = [d for d in self.damage_texts if d.update(dt)]

        if self.player.hp <= 0:
            self.player.hp = 0
            self.battle_over = True
            self.result = "lose"
        elif self.wave >= 5 and not self.enemies:
            self.battle_over = True
            self.result = "win"

    def drop_loot(self):
        loot_table = [
            ("mat_core", "能量核心"),
            ("mat_chip", "机械芯片"),
            ("mat_crystal", "虚空水晶"),
            ("mat_gear", "齿轮零件"),
        ]
        if random.random() < 0.6:
            item_id, item_name = random.choice(loot_table)
            db_add_inventory(self.username, item_id, item_name, 1)
            self.add_log(f"获得 {item_name}")

    def save_and_exit(self):
        db_save_player(
            self.username,
            self.player.level,
            self.player.exp,
            self.player.max_hp,
            self.player.atk,
            self.player.wins
        )

    def draw(self, surface):
        surface.fill(BG_DARK)
        for i in range(0, WIDTH, 40):
            pygame.draw.line(surface, BG_MID, (i, 0), (i, HEIGHT))
        for j in range(0, HEIGHT, 40):
            pygame.draw.line(surface, BG_MID, (0, j), (WIDTH, j))

        for b in self.bullets:
            b.draw(surface)
        for e in self.enemies:
            e.draw(surface)
            ratio = max(0, e.hp / e.max_hp)
            pygame.draw.rect(surface, (51, 51, 51), (e.x - 30, e.y - 35, 60, 6))
            pygame.draw.rect(surface, HP_RED, (e.x - 30, e.y - 35, int(60 * ratio), 6))

        self.player.draw(surface)
        ratio = max(0, self.player.hp / self.player.max_hp)
        pygame.draw.rect(surface, (51, 51, 51),
                         (self.player.x - 30, self.player.y - 40, 60, 6))
        pygame.draw.rect(surface, HP_GREEN,
                         (self.player.x - 30, self.player.y - 40, int(60 * ratio), 6))

        for d in self.damage_texts:
            d.draw(surface)

        self.draw_hud(surface)

    def draw_hud(self, surface):
        panel = pygame.Surface((320, 130), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        surface.blit(panel, (10, 10))
        surface.blit(FONT_M.render(f"指挥官：{self.username}", True, TEXT_WHITE), (20, 18))
        surface.blit(FONT_S.render(f"等级：{self.player.level}  经验：{self.player.exp}/100", True, TEXT_GRAY), (20, 48))
        surface.blit(FONT_S.render(f"生命：{self.player.hp}/{self.player.max_hp}", True, HP_GREEN), (20, 70))
        surface.blit(FONT_S.render(f"攻击：{self.player.atk}  击杀：{self.kills}", True, TEXT_GRAY), (20, 92))
        surface.blit(FONT_M.render(f"波次：{self.wave}/5", True, ACCENT), (WIDTH - 160, 20))

        bar_y = HEIGHT - 70
        skills = [
            ("1 重击", 10, self.player.skill_cd[1]),
            ("2 散射", 8, self.player.skill_cd[2]),
            ("3 回复", 15, self.player.skill_cd[3]),
            ("4 爆发", 25, self.player.skill_cd[4]),
        ]
        for i, (name, cost, cd) in enumerate(skills):
            x = 20 + i * 160
            rect = pygame.Rect(x, bar_y, 140, 50)
            pygame.draw.rect(surface, BG_MID, rect)
            pygame.draw.rect(surface, ACCENT if cd <= 0 else TEXT_GRAY, rect, 2)
            surface.blit(FONT_S.render(name, True, TEXT_WHITE), (x + 10, bar_y + 6))
            surface.blit(FONT_S.render(f"消耗:{cost}", True, TEXT_GRAY), (x + 10, bar_y + 26))
            if cd > 0:
                overlay = pygame.Surface((140, 50), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                surface.blit(overlay, (x, bar_y))
                surface.blit(FONT_S.render(f"{cd:.1f}s", True, TEXT_WHITE), (x + 50, bar_y + 16))

        log_y = HEIGHT - 180
        for i, msg in enumerate(self.logs):
            surface.blit(FONT_S.render(msg, True, TEXT_GRAY), (20, log_y + i * 20))

        if self.battle_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            surface.blit(ov, (0, 0))
            text = FONT_L.render("战斗胜利" if self.result == "win" else "战斗失败",
                                 True, HP_GREEN if self.result == "win" else HP_RED)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 60))
            tip = FONT_M.render("按 R 返回主界面", True, TEXT_WHITE)
            surface.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT // 2 + 20))