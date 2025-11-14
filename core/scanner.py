import dns.resolver
import concurrent.futures
import csv
import random
import string
import os
import asyncio
from typing import List, Optional, Dict, Any, Tuple, Callable


class ScannerError(Exception):
    """Базовое исключение для сканера."""
    pass


class WildcardDetectedError(ScannerError):
    """Исключение при обнаружении wildcard."""
    pass


class FileNotFoundError(ScannerError):
    """Исключение при отсутствии файлов."""
    pass


async def check_wildcard(domain: str, resolver: Optional[dns.resolver.Resolver] = None) -> bool:
    """
    Улучшенная проверка wildcard:
    - Проверяет A и CNAME
    - Делает несколько попыток
    - Сравнивает ответы
    """

    loop = asyncio.get_event_loop()
    res = resolver or dns.resolver

    def resolve_record(name: str):
        """Пытаемся получить A или CNAME запись"""
        try:
            return res.resolve(name, 'A')
        except Exception:
            try:
                return res.resolve(name, 'CNAME')
            except Exception:
                return None

    results = []
    attempts = 3  # кол-во случайных поддоменов

    for _ in range(attempts):
        random_sub = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + '.' + domain
        try:
            ans = await loop.run_in_executor(None, lambda: resolve_record(random_sub))
            if ans is None:
                results.append(None)
            else:
                results.append(sorted([str(r) for r in ans]))
        except Exception:
            results.append(None)

    # Если ВСЕ ответы пустые → wildcard точно нет
    if all(r is None for r in results):
        return False

    # Если ВСЕ ответы одинаковые → 99% wildcard
    unique = set([tuple(r) if r else None for r in results])
    return len(unique) == 1


async def resolve_subdomain(sub: str, domain: str, resolver: Optional[dns.resolver.Resolver] = None) -> Optional[
    Tuple[str, List[str]]]:
    """Разрешает субдомен в IP адреса."""
    full = f"{sub}.{domain}"
    try:
        loop = asyncio.get_event_loop()
        res = resolver or dns.resolver
        answers = await loop.run_in_executor(None, lambda: res.resolve(full, 'A'))
        ips = [str(ip) for ip in answers]
        return full, ips
    except Exception:
        return None


async def scan_domain(
        domain: str,
        wordlist_path: str,
        threads: int = 50,
        resolver: Optional[dns.resolver.Resolver] = None,
        progress_callback: Optional[Callable] = None
) -> List[Tuple[str, List[str]]]:
    """Сканирует один домен на наличие субдоменов."""

    # Проверка wildcard
    if await check_wildcard(domain, resolver):
        raise WildcardDetectedError(f"Wildcard detected for {domain}")

    # Загрузка словаря
    if not os.path.exists(wordlist_path):
        raise FileNotFoundError(f"Wordlist not found: {wordlist_path}")

    with open(wordlist_path, 'r', encoding='utf-8') as f:
        subs = [line.strip() for line in f if line.strip()]

    if not subs:
        return []

    results = []
    total = len(subs)

    # Асинхронное сканирование с ограничением количества одновременных задач
    semaphore = asyncio.Semaphore(threads)

    async def resolve_with_semaphore(sub: str) -> Optional[Tuple[str, List[str]]]:
        async with semaphore:
            return await resolve_subdomain(sub, domain, resolver)

    tasks = [resolve_with_semaphore(sub) for sub in subs]

    for i, task in enumerate(asyncio.as_completed(tasks)):
        try:
            result = await task
            if result:
                results.append(result)

            # Обновление прогресса
            if progress_callback and i % 10 == 0:  # Обновляем каждые 10 задач
                progress_callback(domain, i + 1, total)


        except Exception as e:

            # print(f"Error resolving subdomain: {e}")

            pass  # Просто игнорируем ошибки разрешения

    if progress_callback:
        progress_callback(domain, total, total)

    return results


async def run_scan_async(
        targets_path: str = 'resources/targets.txt',
        wordlist_path: str = 'resources/wordlists/medium.txt',
        output_csv: str = 'output.csv',
        threads: int = 50,
        dns_server: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None
) -> Tuple[Dict[str, List[Tuple[str, List[str]]]], set]:
    """Асинхронно запускает сканирование всех доменов."""

    # Проверка файлов
    if not os.path.exists(targets_path):
        raise FileNotFoundError(f"Targets file not found: {targets_path}")

    # Настройка резолвера
    resolver = None
    if dns_server:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        # Таймауты для избежания зависаний
        resolver.timeout = 5
        resolver.lifetime = 10

    # Загрузка доменов
    with open(targets_path, 'r', encoding='utf-8') as f:
        domains = [line.strip() for line in f if line.strip()]

    if not domains:
        raise ScannerError("No domains found in targets file")

    all_results = {}
    unique_ips = set()

    # Сканирование каждого домена
    for domain in domains:
        # Частая проверка на отмену - даем возможность прерваться
        await asyncio.sleep(0)

        try:
            if progress_callback:
                progress_callback(domain, 0, 0)  # Начало сканирования домена

            results = await scan_domain(domain, wordlist_path, threads, resolver, progress_callback)
            all_results[domain] = results

            # Сбор уникальных IP
            for _, ips in results:
                unique_ips.update(ips)

        except WildcardDetectedError as e:
            if log_callback:
                log_callback(f"Wildcard обнаружен: {domain}")
            else:
                print(f"Warning: {e}")
            all_results[domain] = []

        except Exception as e:
            if log_callback:
                log_callback(f"Ошибка сканирования {domain}: {e}")
            else:
                print(f"Error scanning domain {domain}: {e}")
            all_results[domain] = []

    # Сохранение результатов
    try:
        # CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Main Domain', 'Subdomain', 'IP'])
            for domain, res in all_results.items():
                for sub, ips in res:
                    for ip in ips:
                        writer.writerow([domain, sub, ip])

        # Unique IPs
        with open('unique_ips.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(unique_ips)))

    except Exception as e:
        raise ScannerError(f"Error saving results: {e}")

    return all_results, unique_ips


# Синхронная обертка для обратной совместимости
def run_scan(
        targets_path: str = 'resources/targets.txt',
        wordlist_path: str = 'resources/wordlists/medium.txt',
        output_csv: str = 'output.csv',
        threads: int = 50,
        dns_server: Optional[str] = None
) -> Tuple[Dict[str, List[Tuple[str, List[str]]]], set]:
    """Синхронная обертка для асинхронного сканирования."""
    return asyncio.run(run_scan_async(
        targets_path, wordlist_path, output_csv, threads, dns_server
    ))