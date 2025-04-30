import re

def replace_docstrings(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Шаблон для поиска docstrings
    pattern = r'"""(.*?)"""'
    
    # Функция для замены docstrings на однострочные комментарии
    def replace_with_comments(match):
        docstring = match.group(1)
        # Разбиваем docstring на строки
        lines = docstring.strip().split('\n')
        # Добавляем '#' в начало каждой строки
        commented_lines = ['# ' + line.strip() if line.strip() else '#' for line in lines]
        # Соединяем обратно
        return '\n'.join(commented_lines)
    
    # Заменяем все docstrings
    content = re.sub(pattern, replace_with_comments, content, flags=re.DOTALL)
    
    # Записываем обновленное содержимое в файл
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Docstrings в {filename} заменены на однострочные комментарии.")

# Применяем для bot.py
replace_docstrings('bot.py')