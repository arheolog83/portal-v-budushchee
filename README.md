# Портал в будущее

Конкурсный проект команды «Старт» гимназии №12 Волгограда для хакатона «Идея фикс».

Это веб-приложение для учителей 5–11 классов с двумя разделами: «ИИ-помощник учителя» для создания заданий через GigaChat и «Умное расписание» для планирования недельной нагрузки.

«Умное расписание» составляет пяти- или шестидневное расписание с заданным ограничением уроков в день. Собственный детерминированный алгоритм сохраняет количество часов по предметам, учитывает их условную когнитивную сложность, выравнивает нагрузку по дням и старается избегать повторов и соседства сложных занятий.

## Установка и запуск

Требуется Python 3.10 или новее.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Перед запуском задайте полученную в кабинете GigaChat строку авторизации OAuth:

```bash
export GIGACHAT_CREDENTIALS="ваша_строка_авторизации"
```

В Windows PowerShell:

```powershell
$env:GIGACHAT_CREDENTIALS="ваша_строка_авторизации"
```

`GIGACHAT_CREDENTIALS` — единственная обязательная переменная. Дополнительно можно задать `GIGACHAT_SCOPE` (по умолчанию `GIGACHAT_API_PERS`), `GIGACHAT_MODEL` (по умолчанию `GigaChat`) и `GIGACHAT_CA_BUNDLE` — путь к файлу доверенного сертификата, если он требуется в вашей системе. Секрет используется только сервером и не передаётся браузеру.

Для Windows команда активации окружения:

```powershell
.venv\Scripts\activate
```

После запуска откройте в браузере: http://127.0.0.1:8000

## Запуск в Docker на Windows

В PowerShell из папки проекта соберите образ:

```powershell
docker build -t portal-v-budushchee:latest .
```

Задайте секрет GigaChat только в окружении текущего PowerShell и запустите контейнер:

```powershell
$env:GIGACHAT_CREDENTIALS="ваша_строка_авторизации"
docker run --rm --name portal-v-budushchee -p 8000:8000 `
  -e GIGACHAT_CREDENTIALS `
  portal-v-budushchee:latest
```

После запуска приложение доступно по адресу: http://localhost:8000

В образ не записываются ключи или настройки GigaChat. Все параметры передаются при запуске контейнера:

- `GIGACHAT_CREDENTIALS` — обязательная строка авторизации OAuth;
- `GIGACHAT_SCOPE` — область доступа, по умолчанию `GIGACHAT_API_PERS`;
- `GIGACHAT_MODEL` — модель, по умолчанию `GigaChat`;
- `GIGACHAT_CA_BUNDLE` — необязательный путь к сертификату внутри контейнера. Сам файл нужно подключить отдельным read-only bind mount.

Необязательные значения можно задать в PowerShell и передать тем же способом:

```powershell
$env:GIGACHAT_SCOPE="GIGACHAT_API_PERS"
$env:GIGACHAT_MODEL="GigaChat"
docker run --rm -p 8000:8000 `
  -e GIGACHAT_CREDENTIALS `
  -e GIGACHAT_SCOPE `
  -e GIGACHAT_MODEL `
  portal-v-budushchee:latest
```
