# 🐦 Flappy Bird GG

A faithful recreation of the classic **Flappy Bird** game, built entirely in Python using [Flet](https://flet.dev) — a framework that lets you build interactive multi-platform apps (desktop, web, and mobile) with a single Python codebase powered by Flutter under the hood.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flet](https://img.shields.io/badge/Flet-UI%20Framework-00C853)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 About

Flappy Bird GG reimagines the original mobile sensation with smooth physics, responsive controls, and clean, animated visuals — all without relying on a traditional game engine. Tap, click, or press a key to keep the bird airborne and dodge an endless stream of pipes.

---

## ✨ Features

- **Classic gravity-based flight mechanics** — the bird continuously falls and flaps upward on input, just like the original
- **Tap / Click / Spacebar controls** — works across desktop, web, and mobile builds
- **Procedurally generated pipes** with randomized gaps and spacing for endless replayability
- **Pixel-perfect collision detection** between the bird, pipes, ground, and ceiling
- **Live score counter** that increments as the bird passes through each pipe
- **High score tracking** — persists your best run across sessions
- **Day/night parallax scrolling background** for visual depth
- **Scrolling ground texture** synced to game speed
- **Bird flap animation** with rotation based on velocity (nose-dives and climbs)
- **Game states** — Start Screen → Playing → Game Over, with smooth transitions
- **Restart on tap** from the Game Over screen, no menu diving required
- **Sound effects** for flapping, scoring, and collisions, powered by `pygame.mixer` on desktop for low-latency audio playback
- **Progressive difficulty** — pipe gap and speed can scale as your score increases
- **Responsive layout** that adapts to different window sizes and aspect ratios
- **Cross-platform** — run as a native desktop app, in the browser, or packaged for mobile

---

## 🛠️ Tech Stack

| Component           | Technology                                                               |
| ------------------- | ------------------------------------------------------------------------ |
| Language            | Python 3.10+                                                             |
| UI / Game Framework | [Flet](https://flet.dev) (Flutter-powered)                               |
| Game Loop           | Flet's `Canvas` / animation tick handlers                                |
| Audio (Desktop)     | `pygame.mixer` — low-latency sound playback for flap/score/collision SFX |
| Packaging           | `flet build` (for desktop/mobile/web distribution)                       |

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- `pip`

### Steps

```bash
# Clone the repository
git clone https://github.com/<Adil-Tayyab>/flappy-bird-gg.git
cd flappy-bird-gg

# (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### `requirements.txt`

```
flet
pygame
```

---

## ▶️ Running the Game

```bash
python main.py
```

This launches the game in a native desktop window by default. To run it in a browser instead:

```bash
flet run --web main.py
```

> **Note:** Sound is handled via `pygame.mixer`, which only works in the native desktop build. The web build currently runs silently (or falls back to Flet's `Audio` control, not implemented yet) since `pygame` doesn't run in a browser environment.

---

## 🎮 Controls

| Action      | Input                           |
| ----------- | ------------------------------- |
| Flap / Jump | `Space`, Left Click, or Tap     |
| Start Game  | Click / Tap on Start Screen     |
| Restart     | Click / Tap on Game Over Screen |

---

## 📁 Project Structure

```
flappy-bird-gg/
├── src/                # App entry point & game loop
        ├── assets/
                  ├── icon.ico
                  ├── splash_android.png
                  ├── spriteSheet.png
                  ├── audio/             # contains collision, flap, death sounds
                  └── fonts/              # Game UI fonts
        ├── main.py
        ├── requirements.txt
├── pyproject.toml
├── regions.json
├── uv.lock
├── requirements.txt
└── README.md
```

---

## 🚀 Building for Distribution

Flet supports packaging into standalone apps:

```bash
# Desktop (Windows/macOS/Linux)
flet build windows   # or macos / linux

# Web
flet build web

# Mobile
flet build apk       # Android
flet build ipa        # iOS
```

---

## 🗺️ Roadmap

- [O] Multiple bird skins / unlockables
- [X] Online leaderboard
- [X] Difficulty/game modes (Easy, Classic, Hardcore)
- [O] Theming (day/night toggle)
- [O] Achievements system

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m "Add amazing feature"`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by the original **Flappy Bird** by Dong Nguyen / .GEARS
- Built with [Flet](https://flet.dev) — Python UI framework powered by Flutter
