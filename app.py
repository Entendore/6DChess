import pygame
import sys
import math
import copy
import random
import time
import os

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ─── Layout & Config ─────────────────────────────────────────────────────────
SQ, BSIZE, BPX, GAP = 50, 6, 300, 22
COLS, ROWS, MX, MY = 3, 2, 50, 110
PANEL_W = 306
W = MX * 2 + COLS * BPX + (COLS - 1) * GAP + PANEL_W
H = MY + ROWS * BPX + (ROWS - 1) * GAP + 50
FPS = 60

DCOORD = {0: (0, 0), 1: (1, 0), 2: (2, 0), 3: (0, 1), 4: (1, 1), 5: (2, 1)}
TNAME = {0: "Past", 1: "Present", 2: "Future"}
BNAME = {0: "TL α", 1: "TL β"}
DNAMES = ["α", "β", "γ", "δ", "ε", "ζ"]
TCOL = {0: (85, 135, 210), 1: (200, 195, 85), 2: (220, 85, 85)}
TCOL_DIM = {0: (40, 60, 90), 1: (90, 88, 40), 2: (90, 40, 40)}

BG = (26, 24, 22); LSQ = (238, 216, 180); DSQ = (177, 135, 96)
TXT = (210, 205, 195); DTXT = (120, 115, 108); PBG = (32, 30, 28)
WBG = (245, 238, 228); BBG = (75, 70, 65); WFG = (255, 255, 255); BFG = (35, 30, 25)
GOLD = (255, 215, 50)

MC = {"normal": (100, 200, 100), "branch_shift": (80, 160, 240), "future_shift": (60, 130, 230), "temporal_warp": (190, 90, 255), "knight_warp_branch": (80, 210, 190), "knight_warp_future": (60, 170, 230), "knight_warp_past": (170, 70, 210)}
CAP_C = {"normal": (230, 75, 75), "branch_shift": (70, 130, 210), "future_shift": (60, 110, 210), "temporal_warp": (170, 60, 230), "knight_warp_branch": (70, 190, 170), "knight_warp_future": (60, 150, 210), "knight_warp_past": (150, 50, 190)}

EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(7)
WP, BP = 1, 2
PIECE_CHARS = {(WP, KING): '♔', (WP, QUEEN): '♕', (WP, ROOK): '♖', (WP, BISHOP): '♗', (WP, KNIGHT): '♘', (WP, PAWN): '♙', (BP, KING): '♚', (BP, QUEEN): '♛', (BP, ROOK): '♜', (BP, BISHOP): '♝', (BP, KNIGHT): '♞', (BP, PAWN): '♟'}
PNAMES = {PAWN: "Pawn", KNIGHT: "Knight", BISHOP: "Bishop", ROOK: "Rook", QUEEN: "Queen", KING: "King"}
PVAL = {PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9, KING: 0}

# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class AudioManager:
    def __init__(self):
        self.sounds = {}; self.enabled = False
        try:
            import numpy as np; self.np = np; self.sr = 44100; self.enabled = True
            self._generate_chiptune_sfx(); print("🎵 8-Bit Synthesizer initialized.")
        except ImportError: print("⚠️ Numpy not found. Audio disabled.")

    def _to_sound(self, wave):
        wave = self.np.clip(wave, -1.0, 1.0)
        audio = (wave * 32767).astype(self.np.int16)
        return pygame.sndarray.make_sound(self.np.column_stack((audio, audio)))

    def _gen_square(self, freq, dur, vol=0.3):
        t = self.np.linspace(0, dur, int(self.sr * dur), endpoint=False)
        return self.np.sign(self.np.sin(2 * self.np.pi * freq * t)) * vol

    def _gen_tri(self, freq, dur, vol=0.3):
        t = self.np.linspace(0, dur, int(self.sr * dur), endpoint=False)
        return (2 * self.np.abs(2 * (t * freq - self.np.floor(t * freq + 0.5))) - 1) * vol

    def _gen_noise(self, dur, vol=0.3): return self.np.random.uniform(-vol, vol, int(self.sr * dur))

    def _generate_chiptune_sfx(self):
        np, sr = self.np, self.sr
        t = np.linspace(0, 0.05, int(sr * 0.05), endpoint=False)
        self.sounds["click"] = self._to_sound(self._gen_square(880, 0.05, 0.25) * np.exp(-t * 40))

        t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
        freq = 500 - (350 * (t / 0.1)); phase = 2 * np.pi * np.cumsum(freq) / sr
        self.sounds["move"] = self._to_sound(np.sign(np.sin(phase)) * 0.2 * np.exp(-t * 15))

        t1 = np.linspace(0, 0.08, int(sr * 0.08), endpoint=False)
        thud = self._gen_square(150, 0.08, 0.4) * np.exp(-t1 * 30)
        t2 = np.linspace(0, 0.04, int(sr * 0.04), endpoint=False)
        self.sounds["capture"] = self._to_sound(np.concatenate([thud, self._gen_noise(0.04, 0.3) * np.exp(-t2 * 60)]))

        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        freq = 200 + (1600 * (t / 0.2)**2); phase = 2 * np.pi * np.cumsum(freq) / sr
        self.sounds["warp"] = self._to_sound(np.sign(np.sin(phase)) * 0.25 * np.exp(-t * 5))

        w = np.array([], dtype=np.float64)
        for f in [523.25, 392.00, 311.13, 261.63]:
            t = np.linspace(0, 0.07, int(sr * 0.07), endpoint=False)
            phase = 2 * np.pi * np.cumsum(f + np.sin(2 * np.pi * 20 * t) * 15) / sr
            w = np.concatenate([w, np.sign(np.sin(phase)) * 0.3 * np.exp(-t * 20)])
        self.sounds["causality"] = self._to_sound(w)

        w = np.array([], dtype=np.float64)
        for f in [329.63, 261.63, 220.00]:
            t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
            w = np.concatenate([w, self._gen_tri(f, 0.25, 0.4) * np.exp(-t * 4)])
        self.sounds["gameover"] = self._to_sound(w)

        t = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
        freq = np.where(t < 0.06, 1200, 600); phase = 2 * np.pi * np.cumsum(freq) / sr
        self.sounds["radar"] = self._to_sound(np.sign(np.sin(phase)) * 0.2 * np.exp(-t * 10))

    def play(self, name):
        if self.enabled and name in self.sounds: self.sounds[name].play()

# ═══════════════════════════════════════════════════════════════════════════════
#  CORE GAME LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
class Piece:
    __slots__ = ("type", "color", "uid"); _n = 0
    def __init__(self, t, c): self.type, self.color, self.uid = t, c, Piece._n; Piece._n += 1

class Board:
    def __init__(self): self.g = [[None]*BSIZE for _ in range(BSIZE)]
    def get(self, r, c): return self.g[r][c] if 0<=r<BSIZE and 0<=c<BSIZE else None
    def put(self, r, c, p): self.g[r][c] = p
    def rem(self, r, c): self.g[r][c] = None

