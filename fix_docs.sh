#!/bin/bash

# Список Python файлов
python_files=$(find . -name "*.py" -type f)

# Обрабатываем каждый файл
for file in $python_files; do
    echo "Обработка файла: $file"
    
    # Создаем временный файл
    tmp_file=$(mktemp)
    
    # Удаляем строки с тройными кавычками и пустые строки после них
    awk 'BEGIN {in_docstring=0}
    {
        if (in_docstring) {
            if ($0 ~ /"""/) {
                in_docstring=0;
                if ($0 !~ /^"""$/) {
                    sub(/^[ \t]*"""[ \t]*/, "# ", $0);
                    sub(/[ \t]*"""[ \t]*$/, "", $0);
                    if (length($0) > 2) print $0;
                }
            } else {
                sub(/^[ \t]*/, "# ", $0);
                print $0;
            }
        } else {
            if ($0 ~ /"""/) {
                in_docstring=1;
                if ($0 ~ /""".*"""/) {
                    # Однострочный докстринг
                    sub(/^[ \t]*"""/, "# ", $0);
                    sub(/"""[ \t]*$/, "", $0);
                    print $0;
                    in_docstring=0;
                } else if ($0 !~ /^[ \t]*"""[ \t]*$/) {
                    # Начало многострочного докстринга с текстом
                    sub(/^[ \t]*"""[ \t]*/, "# ", $0);
                    print $0;
                } else {
                    # Пустая строка с тройными кавычками
                    sub(/^[ \t]*"""[ \t]*$/, "#", $0);
                    print $0;
                }
            } else {
                print $0;
            }
        }
    }' "$file" > "$tmp_file"
    
    # Заменяем исходный файл
    mv "$tmp_file" "$file"
done

echo "Готово! Все документационные строки в .py файлах заменены на комментарии с #."