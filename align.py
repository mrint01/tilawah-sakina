"""Find ayah start/end times inside a whole-surah recording that has no published timings.

The reference is the same reciter's per-ayah files from everyayah.com (same text, a different
performance). Each reference ayah is matched into the long recording with subsequence DTW on
normalised MFCC features, one ayah after the other, then every cut is moved into the nearest pause.

    python3 align.py <surah.mp3> <everyayah folder> <surah>     # prints the timings as JSON
"""
import json
import subprocess
import sys

import numpy as np

SR = 16000
HOP = 160          # 10 ms frames
WIN = 400          # 25 ms window
N_MELS, N_MFCC = 40, 13


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def _mel_bank():
    def hz2mel(f): return 2595 * np.log10(1 + f / 700)
    def mel2hz(m): return 700 * (10 ** (m / 2595) - 1)
    nfft = 512
    pts = mel2hz(np.linspace(hz2mel(60), hz2mel(7600), N_MELS + 2))
    bins = np.floor((nfft + 1) * pts / SR).astype(int)
    fb = np.zeros((N_MELS, nfft // 2 + 1), np.float32)
    for m in range(1, N_MELS + 1):
        a, b, c = bins[m - 1], bins[m], bins[m + 1]
        fb[m - 1, a:b] = (np.arange(a, b) - a) / max(1, b - a)
        fb[m - 1, b:c] = (c - np.arange(b, c)) / max(1, c - b)
    k = np.arange(N_MELS)
    dct = np.cos(np.pi / N_MELS * (k + 0.5)[None, :] * np.arange(N_MFCC)[:, None])
    return fb, dct


FB, DCT = _mel_bank()


def features(x):
    """MFCC (without c0) + log energy per 10 ms frame, and the energy alone (for finding pauses)."""
    n = 1 + max(0, (len(x) - WIN) // HOP)
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[np.minimum(idx, len(x) - 1)] * np.hanning(WIN)
    spec = np.abs(np.fft.rfft(frames, 512)) ** 2
    mel = np.log(spec @ FB.T + 1e-8)
    mfcc = mel @ DCT.T
    energy = 10 * np.log10((frames ** 2).mean(1) + 1e-10)
    return mfcc[:, 1:], energy


def cmvn(f):
    return (f - f.mean(0)) / (f.std(0) + 1e-6)


def subseq_dtw(ref, tgt):
    """Best match of all of ref inside tgt (open begin and end). Steps per ref frame: 0, 1 or 2 target frames.
    Returns (start, end) target frame indices and the mean cost."""
    cost = 1 - (ref / np.linalg.norm(ref, axis=1, keepdims=True)) @ (tgt / np.linalg.norm(tgt, axis=1, keepdims=True)).T
    n, m = cost.shape
    D = cost[0].copy()
    S = np.arange(m)
    for i in range(1, n):
        c0 = D                                     # stay on the same target frame
        c1 = np.r_[np.inf, D[:-1]]                 # one target frame
        c2 = np.r_[np.inf, np.inf, D[:-2]]         # two target frames
        stack = np.vstack([c1, c0 + 0.15, c2 + 0.15])  # small penalty keeps the slope near 1
        k = stack.argmin(0)
        D = stack[k, np.arange(m)] + cost[i]
        S = np.where(k == 0, np.r_[0, S[:-1]], np.where(k == 1, S, np.r_[0, 0, S[:-2]]))
    end = int(D.argmin())
    return int(S[end]), end, float(D[end] / n)


def snap(energy, t, radius=40):
    """Move a cut to the quietest 10 ms frame within +-radius frames."""
    lo, hi = max(0, t - radius), min(len(energy), t + radius + 1)
    sm = np.convolve(energy, np.ones(5) / 5, mode="same")
    return lo + int(sm[lo:hi].argmin())


def find_pauses(energy):
    """Pauses: runs of frames well below the local speech level. Returns [(centre, length, depth)]."""
    sm = np.convolve(energy, np.ones(15) / 15, mode="same")
    level = np.convolve(energy, np.ones(301) / 301, mode="same")   # ~3 s local loudness
    quiet = sm < level - 9
    out, i, n = [], 0, len(quiet)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            seg = sm[i:j]
            out.append(((i + j) // 2, j - i, float(level[(i + j) // 2] - seg.min())))
            i = j
        else:
            i += 1
    return out


def best_pause(pauses, t, energy, radius=300):
    """The pause near frame t that looks most like an ayah end: long and deep, and not far away."""
    best, score = None, -1e9
    for c, length, depth in pauses:
        d = abs(c - t)
        if d > radius:
            continue
        s = min(length, 60) * 0.6 + depth * 1.0 - d * 0.12
        if s > score:
            best, score = c, s
    return best if best is not None else snap(energy, t, 40)


def global_cuts(pauses, guess, expect, first, last):
    """Dynamic programming over pause candidates: choose len(guess) cuts, in order."""
    # every detected pause, plus the DTW boundaries themselves (a few short ayahs have no clear pause between them)
    cand = sorted({c[0]: c for c in [(g, 0, 0.0) for g in guess] + list(pauses)}.values())
    cand = [(first, 0, 0.0)] + [c for c in cand if first + 30 < c[0] < last - 30]
    pos = np.array([c[0] for c in cand], float)
    strength = np.array([min(c[1], 60) / 60 + c[2] / 20 for c in cand])
    K, M = len(guess), len(cand)
    INF = 1e18
    cost = np.full((K + 1, M), INF)
    back = np.zeros((K + 1, M), int)
    cost[0, 0] = 0
    for k in range(1, K + 1):
        e = expect[k - 1]
        for j in range(1, M):
            d = pos[j] - pos[:j]
            ok = (d > 0.35 * e) & (d < 2.6 * e) & (cost[k - 1, :j] < INF)
            if not ok.any():
                continue
            c = cost[k - 1, :j] + 6 * np.log(np.maximum(d, 1) / e) ** 2
            c = np.where(ok, c, INF)
            i = int(c.argmin())
            cost[k, j] = c[i] + 1.5 * (1 - min(1, strength[j])) + ((pos[j] - guess[k - 1]) / 400) ** 2
            back[k, j] = i
    # the last ayah has to fit between the final cut and the end of the recording
    tail = last - pos
    final = cost[K] + 6 * np.log(np.maximum(tail, 1) / expect[-1]) ** 2 if len(expect) > K else cost[K]
    j = int(np.argmin(final))
    out = []
    for k in range(K, 0, -1):
        out.append(int(pos[j]))
        j = back[k, j]
    return out[::-1]


def align(surah_mp3, ref_paths):
    """ref_paths: the reference ayah files 1..N in order. Returns [{ayah, start_time, end_time}] in ms."""
    x = load(surah_mp3)
    tf, energy = features(x)
    tf = cmvn(tf)
    refs = [cmvn(features(load(p))[0]) for p in ref_paths]
    total_ref = sum(len(r) for r in refs)
    rate = len(tf) / (total_ref * 1.08)            # this recording vs the reference (the 8 % covers basmala etc.)
    spans, pos = [], 0
    for i, r in enumerate(refs):
        expect = int(len(r) * rate)
        lo = max(0, pos - 50)
        hi = min(len(tf), pos + (3000 if i == 0 else 0) + int(expect * 2.2) + 200)
        s, e, c = subseq_dtw(r, tf[lo:hi])
        spans.append([lo + s, lo + e, c])
        pos = lo + e
    # Global fit: every inner cut sits on a real pause; together the cuts keep each ayah's length in
    # proportion to the reference and stay close to where the DTW match put the boundary.
    first = snap(energy, spans[0][0], 30)
    last = min(len(energy) - 1, snap(energy, spans[-1][1], 40))
    guess = [(a[1] + b[0]) // 2 for a, b in zip(spans, spans[1:])]
    lens = np.array([len(r) for r in refs], float)
    rate2 = (last - first) / lens.sum()
    cuts = [first] + global_cuts(find_pauses(energy), guess, lens * rate2, first, last) + [last]
    out = []
    for i in range(len(refs)):
        out.append({"ayah": i + 1, "start_time": cuts[i] * 10, "end_time": cuts[i + 1] * 10,
                    "match": round(1 - spans[i][2], 3)})
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    import make_reel
    mp3, folder, s = sys.argv[1], sys.argv[2], int(sys.argv[3])
    n = make_reel.chapters()[s]["verses_count"]
    refs = [make_reel.audio(folder, s, a) for a in range(1, n + 1)]
    print(json.dumps(align(mp3, refs)))
