import tkinter as tk
from db.db_queries import get_deck_bonus

class DeckView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Deck Builder")
        self.geometry("500x400")

        self.deck_id = 1  # Default deck

        tk.Button(self, text="Calculate Deck Bonuses", command=self.calculate).pack(pady=10)
        self.output = tk.Text(self, height=20)
        self.output.pack(fill=tk.BOTH, expand=True)

    def calculate(self):
        self.output.delete("1.0", tk.END)
        bonuses = get_deck_bonus(self.deck_id)
        if not bonuses:
            self.output.insert(tk.END, "No bonuses found for this deck.\n")
            return
        for bonus, total in bonuses:
            self.output.insert(tk.END, f"{bonus}: +{total}\n")
