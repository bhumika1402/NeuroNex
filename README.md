# Neuromorphic NPC System

A pygame-based 2D shooter game where enemies adapt to your playstyle in real-time using AI.

---

## Features

- Adaptive NPC difficulty powered by a local AI backend
- Real-time behavior adjustment every 5 seconds based on your performance
- NPC intelligence bar showing how much the AI has learned
- Bonus ammo system and kill-based win condition
- Clean HUD showing accuracy, lives, ammo, and NPC stats

---

## Tech Stack

- **Python 3**
- **Pygame** — game rendering and input
- **Requests** — communication with local AI backend
- **Flask** *(backend)* — receives player stats and returns NPC parameters
- **Threading** — non-blocking API calls during gameplay

---

## Project Structure
neuromorphic-npc/

│

├── game.py          # Main game loop, player, NPC, bullet logic

├── ai_brain.py        # Flask backend that adjusts NPC parameters

├── api.py         # Helper functions

└── README.md

**## How to Play**
You are the blue circle. Your goal is to kill 10 glowing enemies before you run out of lives or bullets.
Move around the screen using W A S D or the arrow keys. Point your mouse cursor at an enemy and press Spacebar to shoot a bullet in that direction. A yellow aim line shows exactly where your next shot will go.
You start with 100 bullets and 2 lives. Press R once at any time to claim 50 bonus bullets. Use them wisely because once they are gone, if enemies are still alive, the game ends.
Enemies patrol randomly until you get close. Once you enter their vision range they will chase you and start firing. Dodge the orange bullets or your HP will drop. If your HP hits zero you lose a life and respawn at the center.
Every 5 seconds the enemies analyze your reaction time, accuracy and movement speed and adjust their behavior automatically. The faster and more accurate you play, the harder they become.
