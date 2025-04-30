#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для преобразования документационных строк Python (docstrings) в однострочные комментарии.
Обрабатывает только файлы проекта.
"""

import re
import sys

def process_file(filename):
    """Обрабатывает файл, заменяя docstrings на комментарии с #."""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Шаблон для поиска docstrings
    pattern = r'"""(.*?)"""'
    
    def replace_docstring(match):
        # Получаем текст между тройными кавычками
        docstring = match.group(1)
        # Разбиваем на строки
        lines = docstring.strip().split('\n')
        # Преобразуем каждую строку в комментарий
        commented_lines = []
        for line in lines:
            # Если строка не пустая, добавляем # перед ней
            if line.strip():
                # Убираем лишние отступы
                cleaned_line = line.lstrip()
                commented_lines.append(f"# {cleaned_line}")
            else:
                commented_lines.append("#")
        
        # Соединяем обратно
        return '\n'.join(commented_lines)
    
    # Заменяем docstrings на комментарии
    modified_content = re.sub(pattern, replace_docstring, content, flags=re.DOTALL)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Обработан файл: {filename}")

if __name__ == "__main__":
    # Список основных файлов проекта
    main_files = [
        "bot.py",
        "commands.py",
        "config.py",
        "database.py",
        "main.py",
        "utils.py"
    ]
    
    for filename in main_files:
        process_file(filename)
        
    print("Готово! Все документационные строки в основных файлах заменены на комментарии с #.")