import pygame
import sys
import os
import random
import sqlite3
import tkinter as tk
from tkinter import simpledialog

from battle2d import Battle2D

pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print("音频初始化失败：", e)

WIDTH, HEIGHT = 960, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("星海回响")
clock = pygame.time.Clock()

BG_DARK = (26, 26, 46)
BG_MID = (22, 33, 62)
BG_LIGHT = (15, 52, 96)
ACCENT = (233, 69, 96)
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (160, 160, 160)

FONT_S = pygame.font.SysFont("microsoftyahei", 16)
FONT_M = pygame.font.SysFont("microsoftyahei", 22)
FONT_L = pygame.font.SysFont("microsoftyahei", 36)
FONT_XL = pygame.font.SysFont("microsoftyahei", 56, bold=True)

ASSETS_DIR = "assets"
DB_FILE = "game.db"


# ---------------- 输入弹窗 ----------------
def ask_input(title, show=None, initial=""):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    result = simpledialog.askstring(title, title, show=show, initialvalue=initial)
    root.destroy()
    return result


# ---------------- 数据库 ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            max_hp INTEGER DEFAULT 100,
            atk INTEGER DEFAULT 15,
            wins INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_count INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def db_get_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT username, password, level, exp, max_hp, atk, wins FROM users WHERE username=?",
                (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0], "password": row[1],
            "level": row[2], "exp": row[3], "max_hp": row[4],
            "atk": row[5], "wins": row[6],
        }
    return None


def db_create_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def db_get_inventory(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT item_id, item_name, item_count FROM inventory WHERE username=?", (username,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]


# ---------------- 素材 ----------------
def try_load_image(name, size=None):
    base = name.rsplit(".", 1)[0]
    for ext in [".png", ".jpg", ".jpeg"]:
        path = os.path.join(ASSETS_DIR, base + ext)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if size:
                    img = pygame.transform.smoothscale(img, size)
                return img
            except Exception as e:
                print(f"加载失败 {path}: {e}")
    return None


def play_music(filename, volume=0.6, loop=True):
    base = filename.rsplit(".", 1)[0]
    for ext in [".mp3", ".ogg", ".wav"]:
        path = os.path.join(ASSETS_DIR, base + ext)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(-1 if loop else 0)
            except Exception as e:
                print("音乐加载失败：", e)
            return


def stop_music(fade_ms=500):
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except Exception:
        pass


# ---------------- 启动动画 ----------------
class StartAnimation:
    def __init__(self):
        self.time = 0.0
        self.bg = try_load_image("bg_start.png", (WIDTH, HEIGHT))
        self.logo = try_load_image("logo.png", (500, 180))
        self.particles = []
        for _ in range(80):
            self.particles.append({
                "x": random.randint(0, WIDTH),
                "y": random.randint(0, HEIGHT),
                "speed": random.uniform(0.3, 1.5),
                "radius": random.uniform(1, 3),
                "alpha": random.randint(80, 220)
            })
        play_music("start_bgm.mp3", volume=0.6, loop=True)

    def update(self, dt):
        self.time += dt
        for p in self.particles:
            p["y"] -= p["speed"]
            if p["y"] < -5:
                p["y"] = HEIGHT + 5
                p["x"] = random.randint(0, WIDTH)

    def draw(self, surface):
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:
            for i in range(HEIGHT):
                ratio = i / HEIGHT
                c = (
                    int(BG_DARK[0] * (1 - ratio) + BG_MID[0] * ratio),
                    int(BG_DARK[1] * (1 - ratio) + BG_MID[1] * ratio),
                    int(BG_DARK[2] * (1 - ratio) + BG_MID[2] * ratio),
                )
                pygame.draw.line(surface, c, (0, i), (WIDTH, i))

        for p in self.particles:
            r = int(p["radius"])
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, int(p["alpha"])), (r, r), r)
            surface.blit(s, (p["x"], p["y"]))

        logo_alpha = min(255, int(self.time * 120))
        if self.logo:
            logo_img = self.logo.copy()
            logo_img.set_alpha(logo_alpha)
            rect = logo_img.get_rect(center=(WIDTH // 2, 200))
            surface.blit(logo_img, rect)
        else:
            title = FONT_XL.render("星 海 回 响", True, TEXT_WHITE)
            title.set_alpha(logo_alpha)
            surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 170))

        if self.time > 0.6:
            sub_alpha = min(255, int((self.time - 0.6) * 200))
            sub = FONT_M.render("STELLAR ECHO", True, TEXT_GRAY)
            sub.set_alpha(sub_alpha)
            surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 270))