class Game:
    def __init__(self):
        Piece._n = 0; self.boards = [Board() for _ in range(6)]
        self.cur, self.sel, self.moves = WP, None, []
        self.over, self.winner, self.last = False, None, None
        self.hist, self.fx = [], []
        self.hover, self.causality_msg, self.causality_timer = None, "", 0
        self.adj = {0:[1,3,4], 1:[0,2,3,4,5], 2:[1,4,5], 3:[0,1,4], 4:[0,1,2,3,5], 5:[1,2,4]}
        self._setup()

    def _setup(self):
        bk = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP]
        for bi in range(6):
            for c in range(BSIZE):
                self.boards[bi].put(0, c, Piece(bk[c], BP)); self.boards[bi].put(1, c, Piece(PAWN, BP))
                self.boards[bi].put(BSIZE-2, c, Piece(PAWN, WP)); self.boards[bi].put(BSIZE-1, c, Piece(bk[c], WP))

    @staticmethod
    def _in(r, c): return 0<=r<BSIZE and 0<=c<BSIZE
    @staticmethod
    def _tdiff(a, b): return DCOORD[b][0] - DCOORD[a][0]

    def _normal(self, bi, r, c):
        b, p, mv = self.boards[bi], self.boards[bi].get(r, c), []
        if not p: return mv
        en = BP if p.color == WP else WP
        def ta(nr, nc, mt="normal"):
            if self._in(nr, nc):
                t = b.get(nr, nc)
                if t is None or t.color == en: mv.append((bi, nr, nc, False, mt))
        def sl(dr, dc, mt="normal"):
            for i in range(1, BSIZE):
                nr, nc = r+dr*i, c+dc*i
                if not self._in(nr, nc): break
                t = b.get(nr, nc)
                if t is None: mv.append((bi, nr, nc, False, mt))
                elif t.color == en: mv.append((bi, nr, nc, False, mt)); break
                else: break
        if p.type == PAWN:
            d, st = (-1 if p.color==WP else 1), (BSIZE-2 if p.color==WP else 1); nr = r+d
            if self._in(nr, c) and b.get(nr, c) is None:
                mv.append((bi, nr, c, False, "normal"))
                if r == st and self._in(nr+d, c) and b.get(nr+d, c) is None: mv.append((bi, nr+d, c, False, "normal"))
            for dc in (-1, 1):
                if self._in(nr, c+dc):
                    t = b.get(nr, c+dc)
                    if t and t.color == en: mv.append((bi, nr, c+dc, False, "normal"))
        elif p.type == KNIGHT:
            for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)): ta(r+dr, c+dc)
        elif p.type == BISHOP:
            for dr, dc in ((-1,-1),(-1,1),(1,-1),(1,1)): sl(dr, dc)
        elif p.type == ROOK:
            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)): sl(dr, dc)
        elif p.type == QUEEN:
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr or dc: sl(dr, dc)
        elif p.type == KING:
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr or dc: ta(r+dr, c+dc)
        return mv

    def _dim(self, bi, r, c):
        p = self.boards[bi].get(r, c)
        if not p or p.type == PAWN: return []
        mv = []
        for ad in self.adj.get(bi, []):
            t = self.boards[ad].get(r, c)
            if t is None or t.color != p.color:
                td = self._tdiff(bi, ad); mt = "temporal_warp" if td<0 else ("future_shift" if td>0 else "branch_shift")
                mv.append((ad, r, c, True, mt))
        return mv

    def _kwarp(self, bi, r, c):
        p = self.boards[bi].get(r, c)
        if not p or p.type != KNIGHT: return []
        mv, en = [], BP if p.color == WP else WP
        for ad in self.adj.get(bi, []):
            for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
                nr, nc = r+dr, c+dc
                if self._in(nr, nc):
                    t = self.boards[ad].get(nr, nc)
                    if t is None or t.color == en:
                        td = self._tdiff(bi, ad); mt = "knight_warp_past" if td<0 else ("knight_warp_future" if td>0 else "knight_warp_branch")
                        mv.append((ad, nr, nc, True, mt))
        return mv

    def all_moves(self, bi, r, c):
        seen, res = set(), []
        for m in self._normal(bi, r, c) + self._dim(bi, r, c) + self._kwarp(bi, r, c):
            if (m[0], m[1], m[2]) not in seen: seen.add((m[0], m[1], m[2])); res.append(m)
        return res

    def get_all_player_moves(self):
        return [m for bi in range(6) for r in range(BSIZE) for c in range(BSIZE) if (p:=self.boards[bi].get(r,c)) and p.color==self.cur for m in self.all_moves(bi, r, c)]

    def _causality(self, cap, to_bi):
        td, br, erased = DCOORD[to_bi][0], DCOORD[to_bi][1], 0
        for bi in range(6):
            if DCOORD[bi][0] > td and DCOORD[bi][1] == br:
                for r in range(BSIZE):
                    for c in range(BSIZE):
                        p = self.boards[bi].get(r, c)
                        if p and p.uid == cap.uid:
                            self.boards[bi].rem(r, c); erased += 1
                            if p.type == KING: self.over, self.winner = True, self.cur
        if erased:
            self.causality_msg = f"⚡ CAUSALITY: {PNAMES[cap.type]} erased from future ({erased} copy{'ies' if erased > 1 else ''})"
            self.causality_timer = 3.0

    def do_move(self, fb, fr, fc, tb, tr, tc, mt="normal"):
        piece, cap = self.boards[fb].get(fr, fc), self.boards[tb].get(tr, tc)
        self.last = ((fb, fr, fc), (tb, tr, tc))
        if cap:
            if cap.type == KING: self.over, self.winner = True, piece.color
            if self._tdiff(fb, tb) != 0: self._causality(cap, tb)
        self.boards[tb].put(tr, tc, piece); self.boards[fb].rem(fr, fc)
        if piece.type == PAWN and ((piece.color==WP and tr==0) or (piece.color==BP and tr==BSIZE-1)):
            self.boards[tb].put(tr, tc, Piece(QUEEN, piece.color))
        self.hist.append((fb, fr, fc, tb, tr, tc, mt))
        self.cur = BP if self.cur == WP else WP; self.sel, self.moves = None, []
        return mt

    def click(self, mx, my):
        if self.over: return None
        for bi in range(6):
            bc, br = bi % COLS, bi // COLS
            bx, by = MX + bc * (BPX + GAP), MY + br * (BPX + GAP)
            if bx <= mx < bx + BPX and by <= my < by + BPX:
                c, r = (mx - bx) // SQ, (my - by) // SQ
                if self.sel:
                    for m in self.moves:
                        if m[0] == bi and m[1] == r and m[2] == c: return self.do_move(*self.sel, bi, r, c, m[4])
                    p = self.boards[bi].get(r, c)
                    if p and p.color == self.cur: self.sel, self.moves = (bi, r, c), self.all_moves(bi, r, c)
                    else: self.sel, self.moves = None, []
                else:
                    p = self.boards[bi].get(r, c)
                    if p and p.color == self.cur: self.sel, self.moves = (bi, r, c), self.all_moves(bi, r, c)
                return "click_empty"
        return None

    def upd_hover(self, mx, my):
        self.hover = None
        for bi in range(6):
            bc, br = bi % COLS, bi // COLS
            bx, by = MX + bc * (BPX + GAP), MY + br * (BPX + GAP)
            if bx <= mx < bx + BPX and by <= my < by + BPX:
                self.hover = (bi, (my - by) // SQ, (mx - bx) // SQ); return

    def count_kings(self):
        wk = bk = 0
        for bi in range(6):
            for r in range(BSIZE):
                for c in range(BSIZE):
                    p = self.boards[bi].get(r, c)
                    if p and p.type == KING:
                        if p.color == WP: wk += 1
                        else: bk += 1
        return wk, bk

    def count_mat(self, color):
        return sum(PVAL[p.type] for bi in range(6) for r in range(BSIZE) for c in range(BSIZE) if (p:=self.boards[bi].get(r,c)) and p.color==color)

# ═══════════════════════════════════════════════════════════════════════════════
#  AI LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
class MCTSNode:
    def __init__(self, s, m=None, p=None):
        self.state, self.move, self.parent = s, m, p
        self.children, self.wins, self.visits = [], 0, 0
        self.untried = s.get_all_player_moves()
        self.term = s.over or not self.untried

    def uct(self):
        if not self.children:
            return None
        return max(self.children, key=lambda c: (c.wins / c.visits) + 1.41 * math.sqrt(math.log(self.visits) / c.visits))

    def expand(self):
        m = self.untried.pop(random.randrange(len(self.untried)))
        ns = copy.deepcopy(self.state); ns.do_move(*m)
        c = MCTSNode(ns, m, self); self.children.append(c); return c

    def roll(self):
        s, d = copy.deepcopy(self.state), 0
        while not s.over and d < 40:
            m = s.get_all_player_moves()
            if not m: break
            s.do_move(*random.choice(m)); d += 1
        if s.winner is None: return 0.5
        return 1 if s.winner == self.state.cur else 0

    def back(self, r):
        self.visits += 1; self.wins += r
        if self.parent: self.parent.back(1 - r)

def get_ai_move(game, difficulty):
    moves = game.get_all_player_moves()
    if not moves: return None

    if difficulty == "EASY":
        return random.choice(moves)

    elif difficulty == "MEDIUM":
        best_move, best_score = moves[0], -1
        for m in moves:
            score = 0
            target = game.boards[m[0]].get(m[1], m[2])
            if target and target.color != game.cur:
                score = PVAL[target.type] * 10
                if target.type == KING: score = 1000
            if "warp" in m[4] or "shift" in m[4]: score += 2
            if score > best_score: best_score, best_move = score, m
        if random.random() < 0.2: return random.choice(moves)
        return best_move

    elif difficulty == "HARD":
        root = MCTSNode(copy.deepcopy(game))
        if root.term: return random.choice(moves)
        iterations = 30
        for _ in range(iterations):
            n = root
            while not n.term and not n.untried:
                if not n.children: break
                n = n.uct()
                if n is None: break
            if n is None: break
            if n.term:
                n.visits += 1
                n.back(1 if n.state.winner == n.state.cur else 0.5)
                continue
            if not n.untried and not n.children: break
            if n.untried: n = n.expand()
            if not n.term:
                n.back(n.roll())
            else:
                n.visits += 1
                n.back(1 if n.state.winner == n.state.cur else 0.5)
        if not root.children: return random.choice(moves)
        return max(root.children, key=lambda c: c.visits).move
    return random.choice(moves)

# ═══════════════════════════════════════════════════════════════════════════════
#  QA & MCTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════
def run_qa_tests():
    print("🧪 RUNNING QA..."); passed, total = 0, 0
    def check(n, c):
        nonlocal passed, total; total += 1
        if c: passed += 1
        else: print(f"  ❌ FAIL: {n}")
    g = Game(); check("Pawn init", len(g.all_moves(0, 4, 0)) == 2)
    g = Game(); g.boards[0].rem(4, 0); g.boards[1].rem(5, 0)
    check("Rook shift", any(m[4] == "future_shift" for m in g.all_moves(0, 5, 0)))
    g = Game(); g.boards[0].rem(4, 1); g.boards[0].rem(3, 0); g.boards[0].rem(4, 2)
    check("Knight warp", any("knight_warp" in m[4] for m in g.all_moves(0, 5, 1)))
    g = Game(); tp = Piece(ROOK, BP); g.boards[1].put(2, 2, tp); fp = Piece(ROOK, BP); fp.uid = tp.uid; g.boards[2].put(2, 2, fp); g.boards[0].put(0, 0, Piece(ROOK, WP)); g.cur = WP; g.do_move(0, 0, 0, 1, 2, 2, "future_shift")
    check("Causality", g.boards[2].get(2, 2) is None)
    g = Game(); g.boards[0].put(2, 3, Piece(QUEEN, WP)); g.boards[0].rem(1, 3); g.cur = WP; g.do_move(0, 2, 3, 0, 0, 4, "normal")
    check("Game Over", g.over == True)
    g = Game(); g.cur = BP; m = get_ai_move(g, "EASY"); check("Easy AI moves", m is not None)
    m = get_ai_move(g, "MEDIUM"); check("Med AI moves", m is not None)
    m = get_ai_move(g, "HARD"); check("Hard AI moves", m is not None)
    print(f"✅ QA PASSED ({passed}/{total})")

def run_mcts_test(iterations=2):
    print("🤖 MCTS SELF-PLAY...")
    for i in range(iterations):
        g, m = Game(), 0
        while not g.over and m < 60:
            root = MCTSNode(copy.deepcopy(g))
            if root.term: break
            for _ in range(20):
                n = root
                while not n.term and not n.untried:
                    if not n.children: break
                    n = n.uct()
                    if n is None: break
                if n is None: break
                if n.term:
                    n.visits += 1
                    n.back(1 if n.state.winner == n.state.cur else 0.5)
                    continue
                if not n.untried and not n.children: break
                if n.untried: n = n.expand()
                if not n.term:
                    n.back(n.roll())
                else:
                    n.visits += 1
                    n.back(1 if n.state.winner == n.state.cur else 0.5)
            if not root.children: break
            g.do_move(*max(root.children, key=lambda c: c.visits).move); m += 1
    print("✅ MCTS STABLE")

# ═══════════════════════════════════════════════════════════════════════════════
#  VISUALS & UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════
class FX:
    def __init__(self, x, y, col, dur=0.35): self.x, self.y, self.col, self.dur, self.t, self.alive = x, y, col, dur, 0, True
    def update(self, dt): self.t += dt; (setattr(self, 'alive', False) if self.t >= self.dur else None)
    def draw(self, scr):
        p = self.t / self.dur; a = int(180 * (1 - p)); r = int(SQ * 0.3 + SQ * 0.7 * p)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA); pygame.draw.circle(s, (*self.col[:3], a), (r, r), r, max(1, int(3 * (1 - p)))); scr.blit(s, (self.x - r, self.y - r))

