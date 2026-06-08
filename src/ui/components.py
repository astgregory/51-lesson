# Импорт необходимых библиотек и модулей
import flet as ft  # Фреймворк для создания пользовательского интерфейса
from .styles import AppStyles  # Импорт стилей приложения
import asyncio  # Библиотека для асинхронного программирования
import os


class MessageBubble(ft.Container):
    """
    Компонент "пузырька" сообщения в чате.

    Наследуется от ft.Container для создания стилизованного контейнера сообщения.
    Отображает сообщения пользователя и AI с разными стилями и позиционированием.

    Args:
        message (str): Текст сообщения для отображения
        is_user (bool): Флаг, указывающий, является ли это сообщением пользователя
    """

    def __init__(self, message: str, is_user: bool):
        # Инициализация родительского класса Container
        super().__init__()

        # Настройка отступов внутри пузырька
        self.padding = 10

        # Настройка скругления углов пузырька
        self.border_radius = 10

        # Установка цвета фона в зависимости от отправителя:
        # - Синий для сообщений пользователя
        # - Серый для сообщений AI
        self.bgcolor = ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700

        # Установка выравнивания пузырька:
        # - Справа для сообщений пользователя
        # - Слева для сообщений AI
        self.alignment = ft.alignment.center_right if is_user else ft.alignment.center_left

        # Настройка внешних отступов для создания эффекта диалога:
        # - Отступ слева для сообщений пользователя
        # - Отступ справа для сообщений AI
        # - Небольшие отступы сверху и снизу для разделения сообщений
        self.margin = ft.margin.only(
            left=50 if is_user else 0,  # Отступ слева
            right=0 if is_user else 50,  # Отступ справа
            top=5,  # Отступ сверху
            bottom=5  # Отступ снизу
        )

        # Создание содержимого пузырька
        self.content = ft.Column(
            controls=[
                # Текст сообщения с настройками отображения
                ft.Text(
                    value=message,  # Текст сообщения
                    color=ft.Colors.WHITE,  # Белый цвет текста
                    size=16,  # Размер шрифта
                    selectable=True,  # Возможность выделения текста
                    weight=ft.FontWeight.W_400  # Нормальная толщина шрифта
                )
            ],
            tight=True  # Плотное расположение элементов в колонке
        )


class ModelSelector(ft.Dropdown):
    """
    Выпадающий список для выбора AI модели с функцией поиска.

    Наследуется от ft.Dropdown для создания кастомного выпадающего списка
    с дополнительным полем поиска для фильтрации моделей.

    Args:
        models (list): Список доступных моделей в формате:
                      [{"id": "model-id", "name": "Model Name"}, ...]
    """

    def __init__(self, models: list):
        # Инициализация родительского класса Dropdown
        super().__init__()

        # Применение стилей из конфигурации к компоненту
        for key, value in AppStyles.MODEL_DROPDOWN.items():
            setattr(self, key, value)

        # Настройка внешнего вида выпадающего списка
        self.label = None  # Убираем текстовую метку
        self.hint_text = "Выбор модели"  # Текст-подсказка

        # Создание списка опций из предоставленных моделей
        self.options = [
            ft.dropdown.Option(
                key=model['id'],  # ID модели как ключ
                text=model['name']  # Название модели как отображаемый текст
            ) for model in models
        ]

        # Сохранение полного списка опций для фильтрации
        self.all_options = self.options.copy()

        # Установка начального значения (первая модель из списка)
        self.value = models[0]['id'] if models else None

        # Создание поля поиска для фильтрации моделей
        self.search_field = ft.TextField(
            on_change=self.filter_options,  # Функция обработки изменений
            hint_text="Поиск модели",  # Текст-подсказка в поле поиска
            **AppStyles.MODEL_SEARCH_FIELD  # Применение стилей из конфигурации
        )

    def filter_options(self, e):
        """
        Фильтрация списка моделей на основе введенного текста поиска.

        Args:
            e: Событие изменения текста в поле поиска
        """
        # Получение текста поиска в нижнем регистре
        search_text = self.search_field.value.lower() if self.search_field.value else ""

        # Если поле поиска пустое - показываем все модели
        if not search_text:
            self.options = self.all_options
        else:
            # Фильтрация моделей по тексту поиска
            # Ищем совпадения в названии или ID модели
            self.options = [
                opt for opt in self.all_options
                if search_text in opt.text.lower() or search_text in opt.key.lower()
            ]

        # Обновление интерфейса для отображения отфильтрованного списка
        e.page.update()


