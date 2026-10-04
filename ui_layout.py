"""Apple-inspired desktop layout. Processing remains in engine.py."""
import customtkinter as ctk
from ui_media import icon, thumbnail
from brand import brand_image
from framing import FRAMING_LABELS, FRAMING_HELP

BG = '#f5f5f7'
PANEL = '#ffffff'
TEXT = '#1d1d1f'
MUTED = '#63636e'
ACCENT = '#0071e3'
SOFT = '#e9e9ef'
FONT = 'Segoe UI Variable'


class StudioUI:
    def label(self, parent, text, size=14, muted=False, weight='normal', **kwargs):
        anchor = kwargs.pop('anchor', 'w')
        return ctk.CTkLabel(parent, text=text, text_color=MUTED if muted else TEXT,
                           font=(FONT, size, weight), anchor=anchor, **kwargs)

    def button(self, parent, text, command, primary=False, **kwargs):
        height = kwargs.pop('height', 42)
        widget = ctk.CTkButton(parent, text=text, command=command, height=height,
            corner_radius=12, fg_color=ACCENT if primary else SOFT,
            hover_color='#0062c4' if primary else '#dddde5',
            text_color='white' if primary else TEXT, text_color_disabled='#85858f',
            font=(FONT, 14, 'bold'), border_width=0, **kwargs)
        self.controls.append(widget)
        return widget

    def entry(self, parent, value, width=90):
        widget = ctk.CTkEntry(parent, width=width, height=38, corner_radius=10,
            fg_color='#f0f0f5', border_width=0, text_color=TEXT,
            font=(FONT, 14), justify='center')
        widget.insert(0, value)
        widget.bind('<FocusIn>', lambda event: widget.configure(border_width=2, border_color=ACCENT))
        widget.bind('<FocusOut>', lambda event: widget.configure(border_width=0))
        self.controls.append(widget)
        return widget

    def build_ui(self):
        self.images = []
        self.details_open = False
        top = ctk.CTkFrame(self, fg_color=BG)
        top.grid(row=0, column=0, columnspan=2, sticky='ew', padx=30, pady=(20, 18))
        top.columnconfigure(1, weight=1)
        logo = brand_image('mark', 38, 48)
        self.label(top, '', 20, image=logo).grid(row=0, column=0, padx=(0, 10))
        self.label(top, '', image=brand_image('wordmark', 156, 28)).grid(row=0, column=1, sticky='w')
        self.button(top, 'Otwórz projekt', self.open_project, width=135, height=36).grid(row=0, column=2, padx=(0, 10))
        self.save_button = self.button(top, 'Zapisz projekt', self.save_project, width=125, height=36)
        self.save_button.grid(row=0, column=3)

        side = ctk.CTkScrollableFrame(self, width=254, fg_color=BG, corner_radius=0,
            scrollbar_button_color='#d8d8df', scrollbar_button_hover_color='#babac4')
        side.grid(row=1, column=0, sticky='ns', padx=(22, 18), pady=(0, 24))
        side.columnconfigure(0, weight=1)
        self.label(side, 'Po Twojemu', 22, weight='bold').grid(row=0, column=0, sticky='w', padx=8, pady=(8, 2))
        self.label(side, 'Ustaw raz. Twórz kolejne klipy.', 13, True).grid(row=1, column=0, sticky='w', padx=8, pady=(0, 22))

        settings = ctk.CTkFrame(side, fg_color=PANEL, corner_radius=16)
        settings.grid(row=2, column=0, sticky='ew')
        settings.columnconfigure(0, weight=1)
        self.label(settings, 'Liczba klipów', 14, weight='bold').grid(row=0, column=0, sticky='w', padx=18, pady=(18, 8))
        self.mode = ctk.CTkSegmentedButton(settings, values=['AI klipy', 'Film · minuty'],
            command=lambda value: self.update_mode_info(), height=34, font=(FONT, 12), corner_radius=9,
            fg_color=SOFT, selected_color='white', selected_hover_color='#fafaff',
            unselected_color=SOFT, unselected_hover_color='#dddde5', text_color=TEXT)
        self.mode.set('AI klipy')
        self.mode.grid(row=1, column=0, padx=18, pady=(0, 10), sticky='ew')
        self.controls.append(self.mode)
        stepper = ctk.CTkFrame(settings, fg_color='#f0f0f5', corner_radius=10)
        stepper.grid(row=2, column=0, sticky='ew', padx=18, pady=(0, 16))
        stepper.columnconfigure(1, weight=1)
        self.button(stepper, '−', lambda: self.step_count(-1), width=40, height=38).grid(row=0, column=0)
        self.count = self.entry(stepper, '5', width=90)
        self.count.grid(row=0, column=1, sticky='ew')
        self.button(stepper, '+', lambda: self.step_count(1), width=40, height=38).grid(row=0, column=2)
        self.label(settings, 'Długość klipu', 14, weight='bold').grid(row=3, column=0, sticky='w', padx=18, pady=(0, 8))
        times = ctk.CTkFrame(settings, fg_color='transparent')
        times.grid(row=4, column=0, padx=18, sticky='ew', pady=(0, 4))
        times.columnconfigure((0, 2), weight=1)
        self.minimum, self.maximum = self.entry(times, '30'), self.entry(times, '60')
        self.minimum.grid(row=0, column=0, sticky='ew')
        self.label(times, '–', muted=True).grid(row=0, column=1, padx=8)
        self.maximum.grid(row=0, column=2, sticky='ew')
        self.label(settings, 'sekund · minimum i maksimum', 12, True).grid(row=5, column=0, padx=18, pady=(0, 18), sticky='w')
        self.mode_hint = self.label(settings, 'AI wybierze najlepsze momenty z transkrypcji.', 12, True, wraplength=215, justify='left')
        self.mode_hint.grid(row=6, column=0, padx=18, pady=(0, 16), sticky='w')
        self.label(settings, 'Format obrazu', 14, weight='bold').grid(row=7, column=0, padx=18, sticky='w', pady=(0, 8))
        self.format = ctk.CTkSegmentedButton(settings, values=['Pionowy 9:16', 'Oryginalny'],
            command=lambda value: self.update_framing_info(),
            height=38, font=(FONT, 12), corner_radius=9, fg_color=SOFT,
            selected_color='white', selected_hover_color='#fafaff',
            unselected_color=SOFT, unselected_hover_color='#dddde5', text_color=TEXT)
        self.format.set('Pionowy 9:16')
        self.format.grid(row=8, column=0, padx=18, pady=(0, 18), sticky='ew')
        self.controls.append(self.format)
        self.label(settings, 'Kadrowanie pionowe', 14, weight='bold').grid(row=9, column=0, padx=18, sticky='w', pady=(0, 8))
        self.cropping = ctk.CTkOptionMenu(settings, values=list(FRAMING_LABELS),
            command=lambda value: self.update_framing_info(), height=38, corner_radius=10,
            fg_color=SOFT, button_color=SOFT, button_hover_color='#dddde5', text_color=TEXT,
            font=(FONT, 12), dropdown_fg_color=PANEL, dropdown_text_color=TEXT, dropdown_hover_color=SOFT)
        self.cropping.set('Cały obraz · czarne pasy')
        self.cropping.grid(row=10, column=0, padx=18, sticky='ew')
        self.controls.append(self.cropping)
        self.framing_hint = self.label(settings, FRAMING_HELP['fit'], 12, True, wraplength=215, justify='left')
        self.framing_hint.grid(row=11, column=0, padx=18, sticky='w', pady=(6, 16))
        self.label(settings, 'Dodatki eksportu', 14, weight='bold').grid(row=12, column=0, padx=18, sticky='w', pady=(0, 8))
        self.light_color = ctk.CTkSwitch(settings, text='Lekki kolor', font=(FONT, 13), progress_color=ACCENT,
            button_color='white', button_hover_color='#f6f6fb', fg_color='#d8d8df', text_color=TEXT, switch_width=42, switch_height=24)
        self.light_color.grid(row=13, column=0, padx=18, pady=2, sticky='w')
        self.speed_up = ctk.CTkSwitch(settings, text='Tempo 1,1×', font=(FONT, 13), progress_color=ACCENT,
            button_color='white', button_hover_color='#f6f6fb', fg_color='#d8d8df', text_color=TEXT, switch_width=42, switch_height=24)
        self.speed_up.grid(row=14, column=0, padx=18, pady=2, sticky='w')
        self.mirror = ctk.CTkSwitch(settings, text='Odbicie lustrzane', font=(FONT, 13), progress_color=ACCENT,
            button_color='white', button_hover_color='#f6f6fb', fg_color='#d8d8df', text_color=TEXT, switch_width=42, switch_height=24)
        self.mirror.grid(row=15, column=0, padx=18, pady=(2, 10), sticky='w')
        self.controls.extend((self.light_color, self.speed_up, self.mirror))
        self.burn = ctk.CTkSwitch(settings, text='Napisy słowo po słowie', font=(FONT, 14),
            progress_color=ACCENT, button_color='white', button_hover_color='#f6f6fb',
            fg_color='#d8d8df', text_color=TEXT, switch_width=42, switch_height=24)
        self.burn.select()
        self.burn.grid(row=16, column=0, padx=18, pady=(2, 18), sticky='w')
        self.controls.append(self.burn)

        self.label(side, 'Wybierz charakter', 17, weight='bold').grid(row=3, column=0, padx=8, sticky='w', pady=(22, 8))
        self.brief = ctk.CTkTextbox(side, height=112, corner_radius=14, fg_color=PANEL,
            text_color=TEXT, font=(FONT, 13), wrap='word', border_spacing=12)
        self.brief.insert('1.0', 'Mocny początek, ciekawa myśl lub zabawny moment. Pełna puenta i naturalne zakończenie.')
        self.brief.grid(row=4, column=0, sticky='ew')
        self.controls.append(self.brief)
        self.label(side, 'Dokładność transkrypcji', 13, True).grid(row=5, column=0, padx=8, sticky='w', pady=(18, 7))
        self.whisper = ctk.CTkOptionMenu(side, values=['Szybka', 'Zrównoważona', 'Dokładna', 'Najdokładniejsza'],
            height=38, corner_radius=10, fg_color=PANEL, button_color=PANEL,
            button_hover_color=SOFT, text_color=TEXT, font=(FONT, 13),
            dropdown_fg_color=PANEL, dropdown_text_color=TEXT, dropdown_hover_color=SOFT)
        self.whisper.set('Zrównoważona')
        self.whisper.grid(row=6, column=0, sticky='ew')
        self.controls.append(self.whisper)
        self.label(side, 'Film zostaje na Twoim komputerze.\nGPT wybiera momenty z transkrypcji.', 12, True,
            justify='left').grid(row=7, column=0, padx=8, sticky='w', pady=(22, 10))

        main = ctk.CTkFrame(self, fg_color='transparent')
        main.grid(row=1, column=1, sticky='nsew', padx=(0, 30), pady=(0, 24))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)
        self.label(main, 'Twój kolejny klip.', 32, weight='bold').grid(row=0, column=0, sticky='w', pady=(2, 2))
        self.label(main, 'Dobry moment. Własny styl. Gotowy do publikacji.', 14, True).grid(row=1, column=0, sticky='w', pady=(0, 18))
        source = ctk.CTkFrame(main, fg_color=PANEL, corner_radius=18)
        self.source_panel = source
        source.grid(row=2, column=0, sticky='ew', pady=(0, 20))
        source.columnconfigure(1, weight=1)
        placeholder = brand_image('mark', 70, 82)
        self.source_thumb = ctk.CTkLabel(source, text='', image=placeholder, width=204, height=116,
            fg_color='#f0f0f5', corner_radius=12)
        self.source_thumb.grid(row=0, column=0, rowspan=3, padx=18, pady=18)
        self.source_label = self.label(source, 'Zacznij od filmu', 20, weight='bold', wraplength=440)
        self.source_label.grid(row=0, column=1, sticky='w', padx=(0, 18), pady=(18, 0))
        self.info_label = self.label(source, 'Przeciągnij film tutaj lub wybierz go z komputera.\nMP4, MKV, MOV lub WEBM.', 13, True,
                                      wraplength=440, justify='left')
        self.info_label.grid(row=1, column=1, sticky='w', padx=(0, 18), pady=(0, 8))
        self.import_button = self.button(source, 'Dodaj film', self.choose_source, True, width=130, height=36,
            image=ctk.CTkImage(icon('plus', 'white'), size=(18, 18)))
        self.import_button.grid(row=2, column=1, sticky='w', padx=(0, 18), pady=(0, 18))
        transcript_bar = ctk.CTkFrame(source, fg_color='transparent')
        transcript_bar.grid(row=3, column=0, columnspan=2, sticky='ew', padx=18, pady=(0, 16))
        transcript_bar.columnconfigure(0, weight=1)
        self.transcript_label = self.label(transcript_bar, 'Transkrypcja: brak', 12, True, wraplength=230)
        self.transcript_label.grid(row=0, column=0, sticky='w')
        self.transcribe_button = self.button(transcript_bar, 'Transkrybuj', self.transcribe_only, width=105, height=32)
        self.transcribe_button.grid(row=0, column=1, padx=(8, 0))
        self.attach_button = self.button(transcript_bar, 'Wczytaj', self.attach_transcript, width=88, height=32)
        self.attach_button.grid(row=0, column=2, padx=(8, 0))
        self.download_button = self.button(transcript_bar, 'Pobierz', self.download_transcript, width=88, height=32)
        self.download_button.grid(row=0, column=3, padx=(8, 0))

        tools = ctk.CTkFrame(main, fg_color='transparent')
        tools.grid(row=3, column=0, sticky='ew', pady=(0, 12))
        tools.columnconfigure(0, weight=1)
        self.results_title = self.label(tools, 'Twoje klipy', 22, weight='bold')
        self.results_title.grid(row=0, column=0, sticky='w')
        self.analyze_button = self.button(tools, 'Znajdź fragmenty', self.analyze, True, width=160, height=38)
        self.analyze_button.grid(row=0, column=1)
        self.cancel_button = ctk.CTkButton(tools, text='Przerwij', command=self.cancel_task,
            height=38, width=90, corner_radius=10, fg_color='#fce9e7', hover_color='#f7d8d5',
            text_color='#a63125', font=(FONT, 13), state='disabled')
        self.cancel_button.grid(row=0, column=2, padx=(10, 0))
        self.cancel_button.grid_remove()
        self.results = ctk.CTkScrollableFrame(main, fg_color=PANEL, corner_radius=18,
            scrollbar_button_color='#ddddE5', scrollbar_button_hover_color='#bdbdc8')
        self.results.grid(row=4, column=0, sticky='nsew')
        self.results.columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(main, fg_color='transparent')
        footer.grid(row=5, column=0, sticky='ew', pady=(16, 10))
        footer.columnconfigure(0, weight=1)
        self.selection_label = self.label(footer, 'Klipy pojawią się po analizie.', 13, True)
        self.selection_label.grid(row=0, column=0, sticky='w')
        self.button(footer, 'Folder klipów', self.open_destination, width=135,
            image=ctk.CTkImage(icon('folder', TEXT), size=(18, 18))).grid(row=0, column=1, padx=(0, 10))
        self.export_button = self.button(footer, 'Eksportuj klipy', self.export, True, width=160,
            image=ctk.CTkImage(icon('export', 'white'), size=(18, 18)))
        self.export_button.grid(row=0, column=2)
        statusbar = ctk.CTkFrame(main, fg_color='transparent')
        statusbar.grid(row=6, column=0, sticky='ew')
        statusbar.columnconfigure(0, weight=1)
        self.status = self.label(statusbar, 'Wszystko gotowe. Dodaj swój pierwszy film.', 12, True, wraplength=650)
        self.status.grid(row=0, column=0, sticky='w')
        self.details_button = ctk.CTkButton(statusbar, text='Szczegóły', command=self.toggle_details,
            fg_color='transparent', hover_color=SOFT, text_color=ACCENT, width=80, height=28, font=(FONT, 12))
        self.details_button.grid(row=0, column=1, sticky='e')
        self.progress = ctk.CTkProgressBar(main, height=3, fg_color='#e3e3ea', progress_color=ACCENT, mode='determinate')
        self.progress.grid(row=7, column=0, sticky='ew', pady=(6, 0))
        self.progress.set(0)
        self.logs = ctk.CTkTextbox(main, height=85, corner_radius=12, fg_color='#ededf2',
            font=('Consolas', 11), text_color=MUTED, state='disabled')
        self.logs.grid(row=8, column=0, sticky='ew', pady=(8, 0))
        self.logs.grid_remove()
        self.render_clips()
        self.update_mode_info()
        self.bind('<Control-o>', lambda event: self.choose_source() if self.pipeline is None else None)
        self.bind('<Control-s>', lambda event: self.save_project() if self.pipeline is None else None)
        self.bind('<Escape>', lambda event: self.cancel_task())

    def toggle_details(self):
        self.details_open = not self.details_open
        if self.details_open:
            self.logs.grid()
        else:
            self.logs.grid_remove()
        self.details_button.configure(text='Ukryj' if self.details_open else 'Szczegóły')

    def update_mode_info(self):
        film_mode = self.mode.get() == 'Film · minuty'
        self.mode_hint.configure(text='Film zostanie podzielony na pełne minuty; ostatnia część może być krótsza.' if film_mode else 'AI wybierze najlepsze momenty z transkrypcji.')
        self.analyze_button.configure(text='Podziel film' if film_mode else 'Znajdź fragmenty')

    def step_count(self, delta):
        try:
            count = max(1, min(20, int(self.count.get()) + delta))
        except ValueError:
            count = 5
        self.count.delete(0, 'end')
        self.count.insert(0, str(count))

    def refresh_actions(self):
        busy = self.pipeline is not None
        selected = sum(bool(row['selected'].get()) for row in self.rows)
        for button, enabled in ((self.analyze_button, bool(self.source) and not busy),
                                (self.export_button, bool(selected) and not busy)):
            button.configure(state='normal' if enabled else 'disabled',
                             fg_color=ACCENT if enabled else '#e7e7ed',
                             text_color='white' if enabled else MUTED,
                             text_color_disabled=MUTED)
        self.analyze_button.configure(text='Trwa zadanie…' if busy else 'Znajdź fragmenty')
        self.save_button.configure(state='normal' if self.source and not busy else 'disabled')
        self.attach_button.configure(state='normal' if self.source and not busy else 'disabled')
        self.download_button.configure(state='normal' if self.segments and not busy else 'disabled')
        self.transcribe_button.configure(state='normal' if self.source and not self.segments and not busy else 'disabled')
        self.transcript_label.configure(text=f'Transkrypcja: gotowa · {len(self.segments)} segmentów'
                                        if self.segments else 'Transkrypcja: brak')
        self.cropping.configure(state='normal' if self.format.get() == 'Pionowy 9:16' and not busy else 'disabled')
        if busy:
            self.cancel_button.grid()
        else:
            self.cancel_button.grid_remove()
        self.selection_label.configure(text=f'{selected} z {len(self.rows)} klipów do eksportu'
                                        if self.rows else 'Klipy pojawią się po analizie.')

    def framing_mode(self):
        return FRAMING_LABELS[self.cropping.get()]

    def update_framing_info(self):
        help_text = FRAMING_HELP[self.framing_mode()] if self.format.get() == 'Pionowy 9:16' else 'Zachowamy oryginalne proporcje całego filmu.'
        self.framing_hint.configure(text=help_text)
        if self.metadata:
            minutes, seconds = divmod(int(self.metadata['duration']), 60)
            self.info_label.configure(text=f"{minutes}:{seconds:02d}  ·  {self.metadata['width']} × {self.metadata['height']}\n{help_text}")
        self.refresh_actions()

    def update_source_preview(self):
        try:
            image = thumbnail(self.source, size=(408, 232))
            self.source_image = ctk.CTkImage(image, size=(204, 116))
            self.source_thumb.configure(image=self.source_image)
        except Exception:
            self.source_thumb.configure(image=brand_image('mark', 70, 82))
        self.import_button.configure(text='Zmień film', fg_color=SOFT, hover_color='#dddde5',
            text_color=TEXT, image=ctk.CTkImage(icon('plus', TEXT), size=(18, 18)))
        self.refresh_actions()

    def render_clips(self):
        for child in self.results.winfo_children():
            child.destroy()
        self.rows = []
        self.images = []
        self.results_title.configure(text=f'Twoje klipy · {len(self.clips)}' if self.clips else 'Twoje klipy')
        if not self.clips:
            empty = ctk.CTkFrame(self.results, fg_color='transparent')
            empty.grid(row=0, column=0, sticky='ew', padx=24, pady=(44, 36))
            empty.columnconfigure(0, weight=1)
            image = brand_image('lockup', 142, 124)
            self.images.append(image)
            ctk.CTkLabel(empty, text='', image=image, height=124).grid(row=0, column=0, pady=(0, 14))
            heading = 'Film gotowy. Znajdź najlepsze momenty.' if self.source else 'Dobre klipy zaczynają się tutaj.'
            self.label(empty, heading, 23, weight='bold', anchor='center', wraplength=530).grid(row=1, column=0, sticky='ew')
            self.label(empty, 'Wybierz film, a potem pozwól AI znaleźć fragmenty,\nktóre mają mocny początek i dobrą puentę.', 14, True,
                anchor='center', justify='center', wraplength=530).grid(row=2, column=0, sticky='ew', pady=(8, 0))
            self.refresh_actions()
            return
        for i, clip in enumerate(self.clips):
            frame = ctk.CTkFrame(self.results, fg_color='transparent')
            frame.grid(row=i, column=0, sticky='ew', padx=16, pady=(20, 4))
            frame.columnconfigure(2, weight=1)
            selected = ctk.CTkCheckBox(frame, text='', width=24, checkbox_width=22, checkbox_height=22,
                corner_radius=7, border_width=2, border_color='#c0c0cb', fg_color=ACCENT,
                hover_color='#0062c4', checkmark_color='white', command=self.refresh_actions)
            selected.select()
            selected.grid(row=0, column=0, rowspan=3, sticky='nw', padx=(0, 12), pady=5)
            try:
                image = ctk.CTkImage(thumbnail(self.source, clip['start'], size=(224, 126)), size=(112, 63))
            except Exception:
                image = brand_image('mark', 40, 50)
            self.images.append(image)
            preview_image = ctk.CTkButton(frame, text='', image=image, width=112, height=70,
                border_spacing=0, fg_color='transparent', hover_color=SOFT, corner_radius=12,
                command=lambda n=i: self.preview(n))
            preview_image.grid(row=0, column=1, rowspan=2, sticky='nw', padx=(0, 16))
            title = self.label(frame, clip['title'], 16, weight='bold', wraplength=420, justify='left')
            title.grid(row=0, column=2, sticky='w')
            score = ctk.CTkLabel(frame, text=f"{clip['score']}/100", font=(FONT, 12, 'bold'),
                text_color='#075aaf', fg_color='#eaf3ff', corner_radius=8, width=65, height=28)
            score.grid(row=0, column=3, sticky='ne', padx=(10, 0))
            self.label(frame, clip['reason'], 13, True, wraplength=440, justify='left').grid(
                row=1, column=2, columnspan=2, sticky='w', pady=(5, 12))
            times = ctk.CTkFrame(frame, fg_color='transparent')
            times.grid(row=2, column=2, columnspan=2, sticky='w')
            self.label(times, 'Od', 12, True).pack(side='left', padx=(0, 6))
            start = self.entry(times, f"{clip['start']:.2f}", width=74)
            start.pack(side='left')
            self.label(times, 'do', 12, True).pack(side='left', padx=8)
            end = self.entry(times, f"{clip['end']:.2f}", width=74)
            end.pack(side='left')
            self.label(times, 's', 12, True).pack(side='left', padx=(6, 14))
            preview = ctk.CTkButton(times, text='Obejrzyj', width=100, height=36, corner_radius=10,
                font=(FONT, 13, 'bold'), fg_color=SOFT, hover_color='#dddde5', text_color=TEXT,
                image=ctk.CTkImage(icon('play', TEXT, 18), size=(16, 16)), command=lambda n=i: self.preview(n))
            preview.pack(side='left')
            ctk.CTkFrame(frame, fg_color='#e9e9ef', height=1).grid(row=3, column=1, columnspan=3, sticky='ew', pady=(20, 0))
            # Row entries are governed by row state, not the persistent settings list.
            self.controls.remove(start)
            self.controls.remove(end)
            self.rows.append({'selected': selected, 'start': start, 'end': end,
                              'widgets': [selected, start, end, preview, preview_image]})
        self.refresh_actions()
