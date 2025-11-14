import os
import time
import shutil
import sys

from ui.app import BigBrotherApp


def clear_screen():
    """Очищает экран и скрывает курсор."""
    os.system("clear")
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def restore_screen():
    """Восстанавливает курсор."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def show_loading_animation():
    """Показывает анимацию загрузки."""
    columns = shutil.get_terminal_size((80, 20)).columns

    # Статичная анимация
    frames_dir = "resources/animation_frames"
    static_frame = None
    if os.path.isdir(frames_dir):
        try:
            frames = []
            for name in sorted(os.listdir(frames_dir)):
                if name.endswith(".txt"):
                    with open(os.path.join(frames_dir, name), "r", encoding="utf-8") as f:
                        frames.append(f.read())
            if frames:
                static_frame = frames[0]
        except Exception:
            static_frame = None

    # Вывод статичного кадра
    if static_frame:
        lines = static_frame.split('\n')
        max_len = max(len(line) for line in lines)
        left_pad = max(0, (columns - max_len) // 2)
        for line in lines:
            print(' ' * left_pad + line)
        print("\n" * 2)

    # Заголовок
    title = "Loading BigBrother Scanner..."
    title_pad = max(0, (columns - len(title)) // 2)
    print(' ' * title_pad + title)
    print()

    # Прогресс-бар
    bar_width = 40
    bar_pad = max(0, (columns - (bar_width + 2)) // 2)

    for i in range(1, bar_width + 1):
        filled = "█" * i
        empty = "░" * (bar_width - i)
        bar = f"[{filled}{empty}]"
        bar_line = ' ' * bar_pad + bar
        print("\r" + bar_line, end="", flush=True)
        time.sleep(0.02)

    print("\n")
    time.sleep(0.2)


def main():
    """Главная функция приложения."""
    try:
        clear_screen()
        show_loading_animation()

        # Запуск основного приложения
        app = BigBrotherApp()
        app.run()

    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\n\nКритическая ошибка: {e}")
    finally:
        restore_screen()


if __name__ == "__main__":
    main()