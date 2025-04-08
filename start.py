import os
import sys
import subprocess

# Устанавливаем кодировку UTF-8 для консоли Windows
if sys.platform == 'win32':
    os.system('chcp 65001')
    sys.stdout.reconfigure(encoding='utf-8')

def check_dependencies():
    """Проверяет наличие необходимых зависимостей и устанавливает их при необходимости"""
    required_packages = ['python-dotenv', 'pyTelegramBotAPI']
    missing_packages = []
    
    for package in required_packages:
        try:
            # Используем subprocess для проверки наличия пакета
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', package], 
                                   capture_output=True, text=True)
            if result.returncode != 0:
                missing_packages.append(package)
        except Exception:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Установка необходимых зависимостей: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("Зависимости успешно установлены")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при установке зависимостей: {e}")
            return False
    
    return True

def check_env_file():
    """Проверяет наличие файла .env и токена в нем"""
    # Проверяем наличие файла .env
    if not os.path.exists('.env'):
        print("Файл .env не найден. Создаю новый файл...")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('# Токен вашего Telegram бота\n')
            f.write('BOT_TOKEN=\n')
        print("Файл .env создан. Пожалуйста, добавьте в него токен вашего бота и перезапустите скрипт.")
        return False
    
    # Загружаем переменные из .env вручную
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    # Убираем кавычки и пробелы из значения
                    value = value.strip().strip('"\'')
                    os.environ[key.strip()] = value
    except Exception as e:
        print(f"Ошибка при чтении файла .env: {e}")
        return False
    
    # Проверяем наличие токена
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("Ошибка: Токен бота не найден в файле .env")
        print("Пожалуйста, добавьте токен в файл .env в формате: BOT_TOKEN=ваш_токен")
        return False
    
    return True

def run_bot():
    """Запускает бота"""
    print("Запуск бота...")
    try:
        subprocess.run([sys.executable, 'main.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске бота: {e}")
        return False
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
        return True
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("Проверка зависимостей...")
    if not check_dependencies():
        input("Нажмите Enter для выхода...")
        return
        
    print("Проверка конфигурации...")
    if check_env_file():
        run_bot()
    else:
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main() 