# ---------------- 主程序 ----------------
class Game:
    def __init__(self):
        init_db()
        self.current_user = None
        self.player_data = None
        self.state = "start_anim"
        self.start_anim = StartAnimation()
        self.field = "user"
        self.login_user = ""
        self.login_pwd = ""
        self.reg_user = ""
        self.reg_pwd = ""
        self.reg_pwd2 = ""

        self.message = ""
        self.message_timer = 0
        self.login_music_started = False
        self.inventory = []
        self.battle = None

    def show_message(self, msg, t=2.0):
        self.message = msg
        self.message_timer = t

    def enter_login(self):
        self.state = "login"
        self.field = "user"
        if not self.login_music_started:
            play_music("login_bgm.mp3", volume=0.5, loop=True)
            self.login_music_started = True

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if self.state == "start_anim":
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                stop_music()
                self.state = "start"
            return

        if self.state == "start":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.enter_login()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if WIDTH // 2 - 120 < mx < WIDTH // 2 + 120:
                    if HEIGHT // 2 - 20 < my < HEIGHT // 2 + 30:
                        self.enter_login()
                    elif HEIGHT // 2 + 50 < my < HEIGHT // 2 + 100:
                        pygame.quit()
                        sys.exit()

        elif self.state == "login":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # 账号框
                if WIDTH // 2 - 150 < mx < WIDTH // 2 + 150:
                    if HEIGHT // 2 - 60 < my < HEIGHT // 2 - 20:
                        val = ask_input("请输入账号", initial=self.login_user)
                        if val is not None:
                            self.login_user = val
                    elif HEIGHT // 2 < my < HEIGHT // 2 + 40:
                        val = ask_input("请输入密码", show="*", initial=self.login_pwd)
                        if val is not None:
                            self.login_pwd = val
                # 按钮
                if WIDTH // 2 - 120 < mx < WIDTH // 2 + 120:
                    if HEIGHT // 2 + 80 < my < HEIGHT // 2 + 130:
                        self.do_login()
                    elif HEIGHT // 2 + 150 < my < HEIGHT // 2 + 200:
                        self.state = "register"
                        self.field = "user"
                    elif HEIGHT // 2 + 220 < my < HEIGHT // 2 + 270:
                        self.state = "start"

        elif self.state == "register":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # 输入框
                if WIDTH // 2 - 150 < mx < WIDTH // 2 + 150:
                    if HEIGHT // 2 - 90 < my < HEIGHT // 2 - 50:
                        val = ask_input("请输入账号", initial=self.reg_user)
                        if val is not None:
                            self.reg_user = val
                    elif HEIGHT // 2 - 30 < my < HEIGHT // 2 + 10:
                        val = ask_input("请输入密码", show="*", initial=self.reg_pwd)
                        if val is not None:
                            self.reg_pwd = val
                    elif HEIGHT // 2 + 30 < my < HEIGHT // 2 + 70:
                        val = ask_input("请再次输入密码", show="*", initial=self.reg_pwd2)
                        if val is not None:
                            self.reg_pwd2 = val
                # 按钮
                if WIDTH // 2 - 120 < mx < WIDTH // 2 + 120:
                    if HEIGHT // 2 + 110 < my < HEIGHT // 2 + 160:
                        self.do_register()
                    elif HEIGHT // 2 + 180 < my < HEIGHT // 2 + 230:
                        self.state = "login"
                        self.field = "user"

        elif self.state == "main":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.start_battle()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if WIDTH - 190 < mx < WIDTH - 50 and 10 < my < 50:
                    self.logout()
                elif WIDTH // 2 - 20 < mx < WIDTH // 2 + 220:
                    if HEIGHT // 2 - 65 < my < HEIGHT // 2 - 15:
                        self.start_battle()
                    elif HEIGHT // 2 + 15 < my < HEIGHT // 2 + 65:
                        self.heal_player()
                    elif HEIGHT // 2 + 95 < my < HEIGHT // 2 + 145:
                        self.reset_player()
                elif WIDTH - 220 < mx < WIDTH - 60 and HEIGHT - 70 < my < HEIGHT - 20:
                    self.open_inventory()

        elif self.state == "battle":
            if self.battle:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.battle.battle_over:
                    self.battle.save_and_exit()
                    self.player_data = db_get_user(self.current_user)
                    self.inventory = db_get_inventory(self.current_user)
                    self.battle = None
                    self.state = "main"
                    if self.login_music_started:
                        play_music("login_bgm.mp3", volume=0.5, loop=True)
                else:
                    self.battle.handle_event(event)

        elif self.state == "inventory":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "main"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if WIDTH // 2 - 100 < mx < WIDTH // 2 + 100 and HEIGHT - 100 < my < HEIGHT - 50:
                    self.state = "main"

    def do_login(self):
        if not self.login_user or not self.login_pwd:
            self.show_message("账号和密码不能为空")
            return
        user = db_get_user(self.login_user)
        if not user:
            self.show_message("账号不存在")
            return
        if user["password"] != self.login_pwd:
            self.show_message("密码错误")
            return
        self.current_user = self.login_user
        self.player_data = user
        self.inventory = db_get_inventory(self.current_user)
        self.state = "main"
        self.show_message(f"欢迎回来，{self.current_user}")

    def do_register(self):
        if not self.reg_user or not self.reg_pwd:
            self.show_message("账号和密码不能为空")
            return
        if len(self.reg_user) < 3:
            self.show_message("账号至少3个字符")
            return
        if len(self.reg_pwd) < 6:
            self.show_message("密码至少6位")
            return
        if self.reg_pwd != self.reg_pwd2:
            self.show_message("两次密码不一致")
            return
        ok = db_create_user(self.reg_user, self.reg_pwd)
        if not ok:
            self.show_message("账号已存在")
            return
        self.show_message("注册成功，请登录")
        self.login_user = self.reg_user
        self.login_pwd = ""
        self.state = "login"
        self.field = "pwd"

    def start_battle(self):
        stop_music(fade_ms=500)
        self.battle = Battle2D(self.player_data, self.current_user)
        self.state = "battle"
        self.show_message("进入战斗！")

    def open_inventory(self):
        self.inventory = db_get_inventory(self.current_user)
        self.state = "inventory"

    def heal_player(self):
        p = self.player_data
        if p["exp"] < 10:
            self.show_message("经验不足")
            return
        p["exp"] -= 10
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE users SET exp=? WHERE username=?", (p["exp"], self.current_user))
        conn.commit()
        conn.close()
        self.show_message("生命已恢复")

    def reset_player(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE users SET level=1, exp=0, max_hp=100, atk=15, wins=0 WHERE username=?",
                     (self.current_user,))
        conn.commit()
        conn.close()
        self.player_data = db_get_user(self.current_user)
        self.show_message("角色已重置")

    def logout(self):
        self.current_user = None
        self.player_data = None
        self.inventory = []
        self.login_user = ""
        self.login_pwd = ""
        self.reg_user = ""
        self.reg_pwd = ""
        self.reg_pwd2 = ""
        self.field = "user"
        self.state = "start"

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        if self.state == "start_anim":
            self.start_anim.update(dt)
            if self.start_anim.time > 3.0:
                stop_music()
                self.state = "start"

        if self.state == "battle" and self.battle:
            keys = pygame.key.get_pressed()
            self.battle.update(keys, dt)

    def draw(self):
        if self.state == "start_anim":
            self.start_anim.draw(screen)
        elif self.state == "start":
            self.draw_start()
        elif self.state == "login":
            self.draw_login()
        elif self.state == "register":
            self.draw_register()
        elif self.state == "main":
            self.draw_main()
        elif self.state == "battle" and self.battle:
            self.battle.draw(screen)
        elif self.state == "inventory":
            self.draw_inventory()

        if self.message:
            img = FONT_M.render(self.message, True, TEXT_WHITE)
            bg = pygame.Surface((img.get_width() + 40, img.get_height() + 20), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (WIDTH // 2 - bg.get_width() // 2, 30))
            screen.blit(img, (WIDTH // 2 - img.get_width() // 2, 40))

    def draw_button(self, text, cx, cy, w=240, h=50, bg=ACCENT):
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        img = FONT_M.render(text, True, TEXT_WHITE)
        screen.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))

    def draw_input(self, label, value, cx, cy, active, is_pwd=False):
        w, h = 300, 40
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_surf.fill((15, 52, 96, 200))
        screen.blit(bg_surf, rect)
        pygame.draw.rect(screen, ACCENT if active else TEXT_GRAY, rect, 2, border_radius=4)

        if is_pwd:
            display = "*" * len(value)
        else:
            display = value

        img = FONT_S.render(display, True, TEXT_WHITE)
        screen.blit(img, (rect.x + 10, cy - img.get_height() // 2))

        lbl = FONT_S.render(label, True, TEXT_GRAY)
        screen.blit(lbl, (rect.x - lbl.get_width() - 10, cy - lbl.get_height() // 2))

    def draw_start(self):
        bg = try_load_image("bg_start.png", (WIDTH, HEIGHT))
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(BG_DARK)
        t = FONT_XL.render("星 海 回 响", True, TEXT_WHITE)
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 160))
        s = FONT_M.render("STELLAR ECHO", True, TEXT_GRAY)
        screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 240))
        self.draw_button("开始游戏", WIDTH // 2, HEIGHT // 2)
        self.draw_button("退出", WIDTH // 2, HEIGHT // 2 + 70, bg=BG_LIGHT)

    def draw_login(self):
        bg = try_load_image("bg_login.png", (WIDTH, HEIGHT))
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(BG_DARK)
        t = FONT_L.render("账号登录", True, TEXT_WHITE)
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 120))
        self.draw_input("账号", self.login_user, WIDTH // 2, HEIGHT // 2 - 40, self.field == "user")
        self.draw_input("密码", self.login_pwd, WIDTH // 2, HEIGHT // 2 + 20, self.field == "pwd", is_pwd=True)
        self.draw_button("登 录", WIDTH // 2, HEIGHT // 2 + 105)
        self.draw_button("去注册", WIDTH // 2, HEIGHT // 2 + 175, bg=BG_LIGHT)
        self.draw_button("返回", WIDTH // 2, HEIGHT // 2 + 245, bg=BG_MID)

    def draw_register(self):
        bg = try_load_image("bg_login.png", (WIDTH, HEIGHT))
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(BG_DARK)
        t = FONT_L.render("注册账号", True, TEXT_WHITE)
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 100))
        self.draw_input("账号", self.reg_user, WIDTH // 2, HEIGHT // 2 - 70, self.field == "user")
        self.draw_input("密码", self.reg_pwd, WIDTH // 2, HEIGHT // 2 - 10, self.field == "pwd", is_pwd=True)
        self.draw_input("确认", self.reg_pwd2, WIDTH // 2, HEIGHT // 2 + 50, self.field == "pwd2", is_pwd=True)
        self.draw_button("注 册", WIDTH // 2, HEIGHT // 2 + 135)
        self.draw_button("返回登录", WIDTH // 2, HEIGHT // 2 + 205, bg=BG_LIGHT)

    def draw_main(self):
        screen.fill(BG_DARK)
        pygame.draw.rect(screen, BG_MID, (0, 0, WIDTH, 60))
        screen.blit(FONT_M.render(f"指挥官：{self.current_user}", True, TEXT_WHITE), (20, 18))
        self.draw_button("退出登录", WIDTH - 120, 30, w=140, h=40, bg=ACCENT)

        p = self.player_data
        panel = pygame.Rect(40, 100, 260, 400)
        pygame.draw.rect(screen, BG_MID, panel)
        screen.blit(FONT_M.render("角色信息", True, TEXT_WHITE), (60, 120))
        screen.blit(FONT_S.render(f"等级：{p['level']}", True, TEXT_GRAY), (60, 170))
        screen.blit(FONT_S.render(f"经验：{p['exp']}/100", True, TEXT_GRAY), (60, 200))
        screen.blit(FONT_S.render(f"生命：{p['max_hp']}", True, TEXT_GRAY), (60, 230))
        screen.blit(FONT_S.render(f"攻击：{p['atk']}", True, TEXT_GRAY), (60, 260))
        screen.blit(FONT_S.render(f"胜场：{p['wins']}", True, TEXT_GRAY), (60, 290))

        self.draw_button("进入战斗", WIDTH // 2 + 100, HEIGHT // 2 - 40)
        self.draw_button("恢复生命(10经验)", WIDTH // 2 + 100, HEIGHT // 2 + 40, bg=BG_LIGHT)
        self.draw_button("重置角色", WIDTH // 2 + 100, HEIGHT // 2 + 120, bg=BG_MID)
        self.draw_button("背包", WIDTH - 140, HEIGHT - 45, w=140, h=40, bg=BG_LIGHT)

    def draw_inventory(self):
        screen.fill(BG_DARK)
        pygame.draw.rect(screen, BG_MID, (0, 0, WIDTH, 60))
        screen.blit(FONT_M.render("背包", True, TEXT_WHITE), (20, 18))

        panel = pygame.Rect(60, 100, WIDTH - 120, HEIGHT - 220)
        pygame.draw.rect(screen, BG_MID, panel)

        if not self.inventory:
            screen.blit(FONT_M.render("背包空空如也", True, TEXT_GRAY), (WIDTH // 2 - 80, HEIGHT // 2 - 20))
        else:
            for i, item in enumerate(self.inventory[:12]):
                col = i % 4
                row = i // 4
                x = 100 + col * 200
                y = 140 + row * 100
                rect = pygame.Rect(x, y, 170, 80)
                pygame.draw.rect(screen, BG_LIGHT, rect)
                pygame.draw.rect(screen, ACCENT, rect, 2)
                screen.blit(FONT_S.render(item["name"], True, TEXT_WHITE), (x + 10, y + 10))
                screen.blit(FONT_S.render(f"x{item['count']}", True, TEXT_GRAY), (x + 10, y + 40))

        self.draw_button("返回", WIDTH // 2, HEIGHT - 70, w=200, h=50, bg=BG_LIGHT)


def main():
    game = Game()
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()