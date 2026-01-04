import tkinter as tk
import customtkinter as ctk
from db.db_queries import get_deck_bonus
from gui.theme import BG_MEDIUM, TEXT_PRIMARY

class DeckView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Deck Builder")
        self.geometry("500x400")

        self.deck_id = 1  # Default deck

        ctk.CTkButton(self, text="Calculate Deck Bonuses", command=self.calculate).pack(pady=10)
        self.output = ctk.CTkTextbox(self, height=300, fg_color=BG_MEDIUM, text_color=TEXT_PRIMARY)
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def calculate(self):
        self.output.delete("1.0", tk.END)
        bonuses = get_deck_bonus(self.deck_id)
        if not bonuses:
            self.output.insert(tk.END, "No bonuses found for this deck.\n")
            return
        for bonus, total in bonuses:
            self.output.insert(tk.END, f"{bonus}: +{total}\n")
