```python
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from datetime import datetime

class ClimaVivoApp:
def __init__(self, root):
self.root = root
self.root.title("Jarvis Next - Clima Vivo")
self.root.geometry("800x600")
self.root.configure(bg="#1a1a2e")

# Estilos
style = ttk.Style()
style.theme_use('clam')
style.configure("Title.TLabel", font=("Arial", 24, "bold"), foreground="#4ecca3")
style.configure("Data.TLabel", font=("Arial", 16), foreground="#e94560")

# Header
header = ttk.Label(root, text="🌤️ Clima Vivo | Jarvis Next", style="Title.TLabel", padding=(20, 10))
header.grid(row=0, column=0, sticky="ew")

# Área de Dados (Simulada com dados públicos recentes para demonstração)
self.dados_clima = {
"temp": "24°C",
"sensacao": "26°C",
"condicao": "Parcialmente Nublado com Chuvas Terciárias",
"umidade": "65%",
"vento": "12 km/h (Sul)",
"prognose_48h": [
{"hora": "14:00", "temp": "24°C", "desc": "Nublado"},
{"hora": "15:00", "temp": "23°C", "desc": "Chuva Fraca"},
{"hora": "16:00", "temp": "22°C", "desc": "Chuva Moderada"},
{"hora": "17:00", "temp": "21°C", "desc": "Nublado"}
]
}

# Painel Principal
panel = ttk.LabelFrame(root, text="Resumo Atualizado", padding=15)
panel.grid(row=1, column=0, sticky="nsew")

# Grid interno do painel
panel.columnconfigure(0, weight=1)
panel.rowconfigure(0, weight=1)

# Temperatura Grande
ttk.Label(panel, text=f"Temperatura: {self.dados_clima['temp']}", style="Data.TLabel", font=("Arial", 28)).grid(row=0, column=0, sticky="w")

# Descrição
desc_text = f"{self.dados_clima['condicao']} • Sensação térmica: {self.dados_clima['sensacao']}°C"
ttk.Label(panel, text=desc_text, style="Data.TLabel", font=("Arial", 14)).grid(row=1, column=0, sticky="w")

# Detalhes
detalhes = f"Umidade: {self.dados_clima['umidade']} | Vento: {self.dados_clima['vento']}"
ttk.Label(panel, text

# Rodapé
        ttk.Label(panel, text="Jarvis Next - Clima Vivo", style="Data.TLabel", font=("Arial", 12)).grid(row=3, column=0, sticky="w")
        # Loop principal da janela
        self.root.mainloop()

if __name__ == "__main__":
    app = ClimaVivoApp()
    app.run()