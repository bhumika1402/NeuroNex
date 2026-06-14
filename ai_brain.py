import numpy as np

class NPCBrain:
    def __init__(self):
        self.difficulty = 0.3        # starts easy
        self.learning_rate = 0.08
        self.history = []

    def update(self, player_data):
        reaction   = max(0, 1 - player_data.get("reaction_time_ms", 500) / 1000)
        accuracy   = player_data.get("hit_accuracy", 0.5)
        speed      = min(1, player_data.get("avg_speed", 3) / 8)
        deaths     = max(0, 1 - player_data.get("death_count", 0) / 5)

        # Weighted skill score
        skill_score = (reaction * 0.3 + accuracy * 0.4 +
                       speed * 0.15 + deaths * 0.15)

        # Smoothly nudge difficulty toward player's skill
        self.difficulty += self.learning_rate * (skill_score - self.difficulty)
        self.difficulty = float(np.clip(self.difficulty, 0.05, 1.0))

        self.history.append(round(self.difficulty, 3))
        if len(self.history) > 50:
            self.history.pop(0)

        return self.difficulty

    def get_npc_params(self):
        d = self.difficulty
        return {
            "speed":        round(1.5 + d * 4.5, 2),     # 1.5 to 6.0
            "aggression":   round(d, 2),                  # 0 to 1
            "attack_rate":  round(0.5 + d * 2.5, 2),     # 0.5 to 3.0
            "vision_range": round(100 + d * 200, 1),      # 100 to 300 px
            "prediction":   round(d * 0.8, 2),            # how well it predicts player
            "difficulty":   round(d, 2),
            "history":      self.history
        }