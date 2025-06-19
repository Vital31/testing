from hashlib import sha3_256

study_group = "211-331"  # Укажите номер учебной группы
fullname = "Фамилия Имя Отчество"  # Укажите свои ФИО
suffix = "Высоконагруженные системы. Лабораторная работа 4"
msg = f"{study_group} {fullname} {suffix}"
var_total = 10
variant = int(sha3_256(msg.encode('utf-8')).hexdigest(), 16) % var_total + 1
print(f"Вариант лабораторной работы: {variant}")

if __name__ == "__main__":
    print(f"Запуск системы обработки данных IoT (Вариант {variant})")
    print("=" * 50) 