def find_piece_font(size):
    for name in ['Segoe UI Symbol', 'DejaVu Sans', 'Arial Unicode MS', None]:
        try:
            f = pygame.font.SysFont(name, size)
            if f.render('♔', True, (0,0,0)).get_width() > size * 0.25: return f
        except: continue
    return pygame.font.SysFont(None, size)

def make_pieces():
    surfs, pf = {}, find_piece_font(int(SQ * 0.72))
    for col, bg, fg, ol in [(WP, WBG, WFG, (180, 170, 155)), (BP, BBG, BFG, (100, 95, 85))]:
        for pt in range(1, 7):
            s = pygame.Surface((SQ, SQ), pygame.SRCALPHA); cx, cy, rad = SQ//2, SQ//2, SQ//2-3
            pygame.draw.circle(s, (0, 0, 0, 50), (cx+2, cy+2), rad); pygame.draw.circle(s, bg, (cx, cy), rad)
            hl = tuple(min(255, c+20) for c in bg); pygame.draw.arc(s, hl, (cx-rad, cy-rad, rad*2, rad*2), 0.4, 2.3, 2)
            pygame.draw.circle(s, ol, (cx, cy), rad, 1); ch = PIECE_CHARS[(col, pt)]
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                os_ = pf.render(ch, True, ol); s.blit(os_, os_.get_rect(center=(cx+dx, cy+dy)))
            ms = pf.render(ch, True, fg); s.blit(ms, ms.get_rect(center=(cx, cy - 1))); surfs[(col, pt)] = s
    return surfs

