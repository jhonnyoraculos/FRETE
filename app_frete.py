"""
Interface moderna para a Calculadora de Custo JR (Tkinter/ttk).
"""

from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import frete_calculo


class App:
    """Camada visual do aplicativo."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Calculadora de Custo JR")
        self.root.geometry("820x900")
        self.root.minsize(720, 780)
        self.root.resizable(True, True)

        self.style = ttk.Style(self.root)
        self._setup_style()

        self.placas = self._carregar_placas()
        self._build_header()
        self._build_form()
        self._build_actions()
        self._build_output()
        self.bind_events()
        self._iniciar_precarregamento_dados()

    def _setup_style(self) -> None:
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.option_add("*Font", ("Segoe UI", 10))

        self.color_bg = "#172a45"
        self.color_header = "#14263e"
        self.color_card = "#234066"
        self.color_border = "#2f4f77"
        self.color_primary = "#2ea8ff"
        self.color_primary_hover = "#1f8de0"
        self.color_primary_active = "#1b6db2"
        self.color_secondary = "#2b4c75"
        self.color_text = "#e2e8f0"
        self.color_muted = "#b3c3d7"
        self.color_input_bg = "#f8fafc"
        self.color_input_text = "#0f172a"

        self.root.configure(background=self.color_bg)
        self.style.configure("App.TFrame", background=self.color_bg)
        self.style.configure("Header.TFrame", background=self.color_header)
        self.style.configure(
            "Card.TLabelframe",
            padding=12,
            relief="solid",
            borderwidth=1,
            background=self.color_card,
        )
        self.style.configure(
            "Card.TLabelframe.Label",
            font=("Segoe UI", 10, "bold"),
            foreground=self.color_primary,
            background=self.color_card,
        )
        self.style.configure("Card.TFrame", background=self.color_card)
        self.style.configure(
            "Total.TFrame",
            background=self.color_card,
            relief="solid",
            borderwidth=1,
        )
        self.style.configure(
            "TotalTitle.TLabel",
            font=("Segoe UI", 9, "bold"),
            foreground=self.color_muted,
            background=self.color_card,
        )
        self.style.configure(
            "TotalValue.TLabel",
            font=("Segoe UI", 18, "bold"),
            foreground=self.color_primary,
            background=self.color_card,
        )
        self.style.configure(
            "Title.TLabel",
            font=("Segoe UI", 16, "bold"),
            foreground=self.color_text,
            background=self.color_header,
        )
        self.style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 9),
            foreground=self.color_muted,
            background=self.color_header,
        )
        self.style.configure(
            "Card.Subtitle.TLabel",
            font=("Segoe UI", 9),
            foreground=self.color_muted,
            background=self.color_card,
        )
        self.style.configure("Header.Info.TLabel", foreground=self.color_muted, background=self.color_header)
        self.style.configure("Header.Error.TLabel", foreground="#fecaca", background=self.color_header)
        self.style.configure("Card.TLabel", foreground=self.color_text, background=self.color_card)

        self.style.configure(
            "TEntry",
            padding=6,
            fieldbackground=self.color_input_bg,
            foreground=self.color_input_text,
        )
        self.style.configure(
            "TCombobox",
            padding=4,
            fieldbackground=self.color_input_bg,
            foreground=self.color_input_text,
            arrowcolor=self.color_input_text,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.color_input_bg)],
            foreground=[("readonly", self.color_input_text)],
        )
        self.style.configure("Invalid.TEntry", fieldbackground="#fca5a5")
        self.style.configure("Invalid.TCombobox", fieldbackground="#fca5a5")

        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            foreground="#ffffff",
            background=self.color_primary,
            bordercolor=self.color_primary,
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", self.color_primary_hover), ("pressed", self.color_primary_active)],
            bordercolor=[("active", self.color_primary_hover), ("pressed", self.color_primary_active)],
            foreground=[("disabled", "#e2e8f0")],
        )
        self.style.configure(
            "Secondary.TButton",
            foreground=self.color_text,
            background=self.color_secondary,
            bordercolor=self.color_border,
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#274366"), ("pressed", "#1f3657")],
            bordercolor=[("active", "#274366"), ("pressed", "#1f3657")],
        )
        self.style.configure("Card.TCheckbutton", background=self.color_card, foreground=self.color_text)
        self.style.configure("TPanedwindow", background=self.color_bg)

    def _carregar_placas(self) -> list[str]:
        placas_permitidas = self._ler_placas_permitidas()
        if placas_permitidas:
            return placas_permitidas
        try:
            import frete_dados

            return frete_dados.get_lista_placas()
        except Exception as exc:  # pragma: no cover - interface interativa
            messagebox.showerror(
                "Erro ao carregar placas",
                f"Nao foi possivel carregar as placas.\nDetalhes: {exc}",
            )
            return []

    def _iniciar_precarregamento_dados(self) -> None:
        if frete_calculo.dados_carregados():
            return
        self._set_message("Carregando planilhas em segundo plano...", erro=False)
        threading.Thread(target=self._precarregar_dados, daemon=True).start()

    def _agendar_ui(self, callback) -> None:
        try:
            self.root.after(0, callback)
        except (RuntimeError, tk.TclError):
            pass

    def _precarregar_dados(self) -> None:
        try:
            frete_calculo.get_dados()
        except Exception as exc:  # pragma: no cover - interface interativa
            texto = f"Falha ao carregar planilhas: {exc}"
            self._agendar_ui(lambda: self._set_message(texto, erro=True))
            return
        self._agendar_ui(self._on_dados_precarregados)

    def _on_dados_precarregados(self) -> None:
        if self.message_var.get() == "Carregando planilhas em segundo plano...":
            self._set_message("Planilhas carregadas. Aplicativo pronto.", erro=False)

    def _ler_placas_permitidas(self) -> list[str]:
        arquivo = Path(__file__).resolve().parent / "placas_permitidas.txt"
        if not arquivo.exists():
            return []
        conteudo = arquivo.read_text(encoding="utf-8")
        placas: list[str] = []
        visto: set[str] = set()
        for linha in conteudo.splitlines():
            placa = linha.strip().replace(" ", "").upper()
            if not placa or placa in visto:
                continue
            placas.append(placa)
            visto.add(placa)
        return placas

    def _build_header(self) -> None:
        self.main_frame = ttk.Frame(self.root, padding=12, style="App.TFrame")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header = ttk.Frame(self.main_frame, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)

        logo_path = Path(__file__).resolve().parent / "logo-jr.png"
        if logo_path.exists():
            try:
                self.logo_img = tk.PhotoImage(file=str(logo_path))
                self.root.iconphoto(True, self.logo_img)
                ttk.Label(header, image=self.logo_img).grid(
                    row=0, column=0, rowspan=2, sticky="w", padx=(0, 10)
                )
            except tk.TclError:
                self.logo_img = None

        ttk.Label(header, text="Calculadora de Custo JR", style="Title.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(
            header,
            text="Preencha os dados e clique em Calcular custo.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        self.message_var = tk.StringVar(value="")
        self.message_label = ttk.Label(
            header, textvariable=self.message_var, style="Header.Info.TLabel"
        )
        self.message_label.grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Separator(self.main_frame, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=(0, 10)
        )

    def _build_form(self) -> None:
        self.card_form = ttk.LabelFrame(
            self.main_frame, text="Dados do custo", style="Card.TLabelframe", padding=10
        )
        self.card_form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.card_form.columnconfigure(1, weight=1)

        ttk.Label(self.card_form, text="Placa:", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.placa_var = tk.StringVar()
        self.placa_combo = ttk.Combobox(
            self.card_form, values=self.placas, textvariable=self.placa_var, state="readonly", width=26
        )
        self.placa_combo.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(self.card_form, text="Distancia (km):", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.distancia_var = tk.StringVar()
        self.entry_distancia = ttk.Entry(self.card_form, textvariable=self.distancia_var)
        self.entry_distancia.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(self.card_form, text="Peso (t):", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.peso_var = tk.StringVar()
        self.entry_peso = ttk.Entry(self.card_form, textvariable=self.peso_var)
        self.entry_peso.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(self.card_form, text="Colaboradores:", style="Card.TLabel").grid(
            row=3, column=0, sticky="w", pady=4
        )
        self.colaboradores_var = tk.StringVar()
        self.entry_colaboradores = ttk.Entry(
            self.card_form, textvariable=self.colaboradores_var
        )
        self.entry_colaboradores.grid(row=3, column=1, sticky="ew", pady=4)

        self.var_pedagio = tk.BooleanVar(value=False)
        self.var_reserva = tk.BooleanVar(value=True)
        options = ttk.Frame(self.card_form, style="Card.TFrame")
        options.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            options, text="Incluir pedagio", variable=self.var_pedagio, style="Card.TCheckbutton"
        ).grid(
            row=0, column=0, sticky="w", padx=(0, 16)
        )
        ttk.Checkbutton(
            options, text="Incluir hoteis", variable=self.var_reserva, style="Card.TCheckbutton"
        ).grid(
            row=0, column=1, sticky="w"
        )

        self._vcmd_float = (self.root.register(self._validate_float_text), "%P")
        self._vcmd_int = (self.root.register(self._validate_int_text), "%P")
        self.entry_distancia.configure(validate="key", validatecommand=self._vcmd_float)
        self.entry_peso.configure(validate="key", validatecommand=self._vcmd_float)
        self.entry_colaboradores.configure(validate="key", validatecommand=self._vcmd_int)

    def _build_actions(self) -> None:
        self.card_actions = ttk.LabelFrame(
            self.main_frame, text="Acoes", style="Card.TLabelframe", padding=10
        )
        self.card_actions.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.card_actions.columnconfigure((0, 1), weight=1)

        self.btn_calcular = ttk.Button(
            self.card_actions, text="Calcular custo", command=self.on_calcular, style="Primary.TButton"
        )
        self.btn_calcular.grid(row=0, column=0, padx=6, pady=6, sticky="ew", ipady=2)

        self.btn_limpar = ttk.Button(
            self.card_actions, text="Limpar campos", command=self.on_limpar, style="Secondary.TButton"
        )
        self.btn_limpar.grid(row=0, column=1, padx=6, pady=6, sticky="ew", ipady=2)

    def _build_output(self) -> None:
        self.panes = ttk.Panedwindow(self.main_frame, orient="vertical")
        self.panes.grid(row=4, column=0, sticky="nsew")

        self.card_result = ttk.LabelFrame(
            self.panes, text="Resumo do custo", style="Card.TLabelframe", padding=10
        )
        self.card_result.columnconfigure(0, weight=1)
        self.card_result.rowconfigure(1, weight=1)

        top_row = ttk.Frame(self.card_result, style="Card.TFrame")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_row.columnconfigure(0, weight=1)
        left_header = ttk.Frame(top_row, style="Card.TFrame")
        left_header.grid(row=0, column=0, sticky="w")
        ttk.Label(left_header, text="Resumo do custo", style="Card.Subtitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            left_header, text="Copiar resumo", command=self.on_copiar, style="Secondary.TButton"
        ).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )

        self.total_var = tk.StringVar(value="R$ 0,00")
        total_box = ttk.Frame(top_row, style="Total.TFrame", padding=(10, 6))
        total_box.grid(row=0, column=1, sticky="e")
        ttk.Label(total_box, text="TOTAL DO CUSTO", style="TotalTitle.TLabel").grid(
            row=0, column=0, sticky="e"
        )
        ttk.Label(total_box, textvariable=self.total_var, style="TotalValue.TLabel").grid(
            row=1, column=0, sticky="e"
        )

        self.text_resultado = tk.Text(
            self.card_result,
            height=16,
            wrap="word",
            state="disabled",
            padx=8,
            pady=8,
            font=("Consolas", 10),
            background=self.color_header,
            foreground=self.color_text,
            insertbackground=self.color_text,
            selectbackground=self.color_primary,
            highlightthickness=1,
            highlightbackground=self.color_border,
        )
        scroll_resultado = ttk.Scrollbar(
            self.card_result, orient="vertical", command=self.text_resultado.yview
        )
        self.text_resultado.configure(yscrollcommand=scroll_resultado.set)
        self.text_resultado.grid(row=1, column=0, sticky="nsew")
        scroll_resultado.grid(row=1, column=1, sticky="ns")

        self.card_metricas = ttk.LabelFrame(
            self.panes, text="Metricas", style="Card.TLabelframe", padding=10
        )
        self.card_metricas.columnconfigure(0, weight=1)
        self.card_metricas.rowconfigure(0, weight=1)

        self.text_metricas = tk.Text(
            self.card_metricas,
            height=8,
            wrap="word",
            state="disabled",
            padx=8,
            pady=8,
            font=("Consolas", 10),
            background=self.color_header,
            foreground=self.color_text,
            insertbackground=self.color_text,
            selectbackground=self.color_primary,
            highlightthickness=1,
            highlightbackground=self.color_border,
        )
        scroll_metricas = ttk.Scrollbar(
            self.card_metricas, orient="vertical", command=self.text_metricas.yview
        )
        self.text_metricas.configure(yscrollcommand=scroll_metricas.set)
        self.text_metricas.grid(row=0, column=0, sticky="nsew")
        scroll_metricas.grid(row=0, column=1, sticky="ns")

        self.panes.add(self.card_result, weight=3)
        self.panes.add(self.card_metricas, weight=2)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(4, weight=1)

    def bind_events(self) -> None:
        self.root.bind("<Return>", self._on_enter)
        self.root.bind("<Escape>", self._on_escape)
        for widget in (
            self.placa_combo,
            self.entry_distancia,
            self.entry_peso,
            self.entry_colaboradores,
        ):
            widget.bind("<FocusIn>", lambda _event: self._clear_message())

    def _on_enter(self, event: tk.Event) -> None:
        if isinstance(event.widget, tk.Text):
            return
        self.on_calcular()

    def _on_escape(self, _event: tk.Event) -> None:
        self.on_limpar()

    def _validate_float_text(self, value: str) -> bool:
        if value == "":
            return True
        texto = value.replace(",", ".")
        if texto.count(".") > 1:
            return False
        return all(ch.isdigit() or ch == "." for ch in texto)

    def _validate_int_text(self, value: str) -> bool:
        return value == "" or value.isdigit()

    def _parse_float(self, text: str) -> float:
        return float(text.strip().replace(",", "."))

    def _parse_int(self, text: str) -> int:
        return int(text.strip())

    def _formatar_reais(self, valor: float, casas: int = 2) -> str:
        formatado = f"{valor:,.{casas}f}"
        return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

    def _set_message(self, texto: str, erro: bool = False) -> None:
        self.message_var.set(texto)
        self.message_label.configure(
            style="Header.Error.TLabel" if erro else "Header.Info.TLabel"
        )

    def _clear_message(self) -> None:
        self.message_var.set("")
        self.message_label.configure(style="Header.Info.TLabel")

    def _set_invalid(self, widget: ttk.Widget, invalid: bool) -> None:
        style = "Invalid.TEntry" if invalid else "TEntry"
        if isinstance(widget, ttk.Combobox):
            style = "Invalid.TCombobox" if invalid else "TCombobox"
        widget.configure(style=style)

    def validate_inputs(self) -> tuple[bool, dict[str, float | int | str]]:
        dados: dict[str, float | int | str] = {}
        valido = True

        self._set_invalid(self.placa_combo, False)
        self._set_invalid(self.entry_distancia, False)
        self._set_invalid(self.entry_peso, False)
        self._set_invalid(self.entry_colaboradores, False)

        placa = self.placa_var.get().strip()
        if not placa:
            self._set_invalid(self.placa_combo, True)
            valido = False

        try:
            distancia = self._parse_float(self.distancia_var.get())
            if distancia <= 0:
                raise ValueError
        except ValueError:
            self._set_invalid(self.entry_distancia, True)
            valido = False
            distancia = 0.0

        try:
            peso = self._parse_float(self.peso_var.get())
            if peso <= 0:
                raise ValueError
        except ValueError:
            self._set_invalid(self.entry_peso, True)
            valido = False
            peso = 0.0

        try:
            colaboradores = self._parse_int(self.colaboradores_var.get())
            if colaboradores <= 0:
                raise ValueError
        except ValueError:
            self._set_invalid(self.entry_colaboradores, True)
            valido = False
            colaboradores = 0

        dados.update(
            {
                "placa": placa,
                "distancia": distancia,
                "peso": peso,
                "colaboradores": colaboradores,
            }
        )

        if not valido:
            self._set_message("Confira os campos em destaque e tente novamente.", erro=True)

        return valido, dados

    def on_calcular(self) -> None:
        self._clear_message()
        valido, dados = self.validate_inputs()
        if not valido:
            return

        carregando_dados = not frete_calculo.dados_carregados()
        mensagem = "Carregando planilhas... aguarde." if carregando_dados else "Calculando custo... aguarde."
        self._set_message(mensagem, erro=False)
        self.btn_calcular.state(["disabled"])
        self.root.configure(cursor="watch")
        self.root.update_idletasks()

        try:
            resultado = frete_calculo.calcular_frete(
                placa=str(dados["placa"]),
                distancia_km=float(dados["distancia"]),
                peso_toneladas=float(dados["peso"]),
                colaboradores=int(dados["colaboradores"]),
                incluir_pedagio=self.var_pedagio.get(),
                incluir_reserva=self.var_reserva.get(),
            )
        except Exception as exc:  # pragma: no cover - interface interativa
            messagebox.showerror(
                "Erro ao calcular custo",
                f"Ocorreu um erro ao calcular o custo.\nDetalhes: {exc}",
            )
            return
        finally:
            self.btn_calcular.state(["!disabled"])
            self.root.configure(cursor="")

        self._render_resultado(frete_calculo.formatar_resultado(resultado), resultado.custo_total)
        self._render_metricas(resultado)
        self._set_message("Calculo de custo concluido.", erro=False)

        placa_normalizada = self._normalizar_placa(str(dados["placa"]))
        placas_2025 = frete_calculo.get_dados().get("custo_combustivel_por_km_por_placa", {})
        if placa_normalizada not in placas_2025:
            self._set_message(
                "Aviso: placa sem dados de combustivel em 2025.", erro=True
            )

    def _render_resultado(self, texto: str, total: float | None = None) -> None:
        self.text_resultado.configure(state="normal")
        self.text_resultado.delete("1.0", tk.END)
        self.text_resultado.insert(tk.END, texto)
        self.text_resultado.configure(state="disabled")
        if total is not None:
            self.total_var.set(self._formatar_reais(total))

    def _render_metricas(self, resultado) -> None:
        linhas: list[str] = []
        if resultado.distancia_km > 0:
            custo_pedagio_info = (
                self._formatar_reais(resultado.custo_pedagio / resultado.distancia_km)
                if self.var_pedagio.get()
                else "Desativado"
            )
            custo_reserva_info = (
                self._formatar_reais(resultado.custo_reserva / resultado.distancia_km)
                if self.var_reserva.get()
                else "Desativado"
            )
            linhas.extend(
                [
                    "Valores por km em R$ (2 casas).",
                    f"Custo combustivel por km: {self._formatar_reais(resultado.custo_combustivel / resultado.distancia_km)}",
                    f"Custo manutencao por km: {self._formatar_reais(resultado.custo_manutencao / resultado.distancia_km)}",
                    f"Custo pedagio por km: {custo_pedagio_info}",
                    f"Custo reserva por km: {custo_reserva_info}",
                    f"Custo mao de obra total por km: {self._formatar_reais(resultado.custo_mao_de_obra_total / resultado.distancia_km)}",
                    f"Tempo medio de viagem: {resultado.tempo_viagem_horas:.2f} h",
                    f"Tempo total medio (viagem + descarga): {resultado.tempo_total_horas:.2f} h",
                    f"Dias estimados de trabalho: {frete_calculo.formatar_dias_horas(resultado.tempo_total_horas)}",
                ]
            )
        else:
            linhas.append("Distancia invalida; nao foi possivel calcular metricas por km.")

        if resultado.dias_trabalho > 0 and resultado.colaboradores > 0:
            custo_diaria = resultado.custo_mao_de_obra_total / (
                resultado.dias_trabalho * resultado.colaboradores
            )
            linhas.append(f"Custo diaria por colaborador: {self._formatar_reais(custo_diaria)}")
        else:
            linhas.append("Custo diaria por colaborador: N/A")

        self.text_metricas.configure(state="normal")
        self.text_metricas.delete("1.0", tk.END)
        self.text_metricas.insert(tk.END, "\n".join(linhas))
        self.text_metricas.configure(state="disabled")

    def on_limpar(self) -> None:
        self.placa_var.set("")
        self.distancia_var.set("")
        self.peso_var.set("")
        self.colaboradores_var.set("")
        self.var_pedagio.set(False)
        self.var_reserva.set(True)
        self._render_resultado("")
        self._render_metricas_empty()
        self._clear_message()
        self.total_var.set("R$ 0,00")
        self._set_invalid(self.placa_combo, False)
        self._set_invalid(self.entry_distancia, False)
        self._set_invalid(self.entry_peso, False)
        self._set_invalid(self.entry_colaboradores, False)

    def _render_metricas_empty(self) -> None:
        self.text_metricas.configure(state="normal")
        self.text_metricas.delete("1.0", tk.END)
        self.text_metricas.configure(state="disabled")

    def _normalizar_placa(self, placa: str) -> str:
        placa = placa.strip().upper()
        return "".join(ch for ch in placa if ch.isalnum())

    def on_copiar(self) -> None:
        texto = self.text_resultado.get("1.0", tk.END).strip()
        if not texto:
            self._set_message("Nao ha resumo para copiar.", erro=True)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self._set_message("Resumo copiado para a area de transferencia.", erro=False)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
