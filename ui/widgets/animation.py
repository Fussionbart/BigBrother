import os
import time
import asyncio
from typing import List


class AnimationPlayer:
    """Проигрыватель анимации с поддержкой асинхронности."""

    def __init__(self, text_area, fps: int = 12):
        self.text_area = text_area
        self.fps = fps
        self.frames = self._load_frames()
        self.is_playing = False

    def _load_frames(self) -> List[str]:
        """Загружает кадры анимации из папки."""
        path = "resources/animation_frames"
        frames = []

        if not os.path.exists(path):
            return ["🎯 BigBrother Scanner\n   No animation frames found"]

        try:
            for file in sorted(os.listdir(path)):
                if file.endswith(".txt"):
                    file_path = os.path.join(path, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        frames.append(f.read())
        except Exception as e:
            return [f"Error loading animation: {str(e)}"]

        if not frames:
            return ["🎯 BigBrother Scanner\n   Ready to scan"]

        # Если один кадр — создаем несколько для плавности
        if len(frames) == 1:
            return frames * 8
        else:
            return frames * 3

    async def play_async(self) -> None:
        """Асинхронно проигрывает анимацию."""
        self.is_playing = True
        try:
            for frame in self.frames:
                if not self.is_playing:
                    break
                self.text_area.text = frame
                await asyncio.sleep(1 / self.fps)
        finally:
            self.is_playing = False

    def play(self) -> None:
        """Синхронно проигрывает анимацию."""
        self.is_playing = True
        try:
            for frame in self.frames:
                if not self.is_playing:
                    break
                self.text_area.text = frame
                time.sleep(1 / self.fps)
        finally:
            self.is_playing = False

    def stop(self) -> None:
        """Останавливает анимацию."""
        self.is_playing = False