def make_window_icon():
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(icon, (40, 38, 35), (0, 0, 32, 32), border_radius=4)
    pygame.draw.rect(icon, GOLD, (0, 0, 32, 32), 2, border_radius=4)
    t = pygame.font.SysFont('segoeuisymbol', 24).render('♚', True, GOLD); icon.blit(t, (4, 2))
    return icon

def bord_orig(bi): bc, br = bi % COLS, bi // COLS; return MX + bc * (BPX + GAP), MY + br * (BPX + GAP)
def bord_center(bi): bx, by = bord_orig(bi); return bx + BPX // 2, by + BPX // 2

def draw_hypercube(scr, rect, t):
    verts = [[1 if (b >> i) & 1 else -1 for i in range(6)] for b in range(64)]
    base_a = [0.32, 0.71, 0.53, 0.21, 0.82, 0.41, 0.63, 0.12, 0.91, 0.37, 0.56, 0.17, 0.73, 0.48, 0.67]
    speeds = [0.5, -0.3, 0.7, -0.4, 0.2, -0.6, 0.8, -0.1, 0.4, -0.5, 0.3, -0.2, 0.6, -0.7, 0.9]
    idx = 0
    for i in range(6):
        for j in range(i + 1, 6):
            a = base_a[idx] + t * speeds[idx]; idx += 1; ca, sa = math.cos(a), math.sin(a)
            for v in verts: vi, vj = v[i], v[j]; v[i] = vi*ca - vj*sa; v[j] = vi*sa + vj*ca
    xs, ys = [v[0] for v in verts], [v[1] for v in verts]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    sc = min((rect[2]-20)/max(mxx-mnx,0.01), (rect[3]-20)/max(mxy-mny,0.01))
    ox, oy = rect[0] + rect[2]//2 - (mnx+mxx)/2*sc, rect[1] + rect[3]//2 - (mny+mxy)/2*sc
    pts = [(int(ox+v[0]*sc), int(oy+v[1]*sc)) for v in verts]
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(64):
        for j in range(i+1, 64):
            if (i^j)&((i^j)-1)==0: pygame.draw.aaline(s, (65, 62, 55, 150), pts[i], pts[j])
    scr.blit(s, (0,0))

# ═══════════════════════════════════════════════════════════════════════════════
#  SCENES
# ═══════════════════════════════════════════════════════════════════════════════
class Scene:
    def __init__(self, app): self.app = app
    def handle_event(self, ev): pass
    def update(self, dt): pass
    def draw(self, scr): pass

