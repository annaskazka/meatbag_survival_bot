from pathlib import Path

# Список папок и расширений, которые нужно исключить из обхода
IGNORE_DIRS = {'.git', '.idea', 'venv', '.venv', '__pycache__', '.pytest_cache', 'build', 'dist', 'migrations'}
IGNORE_EXTENSIONS = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.sqlite3', '.db'}
OUTPUT_FILE = 'project_code_dump.txt'


def bundle_project(root_dir='.'):
    root_path = Path(root_dir).resolve()
    output_file_path = root_path / OUTPUT_FILE

    files_count = 0

    with open(output_file_path, 'w', encoding='utf-8') as out_f:
        for path in sorted(root_path.rglob('*')):
            # Пропускаем директории и сам файл отчета
            if path.is_dir() or path.resolve() == output_file_path.resolve():
                continue

            # Проверяем, входит ли файл в игнорируемые директории
            relative_path = path.relative_to(root_path)
            if any(part in IGNORE_DIRS for part in relative_path.parts):
                continue

            # Проверяем расширение файла
            if path.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            # Записываем разделитель и путь к файлу
            out_f.write(f"{'=' * 80}\n")
            out_f.write(f"ФАЙЛ: {relative_path}\n")
            out_f.write(f"{'=' * 80}\n\n")

            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as in_f:
                    out_f.write(in_f.read())
                out_f.write("\n\n")
                files_count += 1
            except Exception as e:
                out_f.write(f"[Не удалось прочитать файл: {e}]\n\n")

    print(f"Готово! Обработано файлов: {files_count}")
    print(f"Результат сохранен в: {output_file_path}")


if __name__ == '__main__':
    bundle_project()