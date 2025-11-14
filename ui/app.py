import sys
import time
import os
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from prompt_toolkit.application import Application, in_terminal
from core.scanner import run_scan_async
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.widgets import Box

from ui.widgets.banner import load_banner
from ui.views.main_view import build_bottom_menu


class BigBrotherApp:
    """Главное приложение BigBrother с исправленным прогресс-баром."""

    # Константы
    DEFAULT_TARGETS_PATH = 'resources/targets.txt'
    DEFAULT_OUTPUT_CSV = 'output.csv'
    ALLOWED_THREADS = {20, 50, 100}
    WORDLIST_LEVELS = {'small', 'medium', 'large'}
    SUPPORTED_LANGUAGES = {'RU', 'EN'}

    def __init__(self):
        self._initialize_settings()
        self._initialize_ui_components()
        self._initialize_application()
        self.is_scanning = False
        self.current_progress_text = ""
        self.scan_task = None

    def _initialize_settings(self) -> None:
        """Инициализация настроек приложения."""
        self.targets_path = self.DEFAULT_TARGETS_PATH
        self.wordlist_level = 'medium'
        self.threads = 50
        self.dns_resolver: Optional[str] = None
        self.output_csv = self.DEFAULT_OUTPUT_CSV
        self.lang = 'RU'
        self._ensure_directories_exist()

    def _ensure_directories_exist(self) -> None:
        """Создает необходимые директории."""
        os.makedirs('resources/wordlists', exist_ok=True)
        os.makedirs('resources/animation_frames', exist_ok=True)

    def _initialize_ui_components(self) -> None:
        """Инициализация UI компонентов."""
        self._create_banner()
        self._create_center_content()
        self._create_bottom_menu()
        self._create_layout()

    def _create_banner(self) -> None:
        """Создание баннера приложения."""
        banner_text = load_banner()
        self.banner = Window(
            content=FormattedTextControl(banner_text),
            style="class:banner",
            align="center",
            height=8,
        )

    def _create_center_content(self) -> None:
        """Создание центрального контента."""
        instruction_text = self._get_instruction_text()
        self.center = Window(
            content=FormattedTextControl(instruction_text),
            style="class:center",
            always_hide_cursor=True,
            wrap_lines=True,
            align="center",
        )
        self.blank = Window(height=1)

    def _cancel_scan(self):
        """Отмена текущего сканирования."""
        if self.is_scanning:
            if self.scan_task and not self.scan_task.done():
                self.scan_task.cancel()

            # Показываем текст пользователю
            if self.lang == "RU":
                self._update_center_text("Сканирование прервано пользователем.")
            else:
                self._update_center_text("Scan interrupted by user.")

            self.is_scanning = False

    def _log_scan_message(self, message: str) -> None:
        """Добавляет сообщение сканирования в UI без сброса прогресса."""
        # Сохраняем все предыдущие сообщения
        if not hasattr(self, '_scan_messages'):
            self._scan_messages = []

        self._scan_messages.append(message)

        # Ограничиваем количество сообщений (последние 10)
        if len(self._scan_messages) > 10:
            self._scan_messages = self._scan_messages[-10:]

        # Комбинируем прогресс + сообщения
        display_text = ""
        if self.current_progress_text:
            display_text = self.current_progress_text + "\n\n"

        display_text += "\n".join(self._scan_messages)
        self._update_center_text(display_text)

    def _get_instruction_text(self) -> str:
        """Возвращает текст инструкции."""
        if self.lang == 'RU':
            return self._get_russian_instructions()
        else:
            return self._get_english_instructions()

    def _get_russian_instructions(self) -> str:
        """Русская версия инструкции."""
        return """
                    ╔════════════════════════════════════════════════════════════════════════╗
                    ║                Инструкция по использованию BigBrother                  ║
                    ╟────────────────────────────────────────────────────────────────────────╢
                    ║ Добро пожаловать! Это инструмент для анализа субдоменов на топ-сайтах  ║
                    ║ РФ (из "белых списков"). Мы brute-force'им субдомены, проверяем IP,    ║
                    ║ фильтруем wildcard, выводим в CSV и уникальные IP.                     ║
                    ║                                                                        ║
                    ║ Как использовать:                                                      ║
                    ║ - [F2] Targets: Выберите/отредактируйте список сайтов (топ-20 РФ).     ║
                    ║   Пример: yandex.ru, vk.com, sber.ru. Можно добавлять/удалять.         ║
                    ║ - [F3] Threads: Установите кол-во потоков (20/50/100, по умолч. 50).   ║
                    ║ - [F4] Wordlist: Выберите словарь субдоменов (small/medium/large).     ║
                    ║ - [F5] DNS: Настройте DNS-резолвер (по умолч. system).                 ║
                    ║ - [F6] Output: Укажите путь для CSV/логов (по умолч. output.csv).      ║
                    ║ - [F7] Lang: Смена языка (RU/EN).                                      ║
                    ║ - [F9] Run: Запустить сканирование. Результаты в центр + файлы.        ║
                    ║ - [F10] Quit: Выход.                                                   ║
                    ║                                                                        ║
                    ║ Нажмите F-кнопки для действий. Стрелки/Tab для навигации по меню.      ║
                    ║ Готовы? Настройте и жмите Run!                                         ║
                    ╚════════════════════════════════════════════════════════════════════════╝
        """

    def _get_english_instructions(self) -> str:
        """Английская версия инструкции."""
        return """
                    ╔════════════════════════════════════════════════════════════════════════╗
                    ║                     BigBrother Usage Instructions                      ║
                    ╟────────────────────────────────────────────────────────────────────────╢
                    ║ Welcome! This is a tool for subdomain analysis of top Russian          ║
                    ║ websites (from "white lists"). We brute-force subdomains, check IPs,   ║
                    ║ filter wildcards, output to CSV and unique IPs.                        ║
                    ║                                                                        ║
                    ║ How to use:                                                            ║
                    ║ - [F2] Targets: Select/edit website list (top-20 RU).                  ║
                    ║   Example: yandex.ru, vk.com, sber.ru. You can add/remove.             ║
                    ║ - [F3] Threads: Set number of threads (20/50/100, default 50).         ║
                    ║ - [F4] Wordlist: Choose subdomain dictionary (small/medium/large).     ║
                    ║ - [F5] DNS: Configure DNS resolver (default: system).                  ║
                    ║ - [F6] Output: Specify path for CSV/logs (default: output.csv).        ║
                    ║ - [F7] Lang: Change language (RU/EN).                                  ║
                    ║ - [F9] Run: Start scanning. Results in center + files.                 ║
                    ║ - [F10] Quit: Exit.                                                    ║
                    ║                                                                        ║
                    ║ Press F-keys for actions. Arrows/Tab for menu navigation.              ║
                    ║ Ready? Configure and press Run!                                        ║
                    ╚════════════════════════════════════════════════════════════════════════╝
        """

    def _create_bottom_menu(self) -> None:
        """Создание нижнего меню."""
        self.bottom_menu = build_bottom_menu()
        self.buttons = [child for child in self.bottom_menu.children
                        if isinstance(child, Window)]
        self.current_focus_index = 0

    def _create_layout(self) -> None:
        """Создание основного layout."""
        self.body = HSplit([
            self.banner,
            Window(height=1, char="─", style="class:line"),
            self.center,
            self.blank,
            Window(height=1, char="─", style="class:line"),
            self.bottom_menu,
        ])
        self.layout = Layout(self.body)

    def _initialize_application(self) -> None:
        """Инициализация основного приложения."""
        self.kb = KeyBindings()
        self._setup_key_bindings()

        self.app = Application(
            layout=self.layout,
            full_screen=False,
            key_bindings=self.kb,
            style=self._build_style(),
            mouse_support=False,
            # ВАЖНО: включаем автоматическое обновление
            refresh_interval=0.1,  # 100ms refresh rate
        )

    def _setup_key_bindings(self) -> None:
        """Настройка привязок клавиш."""

        # Навигация
        @self.kb.add('right')
        @self.kb.add('tab')
        def next_button(event):
            self.current_focus_index = (self.current_focus_index + 1) % len(self.buttons)
            event.app.layout.focus(self.buttons[self.current_focus_index])

        @self.kb.add('left')
        @self.kb.add('s-tab')
        def prev_button(event):
            self.current_focus_index = (self.current_focus_index - 1) % len(self.buttons)
            event.app.layout.focus(self.buttons[self.current_focus_index])

        @self.kb.add('enter')
        def select_button(event):
            self._handle_enter_key(event)

        # Функциональные клавиши
        function_handlers = {
            'f2': self.handle_targets,
            'f3': self.handle_threads,
            'f4': self.handle_wordlist,
            'f5': self.handle_dns,
            'f6': self.handle_output,
            'f7': self.handle_lang,
            'f9': self.handle_run,
            'f10': self.handle_quit,
        }

        for key, handler in function_handlers.items():
            @self.kb.add(key)
            def _(event, handler=handler):
                handler(event)

        # Выход
        @self.kb.add("c-c")
        @self.kb.add("escape")
        def _(event):
            if self.is_scanning:
                self._cancel_scan()
            else:
                event.app.exit(result="\nBigBrother shutting down...\n")

    def _handle_enter_key(self, event) -> None:
        """Обработка нажатия Enter."""
        if self.is_scanning:
            return

        current_window = self.layout.current_window
        if current_window in self.buttons:
            button_text = current_window.content.text.strip()

            button_handlers = {
                '[F2] Targets': self.handle_targets,
                '[F3] Threads': self.handle_threads,
                '[F4] Wordlist': self.handle_wordlist,
                '[F5] DNS': self.handle_dns,
                '[F6] Output': self.handle_output,
                '[F7] Lang': self.handle_lang,
                '[F9] Run': self.handle_run,
                '[F10] Quit': self.handle_quit,
            }

            for text_pattern, handler in button_handlers.items():
                if text_pattern in button_text:
                    handler(event)
                    break

    async def _show_dialog_async(self, dialog) -> Any:
        """
        Показать диалог, временно приостанавливая основной Application.
        Никаких троганий self.app.layout.
        """
        async with in_terminal():
            # Здесь основной BigBrotherApp «спит»,
            # диалог спокойно крутится в том же терминале.
            return await dialog.run_async()

    def _update_center_text(self, text: str) -> None:
        """Обновляет текст в центральной области."""
        self.center.content.text = text
        # ФОРСИРУЕМ ПЕРЕРИСОВКУ ЭКРАНА
        if hasattr(self.app, 'invalidate'):
            self.app.invalidate()

    def _show_scan_progress(self, domain: str, current: int, total: int) -> None:
        """Показывает прогресс сканирования с автоматическим обновлением."""
        progress = int((current / total) * 50) if total > 0 else 0
        bar = "█" * progress + "░" * (50 - progress)
        percent = int((current / total) * 100) if total > 0 else 0

        progress_text = f"Сканирование... {domain}\n[{bar}] {percent}% ({current}/{total})"

        # Сохраняем текст прогресса
        self.current_progress_text = progress_text

        # Комбинируем прогресс + сообщения
        display_text = progress_text
        if hasattr(self, '_scan_messages') and self._scan_messages:
            display_text += "\n\n" + "\n".join(self._scan_messages[-5:])  # Последние 5 сообщений

        self._update_center_text(display_text)

    # Обработчики действий
    def handle_targets(self, event) -> None:
        """Обработчик для настройки целей."""
        if self.is_scanning:
            return

        async def _coro():
            current_targets = ""
            try:
                if os.path.exists(self.targets_path):
                    with open(self.targets_path, 'r', encoding='utf-8') as f:
                        current_targets = f.read()
            except Exception as e:
                current_targets = f"Ошибка чтения файла: {e}"

            # Создаем стиль без тени для диалога
            no_shadow_style = Style.from_dict({
                "dialog": "bg:default",
                "dialog shadow": "bg:default",
                "shadow": "bg:default",
                "text-area": "bg:white",
                "textarea": "bg:white",
            })

            dialog = input_dialog(
                title='Targets',
                text='Введите домены через запятую:\nТекущие:\n' + current_targets,
                style=no_shadow_style  # Добавляем стиль без тени
            )

            new_targets = await self._show_dialog_async(dialog)

            if new_targets:
                try:
                    with open(self.targets_path, 'w', encoding='utf-8') as f:
                        domains = [d.strip() for d in new_targets.split(',') if d.strip()]
                        f.write('\n'.join(domains))
                    self._update_center_text(f"Targets обновлены! Сохранено {len(domains)} доменов.")
                except Exception as e:
                    self._update_center_text(f"Ошибка сохранения targets: {e}")

        event.app.create_background_task(_coro())

    def handle_threads(self, event) -> None:
        """Обработчик для настройки потоков."""
        if self.is_scanning:
            return

        async def _coro():
            # Создаем стиль без тени для диалога
            no_shadow_style = Style.from_dict({
                "dialog": "bg:default",
                "dialog shadow": "bg:default",
                "shadow": "bg:default",
                "text-area": "bg:white",
                "textarea": "bg:white",
            })

            dialog = input_dialog(
                title='Threads',
                text=f'Введите кол-во потоков ({"/".join(map(str, sorted(self.ALLOWED_THREADS)))}):',
                style=no_shadow_style  # Добавляем стиль без тени
            )

            new_threads = await self._show_dialog_async(dialog)

            if new_threads:
                try:
                    value = int(new_threads)
                    if value in self.ALLOWED_THREADS:
                        self.threads = value
                        self._update_center_text(f"Threads установлены на {value}")
                    else:
                        self._update_center_text(
                            f"Неверное значение. Разрешено: {', '.join(map(str, sorted(self.ALLOWED_THREADS)))}."
                        )
                except ValueError:
                    self._update_center_text("Ошибка: введите число.")

        event.app.create_background_task(_coro())

    def handle_wordlist(self, event) -> None:
        """Обработчик для выбора словаря."""
        if self.is_scanning:
            return

        async def _coro():
            # Создаем стиль без тени для диалога
            no_shadow_style = Style.from_dict({
                "dialog": "bg:default",
                "dialog shadow": "bg:default",
                "shadow": "bg:default",
                "text-area": "bg:white",
                "textarea": "bg:white",
            })

            dialog = input_dialog(
                title='Wordlist',
                text=f'Размер словаря ({"/".join(self.WORDLIST_LEVELS)}):',
                style=no_shadow_style  # Добавляем стиль без тени
            )

            choice = await self._show_dialog_async(dialog)

            if choice:
                choice = choice.strip().lower()
                if choice in self.WORDLIST_LEVELS:
                    self.wordlist_level = choice
                    self._update_center_text(f"Wordlist: {choice}")
                else:
                    self._update_center_text(
                        f"Неверный выбор. Допустимо: {', '.join(self.WORDLIST_LEVELS)}."
                    )

        event.app.create_background_task(_coro())

    def handle_dns(self, event) -> None:
        """Обработчик для настройки DNS."""
        if self.is_scanning:
            return

        async def _coro():
            # Создаем стиль без тени для диалога
            no_shadow_style = Style.from_dict({
                "dialog": "bg:default",
                "dialog shadow": "bg:default",
                "shadow": "bg:default",
                "text-area": "bg:white",
                "textarea": "bg:white",
            })

            dialog = input_dialog(
                title='DNS',
                text='Введите custom DNS (пусто для system):',
                style=no_shadow_style  # Добавляем стиль без тени
            )

            new_dns = await self._show_dialog_async(dialog)

            self.dns_resolver = new_dns if new_dns else None
            self._update_center_text(f"DNS: {self.dns_resolver or 'system'}")

        event.app.create_background_task(_coro())

    def handle_output(self, event) -> None:
        """Обработчик для настройки выходного файла."""
        if self.is_scanning:
            return

        async def _coro():
            # Создаем стиль без тени для диалога
            no_shadow_style = Style.from_dict({
                "dialog": "bg:default",
                "dialog shadow": "bg:default",
                "shadow": "bg:default",
                "text-area": "bg:white",
                "textarea": "bg:white",
            })

            dialog = input_dialog(
                title='Output',
                text='Введите путь для CSV:',
                default=self.output_csv,
                style=no_shadow_style  # Добавляем стиль без тени
            )

            new_output = await self._show_dialog_async(dialog)

            if new_output:
                self.output_csv = new_output
                self._update_center_text(f"Output: {self.output_csv}")

        event.app.create_background_task(_coro())

    def handle_lang(self, event) -> None:
        """Обработчик для смены языка."""
        if self.is_scanning:
            return
        self.lang = 'EN' if self.lang == 'RU' else 'RU'
        self._update_center_text(f"Язык изменён на {self.lang}")
        self.center.content.text = self._get_instruction_text()

    def handle_run(self, event) -> None:
        """Обработчик для запуска сканирования."""
        if self.is_scanning:
            self._update_center_text("Сканирование уже запущено!")
            return

        async def _coro():
            self.is_scanning = True
            # Очищаем предыдущие сообщения ПРАВИЛЬНО ЗДЕСЬ!
            if hasattr(self, '_scan_messages'):
                self._scan_messages = []
            wordlist_path = f'resources/wordlists/{self.wordlist_level}.txt'

            self._update_center_text("Сканирование запущено...\n")

            try:
                # Создаем callback для логов
                def log_callback(message: str):
                    self._log_scan_message(message)

                results, unique_ips = await run_scan_async(
                    targets_path=self.targets_path,
                    wordlist_path=wordlist_path,
                    output_csv=self.output_csv,
                    threads=self.threads,
                    dns_server=self.dns_resolver,
                    progress_callback=self._show_scan_progress,
                    log_callback=log_callback  # Добавляем callback для логов
                )

                # Если прервали — просто выходим
                if not self.is_scanning:
                    return

                # Печать результата
                total_subdomains = sum(len(r) for r in results.values())
                log_text = (
                    f"Сканирование завершено!\n"
                    f"Найдено субдоменов: {total_subdomains}\n"
                    f"Уникальных IP: {len(unique_ips)}\n"
                    f"Результаты сохранены в {self.output_csv} и unique_ips.txt"
                )
                self._update_center_text(log_text)

            except asyncio.CancelledError:
                # ничего не делаем — текст уже показан в _cancel_scan()
                pass

            except Exception as e:
                self._update_center_text(f"Ошибка при сканировании: {str(e)}")

            finally:
                self.is_scanning = False

        self.scan_task = event.app.create_background_task(_coro())

    def handle_quit(self, event):
        if self.is_scanning:
            self._cancel_scan()
        else:
            event.app.exit(result="\nBigBrother shutting down...\n")

    def _build_style(self) -> Style:
        """Создание стилей для приложения."""
        return Style.from_dict({
            "banner": "bold fg:white",
            "center": "fg:white",
            "menu": "fg:black bold bg:white bold",
            "menu.focused": "fg:white bg:black bold",
            "menu.key": "fg:white bold",
            "line": "fg:#aaaaaa",
            "cursor": "hidden",
            # Убираем тень полностью
            "dialog": "bg:default",
            "dialog.body": "bg:default",
            "dialog shadow": "bg:default",
            "dialog.shadow": "bg:default",
            "shadow": "bg:default",
            "text-area": "bg:default",
            "textarea": "bg:default"
        })

    def run(self) -> None:
        """Запуск приложения."""
        try:
            os.system("clear")
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

            result = self.app.run()

            os.system("clear")
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

            time.sleep(0.5)
            print(result)

        except Exception as e:
            print(f"Ошибка при запуске приложения: {e}")
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()