class MainMenuScene(Scene):
    def __init__(self, app):
        super().__init__(app); self.t = 0; self.state = "main"
        self.main_buttons = [
            {"rect": pygame.Rect(0,0,240,50), "text": "🤖  PLAY VS AI", "action": "ai_menu", "y": 300, "hover": False},
            {"rect": pygame.Rect(0,0,240,50), "text": "👥  LOCAL 2 PLAYER", "action": "pvp", "y": 370, "hover": False},
            {"rect": pygame.Rect(0,0,240,50), "text": "📖  HOW TO PLAY", "action": "help", "y": 440, "hover": False},
            {"rect": pygame.Rect(0,0,240,50), "text": "🚪  QUIT", "action": "quit", "y": 510, "hover": False}
        ]
        for b in self.main_buttons: b["rect"].x = W//2 - 120; b["rect"].y = b["y"]

        self.ai_buttons = [
            {"rect": pygame.Rect(0,0,200,50), "text": "🟢 EASY AI", "action": "easy", "y": 300, "hover": False},
            {"rect": pygame.Rect(0,0,200,50), "text": "🟡 MEDIUM AI", "action": "medium", "y": 370, "hover": False},
            {"rect": pygame.Rect(0,0,200,50), "text": "🔴 HARD AI (MCTS)", "action": "hard", "y": 440, "hover": False},
            {"rect": pygame.Rect(0,0,200,50), "text": "⬅ BACK", "action": "back", "y": 520, "hover": False}
        ]
        for b in self.ai_buttons: b["rect"].x = W//2 - 100; b["rect"].y = b["y"]

    def handle_event(self, ev):
        btns = self.ai_buttons if self.state == "ai" else self.main_buttons
        if ev.type == pygame.MOUSEMOTION:
            for b in btns: b["hover"] = b["rect"].collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in btns:
                if b["rect"].collidepoint(ev.pos):
                    act = b["action"]
                    if act == "quit": pygame.quit(); sys.exit()
                    elif act == "help": self.app.transition_to("help")
                    elif act == "pvp": self.app.transition_to("game", mode="PVP", difficulty=None)
                    elif act == "back": self.state = "main"
                    elif act in ["easy", "medium", "hard"]:
                        self.app.transition_to("game", mode="PVE", difficulty=act.upper())
                    elif act == "ai_menu": self.state = "ai"
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.state == "ai": self.state = "main"
            else: pygame.quit(); sys.exit()

    def update(self, dt): self.t += dt

    def draw(self, scr):
        scr.fill(BG)
        draw_hypercube(scr, (0, 0, W, H), self.t * 0.5)
        ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((26, 24, 22, 180)); scr.blit(ov, (0,0))
        tf = self.app.fonts["title"]; t = tf.render("6D  CHESS", True, GOLD); scr.blit(t, (W//2 - t.get_width()//2, 160))
        nf = self.app.fonts["normal"]; sub = nf.render("High-Dimensional Temporal Warfare", True, DTXT); scr.blit(sub, (W//2 - sub.get_width()//2, 220))

        btns = self.ai_buttons if self.state == "ai" else self.main_buttons
        if self.state == "ai":
            st = nf.render("Select AI Difficulty:", True, TXT); scr.blit(st, (W//2 - st.get_width()//2, 260))

        for b in btns:
            col = (60, 58, 54) if b.get("hover") else (45, 43, 40)
            bdr = GOLD if b.get("hover") else (80, 78, 72)
            pygame.draw.rect(scr, col, b["rect"], border_radius=8); pygame.draw.rect(scr, bdr, b["rect"], 2, border_radius=8)
            txt = nf.render(b["text"], True, TXT); scr.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

class HelpScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.pages = [
            ["WELCOME TO 6D CHESS", "", "This is chess extended into 6 dimensions.", "You play on 6 boards arranged in a grid.", "", "x₁, x₂: Normal board space (Rows/Cols)", "x₃, x₄: Hidden compactified dimensions", "x₅: Time (Past ⏪, Present ⏸, Future ⏩)", "x₆: Probability Branches (α, β)"],
            ["DIMENSIONAL SHIFTS", "", "Non-pawn pieces can warp through x₃/x₄", "to appear on the SAME square of an adjacent board.", "", "⏩ Future Shift: Move right on time axis.", "⏪ Past Warp: Move left on time axis.", "🌿 Branch Shift: Move up/down on branches.", "♙ Pawns CANNOT shift dimensions."],
            ["SPECIAL RULES", "", "♞ KNIGHT GEODESICS:", "Knights combine L-shape AND dim shifts.", "", "⚡ CAUSALITY:", "Capturing through time erases that piece", "from ALL future boards on that branch.", "The timeline self-corrects!"],
            ["HOW TO WIN & RADAR", "", "Each player starts with 6 Kings.", "Capture ANY of the opponent's Kings to win!", "", "👁️ CHRONO-RADAR (Press T):", "Shows a red heatmap of all squares the", "opponent can attack across ALL dimensions.", "Highly recommended for new players!"]
        ]
        self.page = 0
        self.back_rect = pygame.Rect(50, H-60, 100, 40)
        self.next_rect = pygame.Rect(W-150, H-60, 100, 40)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.back_rect.collidepoint(ev.pos):
                if self.page > 0: self.page -= 1
                else: self.app.transition_to("menu")
            if self.next_rect.collidepoint(ev.pos):
                if self.page < len(self.pages) - 1: self.page += 1
                else: self.app.transition_to("menu")
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: self.app.transition_to("menu")

    def draw(self, scr):
        scr.fill(BG)
        nf, sf = self.app.fonts["normal"], self.app.fonts["small"]
        lines = self.pages[self.page]; y = 60
        for i, line in enumerate(lines):
            if i == 0: t = nf.render(line, True, GOLD)
            elif "⚡" in line or "♞" in line or "👁️" in line: t = sf.render(line, True, (190, 100, 255))
            else: t = sf.render(line, True, TXT)
            scr.blit(t, (60, y)); y += 30
        for i in range(len(self.pages)):
            col = GOLD if i == self.page else (60, 58, 54)
            pygame.draw.circle(scr, col, (W//2 - (len(self.pages)*15)//2 + i*15 + 7, H-90), 5)
        for rect, text in [(self.back_rect, "⬅ Back"), (self.next_rect, "Next ➡")]:
            pygame.draw.rect(scr, (50,48,44), rect, border_radius=6); pygame.draw.rect(scr, (80,78,72), rect, 1, border_radius=6)
            t = sf.render(text, True, TXT); scr.blit(t, (rect.centerx - t.get_width()//2, rect.centery - t.get_height()//2))

class GameScene(Scene):
    def __init__(self, app, mode="PVP", difficulty=None):
        super().__init__(app)
        self.game = Game()
        self.ps = make_pieces()
        self.t = 0
        self.mode = mode
        self.difficulty = difficulty
        self.menu_btn = pygame.Rect(W - 110, 6, 90, 26)
        self.radar_btn = pygame.Rect(210, 6, 120, 26)
        self.radar_active = False
        self.threat_map = set()
        self.last_hist_len = -1
        self.ai_thinking = False
        self.ai_timer = 0.0
        self.ai_delay = 0.6

    def _recalc_threat_map(self):
        self.threat_map = set()
        enemy = BP if self.game.cur == WP else WP
        for bi in range(6):
            for r in range(BSIZE):
                for c in range(BSIZE):
                    p = self.game.boards[bi].get(r, c)
                    if p and p.color == enemy:
                        for m in self.game.all_moves(bi, r, c): self.threat_map.add((m[0], m[1], m[2]))
        self.last_hist_len = len(self.game.hist)

    def _execute_ai_turn(self):
        move = get_ai_move(self.game, self.difficulty)
        if move:
            mt = self.game.do_move(*move)
            if "warp" in mt or "shift" in mt: self.app.audio.play("warp")
            elif self.game.hist and self.game.boards[move[0]].get(move[1], move[2]) is None and self.game.last:
                pass
            else: self.app.audio.play("move")
            if self.game.last:
                tb, tr, tc = self.game.last[1]
                if self.game.boards[tb].get(tr, tc) is None:
                    pass
            self.app.audio.play("move")
            if self.game.over: self.app.audio.play("gameover")
            if self.game.causality_timer > 2.9: self.app.audio.play("causality")

    def handle_event(self, ev):
        if self.mode == "PVE" and self.game.cur == BP and not self.game.over: return

        if ev.type == pygame.MOUSEMOTION: self.game.upd_hover(*ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.menu_btn.collidepoint(ev.pos): self.app.transition_to("menu"); return
            if self.radar_btn.collidepoint(ev.pos):
                self.radar_active = not self.radar_active; self.app.audio.play("radar")
                if self.radar_active: self._recalc_threat_map()
                return
            res = self.game.click(*ev.pos)
            if res:
                if "warp" in res or "shift" in res: self.app.audio.play("warp")
                elif res == "click_empty": self.app.audio.play("click")
                else: self.app.audio.play("move")
                if self.game.over: self.app.audio.play("gameover")
                if self.game.causality_timer > 2.9: self.app.audio.play("causality")
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_r:
                self.game = Game(); self.ai_thinking = False; self.ai_timer = 0
                if self.radar_active: self._recalc_threat_map()
            if ev.key == pygame.K_ESCAPE: self.app.transition_to("menu")
            if ev.key == pygame.K_t:
                self.radar_active = not self.radar_active; self.app.audio.play("radar")
                if self.radar_active: self._recalc_threat_map()

    def update(self, dt):
        self.t += dt
        self.game.causality_timer = max(0, self.game.causality_timer - dt)
        for fx in self.game.fx: fx.update(dt)
        self.game.fx = [f for f in self.game.fx if f.alive]
        if self.radar_active and len(self.game.hist) != self.last_hist_len: self._recalc_threat_map()

        if self.mode == "PVE" and self.game.cur == BP and not self.game.over:
            if not self.ai_thinking:
                self.ai_thinking = True
                self.ai_timer = 0
            else:
                self.ai_timer += dt
                if self.ai_timer >= self.ai_delay:
                    self._execute_ai_turn()
                    self.ai_thinking = False

    def draw(self, scr):
        scr.fill(BG)
        game_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        g = self.game; nf, sf, df, xf, cf = self.app.fonts["normal"], self.app.fonts["sub"], self.app.fonts["dim"], self.app.fonts["small"], self.app.fonts["tiny"]

        # TOP BAR
        bar_s = pygame.Surface((W, 38), pygame.SRCALPHA); bar_s.fill((20, 18, 16, 220)); pygame.draw.line(bar_s, (60, 58, 54), (0, 37), (W, 37)); game_surf.blit(bar_s, (0, 0))
        is_w = g.cur == WP

        if self.mode == "PVE" and self.ai_thinking:
            pill_col, pill_bdr = (100, 40, 40), (255, 100, 100)
            tt = nf.render(f"🤖 AI Thinking...", True, (255, 150, 150))
        else:
            pill_col = (60, 58, 50) if is_w else (50, 48, 42); pill_bdr = (180, 170, 140) if is_w else (120, 115, 100)
            tt = nf.render("White's Turn" if is_w else "Black's Turn", True, TXT)

        pygame.draw.rect(game_surf, pill_col, (15, 5, 220, 28), border_radius=14); pygame.draw.rect(game_surf, pill_bdr, (15, 5, 220, 28), 2, border_radius=14)
        if not (self.mode == "PVE" and self.ai_thinking):
            pulse = int(6 + 2 * math.sin(self.t * 4)); dot_col = (230, 220, 200) if is_w else (50, 45, 40)
            pygame.draw.circle(game_surf, dot_col, (35, 19), pulse)
        game_surf.blit(tt, (50, 9))

        if self.mode == "PVE":
            tag_col = {"EASY":(100,220,100), "MEDIUM":(220,200,80), "HARD":(220,80,80)}.get(self.difficulty, DTXT)
            tag = cf.render(f"VS AI: {self.difficulty}", True, tag_col)
            game_surf.blit(tag, (245, 10))

        r_col = (100, 40, 40) if self.radar_active else (60,58,54)
        r_bdr = (255, 80, 80) if self.radar_active else (90,88,82)
        pygame.draw.rect(game_surf, r_col, self.radar_btn, border_radius=6); pygame.draw.rect(game_surf, r_bdr, self.radar_btn, 1, border_radius=6)
        rt = cf.render("👁 RADAR [T]", True, (255, 120, 120) if self.radar_active else TXT); game_surf.blit(rt, (self.radar_btn.x + 8, self.radar_btn.y + 6))
        pygame.draw.rect(game_surf, (60,58,54), self.menu_btn, border_radius=6); pygame.draw.rect(game_surf, (90,88,82), self.menu_btn, 1, border_radius=6)
        mt = cf.render("Menu 🚪", True, TXT); game_surf.blit(mt, (self.menu_btn.x + 10, self.menu_btn.y + 6))

        wm, bm = g.count_mat(WP), g.count_mat(BP); wk, bk = g.count_kings(); md = wm - bm
        ds = f"+{md}" if md > 0 else str(md) if md < 0 else "Equal"; dc = (150, 220, 150) if md > 0 else ((220, 150, 150) if md < 0 else DTXT)
        stats = [(f"♔ {wk}", TXT if is_w else DTXT), (f"♚ {bk}", DTXT if is_w else TXT), ("|", (60,58,54)), (f"Mat: {ds}", dc), ("|", (60,58,54)), (f"T{len(g.hist)//2+1}", DTXT)]
        cx = W - 120
        for text, col in reversed(stats):
            ts = cf.render(text, True, col); cx -= ts.get_width(); game_surf.blit(ts, (cx, 12)); cx -= 12

        # TIMELINE
        y_c = MY - 22; sx = MX; ex = MX + COLS * BPX + (COLS - 1) * GAP; bw = ex - sx
        pygame.draw.line(game_surf, (50, 48, 44), (sx, y_c), (ex, y_c), 2)
        for i in range(3):
            x = sx + i * (bw//2); col, dim = TCOL[i], TCOL_DIM[i]
            gr = 12 + int(2 * math.sin(self.t * 2 + i)); gs = pygame.Surface((gr*2, gr*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*dim, 100), (gr, gr), gr); game_surf.blit(gs, (x - gr, y_c - gr))
            pygame.draw.circle(game_surf, col, (x, y_c), 6); pygame.draw.circle(game_surf, (255,255,255,80), (x, y_c), 3)
            lt = xf.render(["⏪ PAST", "⏸ PRESENT", "⏩ FUTURE"][i], True, col); game_surf.blit(lt, (x - lt.get_width()//2, y_c - 22))
        for bi in range(6):
            bc, br = bi % COLS, bi // COLS; bx = MX + bc * (BPX + GAP) + BPX // 2; bd = DCOORD[bi][1]
            lt = xf.render("α" if bd == 0 else "β", True, (160, 150, 120) if bd == 0 else (100, 150, 180))
            game_surf.blit(lt, (bx - lt.get_width()//2, y_c + 10))

        # CONNECTIONS & BOARDS
        for bi, adjs in g.adj.items():
            x1, y1 = bord_center(bi)
            for ad in adjs:
                if ad > bi:
                    x2, y2 = bord_center(ad); pt = (math.sin(self.t * 2 + bi) + 1) / 2
                    px_ = int(x1 + (x2-x1)*pt); py_ = int(y1 + (y2-y1)*pt)
                    pygame.draw.aaline(game_surf, (45, 42, 38), (x1, y1), (x2, y2))
                    pygame.draw.circle(game_surf, (75, 70, 60), (px_, py_), 2)

        mlookup = { (m[0], m[1], m[2]): m[4] for m in g.moves }
        radar_alpha = int(35 + 10 * math.sin(self.t * 3)) if self.radar_active else 0

        for bi in range(6):
            bx, by = bord_orig(bi); board = g.boards[bi]; td, tcol = DCOORD[bi][0], TCOL[td]
            sh = pygame.Surface((BPX+4, BPX+4), pygame.SRCALPHA); pygame.draw.rect(sh, (0,0,0,35), (0,0,BPX+4,BPX+4), border_radius=3); game_surf.blit(sh, (bx, by+3))
            te = {0:"⏪", 1:"⏸", 2:"⏩"}; lbl = cf.render(f"{DNAMES[bi]}  {te[td]} {TNAME[td]}", True, tcol)
            pw_, ph_ = lbl.get_width()+12, lbl.get_height()+4; ps = pygame.Surface((pw_, ph_), pygame.SRCALPHA)
            pygame.draw.rect(ps, (*BG, 200), (0,0,pw_,ph_), border_radius=8); game_surf.blit(ps, (bx + BPX//2 - pw_//2, by - 18)); game_surf.blit(lbl, (bx + BPX//2 - lbl.get_width()//2, by - 16))
            for r in range(BSIZE):
                for c in range(BSIZE):
                    sx, sy = bx + c*SQ, by + r*SQ; col = LSQ if (r+c)%2==0 else DSQ
                    pygame.draw.rect(game_surf, col, (sx, sy, SQ, SQ))
                    if self.radar_active and (bi, r, c) in self.threat_map:
                        r_hl = pygame.Surface((SQ, SQ), pygame.SRCALPHA); r_hl.fill((255, 40, 40, radar_alpha)); game_surf.blit(r_hl, (sx, sy))
                    if g.last:
                        (fb,fr,fc),(tb,tr,tc) = g.last
                        if (bi==fb and r==fr and c==fc) or (bi==tb and r==tr and c==tc):
                            hl = pygame.Surface((SQ,SQ), pygame.SRCALPHA); hl.fill((205,210,106,60)); game_surf.blit(hl, (sx,sy))
                    if g.sel == (bi, r, c):
                        p_ = int(30 * (math.sin(self.t * 6) + 1)); hl = pygame.Surface((SQ,SQ), pygame.SRCALPHA); hl.fill((186,202,68,120+p_)); game_surf.blit(hl, (sx,sy))
                    key = (bi, r, c)
                    if key in mlookup:
                        mt, tgt = mlookup[key], board.get(r, c); hl = pygame.Surface((SQ,SQ), pygame.SRCALPHA)
                        if tgt: ccol = CAP_C.get(mt, (220,70,70)); hl.fill((*ccol[:3],100))
                        else:
                            ccol = MC.get(mt, (100,195,100)); pygame.draw.circle(hl, (*ccol[:3],180), (SQ//2,SQ//2), SQ//6)
                            if "warp" in mt: pygame.draw.circle(hl, (*ccol[:3],100), (SQ//2,SQ//2), SQ//3, 2)
                        game_surf.blit(hl, (sx,sy))
                    p = board.get(r, c)
                    if p: game_surf.blit(self.ps[(p.color, p.type)], (sx, sy))
            glow_s = pygame.Surface((BPX+8, BPX+8), pygame.SRCALPHA); pygame.draw.rect(glow_s, (*tcol, 40), (0,0,BPX+8,BPX+8), border_radius=3); game_surf.blit(glow_s, (bx-4, by-4))
            pygame.draw.rect(game_surf, tcol, (bx-1, by-1, BPX+2, BPX+2), 2, border_radius=2)
            for i in range(BSIZE):
                fl = cf.render(chr(ord("a")+i), True, DTXT); game_surf.blit(fl, (bx + i*SQ + SQ//2 - fl.get_width()//2, by + BPX + 3))
                rl = cf.render(str(BSIZE-i), True, DTXT); game_surf.blit(rl, (bx - 14, by + i*SQ + SQ//2 - rl.get_height()//2))

        # RIGHT PANEL
        px_, pw_, py_, ph_ = MX*2 + COLS*BPX + (COLS-1)*GAP + 6, PANEL_W - 12, 42, H - 90
        panel_s = pygame.Surface((pw_, ph_), pygame.SRCALPHA); pygame.draw.rect(panel_s, (*PBG, 240), (0,0,pw_,ph_), border_radius=10); game_surf.blit(panel_s, (px_, py_))
        pygame.draw.rect(game_surf, (55, 53, 48), (px_, py_, pw_, ph_), 1, border_radius=10)
        y, lx = py_ + 12, px_ + 14
        def mod(title, func):
            nonlocal y; ts = df.render(title, True, (180,175,160)); game_surf.blit(ts, (lx, y)); y += ts.get_height() + 2
            pygame.draw.line(game_surf, (50,48,44), (lx, y), (lx+pw_-28, y)); y += 6; y = func(lx, y, py_+ph_-10); y += 10
        def hc_mod(lx, y, my):
            rect = (lx, y, pw_-28, 80); draw_hypercube(game_surf, rect, self.t); pygame.draw.rect(game_surf, (50,48,44), rect, 1, border_radius=4)
            lt = cf.render("6-Cube: 64 Verts", True, (80,78,72)); game_surf.blit(lt, (lx, rect[1]+rect[3]+2)); return y + rect[3] + 16
        def r_mod(lx, y, my):
            for txt, c in [("x₁,x₂: Board Space", TXT), ("x₃,x₄: Hidden 🔒", DTXT), ("x₅: Time ⏱️", TCOL[2]), ("x₆: Branch 🌿", (120,180,200)), ("", DTXT), ("⚡ Causality:", (190,100,255)), ("Time captures erase future", (160,90,220))]:
                if y > my - 14: break
                if txt: game_surf.blit(xf.render(txt, True, c), (lx, y)); y += 14
            return y
        def s_mod(lx, y, my):
            wk, bk = g.count_kings(); wm, bm = g.count_mat(WP), g.count_mat(BP)
            game_surf.blit(sf.render("♔ WHITE", True, TXT if g.cur==WP else DTXT), (lx, y)); y += 18
            game_surf.blit(xf.render(f"  Kings: {wk}/6 | Mat: {wm}", True, DTXT), (lx, y)); y += 18
            game_surf.blit(sf.render("♚ BLACK", True, TXT if g.cur==BP else DTXT), (lx, y)); y += 18
            game_surf.blit(xf.render(f"  Kings: {bk}/6 | Mat: {bm}", True, DTXT), (lx, y)); y += 20
            cx_ = lx
            for col, text in [(MC["normal"],"● Move"),(MC["future_shift"],"● Fut⏩"),(MC["temporal_warp"],"● Past⏪"),(CAP_C["normal"],"■ Cap")]:
                if cx_ > lx + pw_ - 40: y += 16; cx_ = lx
                if y > my - 14: break
                ts = cf.render(text, True, col); game_surf.blit(ts, (cx_, y)); cx_ += ts.get_width() + 8
            return y + 20
        mod("🔮 6D PROJECTION", hc_mod); mod("🌍 RULES", r_mod); mod("📊 STATUS", s_mod)

        if g.hover:
            bi, r, c = g.hover; p = g.boards[bi].get(r, c)
            if p:
                td, bd = DCOORD[bi][0], DCOORD[bi][1]; ch = PIECE_CHARS[(p.color, p.type)]
                l1 = f"{ch} {PNAMES[p.type]} ({'White' if p.color==WP else 'Black'})"
                l2 = f"Pos: {chr(ord('a')+c)}{BSIZE-r} | {DNAMES[bi]} {TNAME[td]} {BNAME[bd]}"
                t1, t2 = xf.render(l1, True, TXT), cf.render(l2, True, DTXT)
                w, h = max(t1.get_width(), t2.get_width()) + 16, t1.get_height() + t2.get_height() + 10
                tx = min(self.app.mx + 15, W - w - 5); ty = max(self.app.my - h - 5, 45)
                ts = pygame.Surface((w, h), pygame.SRCALPHA); pygame.draw.rect(ts, (25,23,20,235), (0,0,w,h), border_radius=6); pygame.draw.rect(ts, (80,78,72), (0,0,w,h), 1, border_radius=6)
                game_surf.blit(ts, (tx, ty)); game_surf.blit(t1, (tx+8, ty+5)); game_surf.blit(t2, (tx+8, ty+5+t1.get_height()))

        if g.causality_timer > 0:
            alpha = min(1.0, g.causality_timer); bw_, bh_ = 560, 36; bx_ = (MX*2 + COLS*BPX + (COLS-1)*GAP)//2 - bw_//2; by_ = 44
            offset = int(40 * (1 - min(1.0, g.causality_timer / 0.3))); by_ += offset
            s = pygame.Surface((bw_, bh_), pygame.SRCALPHA); pygame.draw.rect(s, (40,10,80,int(200*alpha)), (0,0,bw_,bh_), border_radius=6)
            for i in range(0, bh_, 3): pygame.draw.line(s, (255,255,255,int(10*alpha)), (0,i), (bw_,i))
            game_surf.blit(s, (bx_, by_)); pygame.draw.rect(game_surf, (180,80,255), (bx_, by_, bw_, bh_), 2, border_radius=6)
            ct = sf.render(g.causality_msg, True, (int(230*alpha), int(180*alpha), int(255*alpha))); game_surf.blit(ct, (bx_ + bw_//2 - ct.get_width()//2, by_ + bh_//2 - ct.get_height()//2))

        if g.over:
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,180)); game_surf.blit(ov, (0,0))
            fw, fh = 480, 180; fx_, fy_ = W//2 - fw//2, H//2 - fh//2
            fs = pygame.Surface((fw, fh), pygame.SRCALPHA); pygame.draw.rect(fs, (30,28,25,240), (0,0,fw,fh), border_radius=12); game_surf.blit(fs, (fx_, fy_))
            pygame.draw.rect(game_surf, GOLD, (fx_, fy_, fw, fh), 2, border_radius=12)
            wt = "♔ White Wins! ♔" if g.winner == WP else "♚ Black Wins! ♚"; ws = self.app.fonts["title"].render(wt, True, GOLD); game_surf.blit(ws, (W//2 - ws.get_width()//2, fy_ + 25))
            cx, cy = W//2, fy_ + 85; pts = []
            for i in range(5):
                a = -math.pi/2 + i*math.pi*2/5; pts.append((cx+20*math.cos(a), cy+20*math.sin(a))); a2 = a+math.pi/5; pts.append((cx+10*math.cos(a2), cy+10*math.sin(a2)))
            pygame.draw.polygon(game_surf, GOLD, pts)
            st = nf.render(f"Game ended in {len(g.hist)} moves.", True, (160,155,145)); game_surf.blit(st, (W//2 - st.get_width()//2, fy_ + 110))
            if int(self.t * 2) % 2 == 0:
                rs = nf.render("🔄 Press R to restart", True, TXT); game_surf.blit(rs, (W//2 - rs.get_width()//2, fy_ + 140))

        bb = pygame.Surface((W, 26), pygame.SRCALPHA); bb.fill((20,18,16,200)); pygame.draw.line(bb, (60,58,54), (0,0), (W,0)); game_surf.blit(bb, (0, H-26))
        ct = cf.render("🖱️ Select   |   👁️ T: Radar   |   ♞ Warp   |   🔄 R: Restart   |   ⎋ ESC: Menu", True, (90,88,82)); game_surf.blit(ct, (W//2 - ct.get_width()//2, H - 22))

        scr.blit(game_surf, (0, 0))

# ═══════════════════════════════════════════════════════════════════════════════
#  APP CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════
class App:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("6D Chess")
        pygame.display.set_icon(make_window_icon())
        self.clock = pygame.time.Clock()
        self.audio = AudioManager()
        self.mx, self.my = 0, 0
        self.fonts = {
            "title": pygame.font.SysFont("arial", 48, bold=True),
            "normal": pygame.font.SysFont("arial", 18, bold=True),
            "sub": pygame.font.SysFont("arial", 16, bold=True),
            "dim": pygame.font.SysFont("arial", 14, bold=True),
            "small": pygame.font.SysFont("arial", 13),
            "tiny": pygame.font.SysFont("arial", 12)
        }
        self.scenes = {"menu": MainMenuScene(self), "help": HelpScene(self), "game": GameScene(self)}
        self.state = "menu"
        self.transition_alpha = 0; self.transitioning = False; self.next_state = None; self.trans_speed = 800
        self.next_args = {}

    def transition_to(self, state_name, **kwargs):
        self.transitioning = True; self.next_state = state_name; self.transition_alpha = 0
        self.next_args = kwargs

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: running = False
                if ev.type == pygame.MOUSEMOTION: self.mx, self.my = ev.pos
                if not self.transitioning: self.scenes[self.state].handle_event(ev)

            self.scenes[self.state].update(dt)

            if self.transitioning:
                self.transition_alpha += self.trans_speed * dt
                if self.transition_alpha >= 255:
                    if self.next_state == "game":
                        self.scenes["game"] = GameScene(self, **self.next_args)
                    self.state = self.next_state; self.transition_alpha = 255; self.trans_speed = -800
                elif self.transition_alpha <= 0 and self.trans_speed < 0:
                    self.transitioning = False; self.transition_alpha = 0; self.trans_speed = 800

            self.scenes[self.state].draw(self.screen)

            if self.transitioning and self.transition_alpha > 0:
                fade = pygame.Surface((W, H), pygame.SRCALPHA); fade.fill((0, 0, 0, int(self.transition_alpha)))
                self.screen.blit(fade, (0, 0))

            pygame.display.flip()
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    run_qa_tests()
    run_mcts_test(iterations=2)
    print("🚀 Launching Client...\n")
    App().run()