# Окно входа в приложение с системой аутентификации.
class LoginWindow(ft.Container):

    # Инициализация окна входа
    def __init__(self, on_login_success, cache):
        super().__init__()
        self.on_login_success = on_login_success
        self.cache = cache
        self.current_state = "check_auth"  # Состояние: check_auth, api_input, pin_input

        # Создание компонентов интерфейса
        self.create_ui()

        # Проверка существующих данных аутентификации будет выполнена после добавления на страницу
        self._pending_auth_check = True

    # Создание пользовательского интерфейса окна входа
    def create_ui(self):
        # Заголовок
        self.title = ft.Text(
            "Добро пожаловать в AI Chat",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE
        )

        # Поле ввода API ключа
        self.api_key_input = ft.TextField(
            label="API ключ OpenRouter",
            password=True,
            hint_text="Введите ваш API ключ",
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_600,
            text_size=16,
            width=400
        )

        # Поле ввода PIN
        self.pin_input = ft.TextField(
            label="PIN код",
            password=True,
            hint_text="Введите 4-значный PIN",
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_600,
            text_size=16,
            width=200,
            max_length=4
        )

        # Кнопка входа
        self.login_button = ft.ElevatedButton(
            text="Войти",
            on_click=self.handle_login,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            width=200,
            height=50
        )

        # Кнопка сброса ключа
        self.reset_key_button = ft.TextButton(
            text="Сбросить ключ",
            on_click=self.reset_api_key
        )

        # Индикатор загрузки
        self.loading_indicator = ft.ProgressRing(
            visible=False,
            color=ft.Colors.BLUE_400
        )

        # Сообщение об ошибке
        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED_400,
            size=14,
            text_align=ft.TextAlign.CENTER,
            visible=False
        )

        # Сообщение об успехе
        self.success_text = ft.Text(
            "",
            color=ft.Colors.GREEN_400,
            size=14,
            text_align=ft.TextAlign.CENTER,
            visible=False
        )

        # Контейнер для API ключа
        self.api_key_container = ft.Column([
            ft.Text(
                "Введите API ключ OpenRouter",
                size=16,
                color=ft.Colors.GREY_300,
                text_align=ft.TextAlign.CENTER
            ),
            self.api_key_input,
            ft.Row([
                self.login_button,
                self.loading_indicator
            ], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # Контейнер для PIN
        self.pin_container = ft.Column([
            ft.Text(
                "Введите PIN код для входа",
                size=16,
                color=ft.Colors.GREY_300,
                text_align=ft.TextAlign.CENTER
            ),
            self.pin_input,
            ft.Row([
                self.login_button,
                self.loading_indicator
            ], alignment=ft.MainAxisAlignment.CENTER),
            self.reset_key_button
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # Основной контейнер
        self.content = ft.Column([
            self.title,
            ft.Container(height=40),  # Отступ
            self.api_key_container,  # Показываем только одно окно за раз
            self.error_text,
            self.success_text
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # Стили контейнера
        self.padding = 40
        self.bgcolor = ft.Colors.GREY_900
        self.border_radius = 20
        self.width = 500
        self.alignment = ft.alignment.center

    # Проверяем, есть ли сохраненные данные аутентификации
    def check_auth_state(self):
        has_data = self.cache.has_auth_data()

        if has_data:
            # Есть сохраненные данные - показываем форму PIN
            self.show_pin_input()
        else:
            # Нет данных - показываем форму API ключа
            self.show_api_input()

    # Показать поле ввода API ключа
    def show_api_input(self):
        self.current_state = "api_input"
        # Заменяем содержимое на форму API ключа
        self.content.controls[2] = self.api_key_container
        # НЕ устанавливаем фокус здесь - это может вызвать ошибку
        self.update()

    # Показать поле ввода PIN
    def show_pin_input(self):
        self.current_state = "pin_input"
        # Заменяем содержимое на форму PIN
        self.content.controls[2] = self.pin_container
        # НЕ устанавливаем фокус здесь - это может вызвать ошибку
        self.update()

    # Инициализация после добавления на страницу
    def initialize_after_page_add(self):
        if hasattr(self, '_pending_auth_check') and self._pending_auth_check:
            self.check_auth_state()
            self._pending_auth_check = False

    # Показать сообщение об ошибке
    def show_error(self, message: str):
        self.error_text.value = message
        self.error_text.visible = True
        self.success_text.visible = False
        self.update()

    # Показать сообщение об успехе
    def show_success(self, message: str):
        self.success_text.value = message
        self.success_text.visible = True
        self.error_text.visible = False
        self.update()

    # Очистить все сообщения
    def clear_messages(self):
        self.error_text.visible = False
        self.success_text.visible = False
        self.update()

    # Установить состояние загрузки
    def set_loading(self, loading: bool):
        self.loading_indicator.visible = loading
        self.login_button.disabled = loading
        self.update()

    # Обработка кнопки входа
    async def handle_login(self, e):
        self.clear_messages()
        self.set_loading(True)

        try:
            if self.current_state == "api_input":
                await self.handle_api_key_login()
            elif self.current_state == "pin_input":
                await self.handle_pin_login()
        except Exception as error:
            self.show_error(f"Ошибка: {str(error)}")
        finally:
            self.set_loading(False)

    # Обработка входа по API ключу
    async def handle_api_key_login(self):
        api_key = self.api_key_input.value.strip()

        if not api_key:
            self.show_error("Введите API ключ")
            return

        try:
            from src.api.openrouter import OpenRouterClient
            os.environ["OPENROUTER_API_KEY"] = api_key  # Временно устанавливаем ключ в env для проверки
            temp_client = OpenRouterClient()  # Создаём временный клиент и проверяем баланс
            balance_str = temp_client.get_balance()

            if not balance_str or "Ошибка" in balance_str:  # Если ошибка выполнения запроса — отклоняем ключ
                os.environ.pop("OPENROUTER_API_KEY", None)  # Удаляем временный ключ из env
                self.show_error("Неверный API ключ или ошибка подключения")
                return

            # Парсим числовой баланс
            try:
                # Обрезаем символ '$' и преобразуем в float
                bal_value = float(balance_str.replace('$', '').strip())
            except Exception:
                os.environ.pop("OPENROUTER_API_KEY", None)
                self.show_error("Не удалось определить баланс (ошибка формата).")
                return

            # if bal_value <= 0.0:
            if bal_value < 0.0:
                # Баланс отрицательный — отклоняем ключ
                os.environ.pop("OPENROUTER_API_KEY", None)
                self.show_error("Баланс должен быть положительным для использования приложения.")
                return

            # Баланс положительный — генерируем/восстанавливаем PIN и сохраняем ключ+PIN в БД
            stored_api_key, stored_pin = self.cache.get_auth_data()
            normalized_api_key = api_key.strip()
            normalized_stored_key = stored_api_key.strip() if stored_api_key else ""

            if normalized_stored_key == normalized_api_key and stored_pin:
                pin = stored_pin
                self.show_success(f"API ключ найден! Ваш PIN: {pin}")
            else:
                import random
                pin = str(random.randint(1000, 9999)).zfill(4)
                self.cache.save_auth_data(normalized_api_key, pin)
                self.show_success(f"Новый API ключ успешно сохранен! Ваш PIN: {pin}")

            # Удаляем ключ из env.
            os.environ.pop("OPENROUTER_API_KEY", None)

            await asyncio.sleep(2)
            self.show_pin_input()

        except Exception as e:
            # В случае исключения убедимся, что временный ключ удалён
            os.environ.pop("OPENROUTER_API_KEY", None)
            self.show_error(f"Ошибка проверки API ключа: {str(e)}")

    # Обработка входа по PIN
    async def handle_pin_login(self):
        pin = self.pin_input.value.strip()

        if not pin:
            self.show_error("Введите PIN код")
            return

        # Проверяем PIN
        stored_api_key, stored_pin = self.cache.get_auth_data()

        if pin == stored_pin:
            # Успешный вход
            self.show_success("Вход выполнен успешно!")

            # Устанавливаем API ключ в переменные окружения
            os.environ["OPENROUTER_API_KEY"] = stored_api_key

            # Вызываем callback успешного входа
            await asyncio.sleep(1)
            if asyncio.iscoroutinefunction(self.on_login_success):
                await self.on_login_success()
            else:
                self.on_login_success()
        else:
            self.show_error("Неверный PIN код")
            self.pin_input.value = ""
            # НЕ устанавливаем фокус здесь - это может вызвать ошибку

    # Сброс API ключа
    async def reset_api_key(self, e):
        try:
            # Очищаем данные аутентификации
            self.cache.clear_auth_data()

            # Показываем форму API ключа
            self.show_api_input()

            # Очищаем поля ввода
            self.api_key_input.value = ""
            self.pin_input.value = ""

            # Очищаем сообщения
            self.clear_messages()

        except Exception as error:
            self.show_error(f"Ошибка сброса ключа: {str(error)}")