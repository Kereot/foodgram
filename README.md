<h1 align="center">Добро пожаловать в Foodgram</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-1.0-blue.svg?cacheSeconds=2592000" />
  <a href="#" target="_blank">
    <img alt="License: MIT license" src="https://img.shields.io/badge/License-MIT license-yellow.svg" />
  </a>
  <a href="https://github.com/Kereot/foodgram/actions/workflows/main.yml">
    <img alt="Workflow" src="https://github.com/Kereot/foodgram/actions/workflows/main.yml/badge.svg?branch=main" />
  </a>
</p>

> Foodgram - это разворачиваемый сайт, где зарегистрированные пользователи 
могут делиться рецептами блюд, добавляя информацию об ингредиентах, времени и 
порядке приготовления, изображении готового блюда. Все пользователи могут также 
просматривать рецепты, выложенные другими пользователями.

### [Страница проекта](https://github.com/Kereot/foodgram)

### [Адрес сайта](https://foodgram.kereot.dev/)

### [Документация redoc](https://foodgram.kereot.dev/api/docs/)

## Описание проекта

Проект реализован на Django, React и Docker.
### Стек технологий:

[![Stack](https://skillicons.dev/icons?i=py,django,react,nginx,postgres,docker,ubuntu,github)](https://skillicons.dev)

### Основные возможности:
- регистрация пользователей;
- авторизация по имейлу и паролю, возможность смены пароля;
- создание записей о рецептах, их редактирование и удаление:
  + название,
  + теги (выбор из списка),
  + ингредиенты (выбор из списка) с указанием количества,
  + время приготовления,
  + описание процесса приготовления,
  + изображение (например, фотография);
- просмотр рецептов, созданных другими пользователями;
- добавление рецептов в избранное для быстрого доступа;
- подписка на других пользователей, что обеспечивает удобный доступ к 
  выложенным ими рецептам;
- добавление рецепта в список покупок, что позволяет получить файл с 
  перечнем необходимых ингредиентов;
- получение короткой ссылки на рецепт;
- панель администратора.

Проект настроен на автоматическое развёртывание docker-контейнерами на 
удалённом ubuntu-сервере с помощью workflow на github. В workflow встроена 
команда отправки сообщения об успешном развертывании в Телеграм.

### Основные энд-поинты:

- /api/users/ - $${\color{green}GET}$$, $${\color{blue}POST}$$ - пользователи;
- /api/users/{id}/ - $${\color{green}GET}$$ - профиль пользователя;
- /api/users/me/ - $${\color{green}GET}$$ - текущий пользователь;
- /api/users/me/avatar/ - $${\color{orange}PUT}$$, $${\color{red}DELETE}$$ - 
  управление аватаром пользователя;
- /api/users/subscriptions/ - $${\color{green}GET}$$ - подписки;
- /api/users/{id}/subscribe/ - $${\color{blue}POST}$$, $${\color{red}DELETE}$$ - управление подпиской;
- /api/users/set_password/ - $${\color{blue}POST}$$ - изменение пароля;
- /api/auth/token/login/ | /api/auth/token/logout/ - $${\color{blue}POST}$$ - токены авторизации;
- /api/tags/ - $${\color{green}GET}$$ - теги;
- /api/tags/{id}/ - $${\color{green}GET}$$ - конкретный тег;
- /api/ingredients/ - $${\color{green}GET}$$ - ингредиенты;
- /api/ingredients/{id}/ - $${\color{green}GET}$$ - конкретный ингредиент;
- /api/recipes/ - $${\color{green}GET}$$, $${\color{blue}POST}$$ - рецепты;
- /api/recipes/{id}/ - $${\color{green}GET}$$, $${\color{orange}PATCH}$$, $${\color{red}DELETE}$$ - управление конкретным рецептом;
- /api/recipes/download_shopping_cart/ - $${\color{green}GET}$$ - получение файла покупок;
- /api/recipes/{id}/get-link/ - $${\color{green}GET}$$ - получение короткой ссылки на рецепт;
- /api/recipes/{id}/favorite/ - $${\color{blue}POST}$$, $${\color{red}DELETE}$$ - управление рецептом в избранном;
- /api/recipes/{id}/shopping_cart/ - $${\color{blue}POST}$$, $${\color{red}DELETE}$$ - управление рецептом в 
  списке покупок.

### Документация локально:

- /api/docs - локально документация будет доступна после запуска 
  backend-приложения при настройке DEBUG=True.

## Установка и запуск

### 1. Клонируйте репозиторий

```sh 
git clone https://github.com/kereot/foodgram.git
```

### 2. Настройте переменные окружения

Создайте на своём удалённом сервере файл .env в директории, в которой будет 
развернут проект. В файле ожидаются следующие переменные:
- DJANGO_SECRET_KEY
- DJANGO_DEBUG (по умолчанию будет False)
- DJANGO_ALLOWED_HOSTS (значения localhost, 127.0.0.1 будут по умолчанию, 
  необходимо указать их и ваш адрес сайта)
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB
- DB_ENGINE (по умолчанию будет postgres, для целей отладки настроено 
  использование sqlite3)
- DB_HOST
- DB_PORT (порт по умолчанию 5432)

> Следующие шаги написаны для автоматического развёртывания через функционал
github на вашем удалённом сервере, работающем на операционной системе ubuntu 
или иной близкой linux-ОС.

### 3. Настройте секретные ключи

В репозитории на github перейдите в Settings->Secrets and variables->Actions.<br>
Добавьте следующие новые секреты репозитория (New Repository Secrets):
* DOCKER_PASSWORD (ваш пароль на DockerHub)
* DOCKER_USERNAME (ваш логин на DockerHub, используйте только строчные символы)
* HOST (ваш ip-адрес удалённого сервера)
* SSH_KEY (закрытый ключ доступа на удалённый сервер)
* TELEGRAM_TO (ваш id в Телеграм)
* TELEGRAM_TOKEN (токен бота в Телеграм)
* USER (имя пользователя на удалённом сервере)

### 4. При необходимости сделайте дополнительные настройки

На удалённом сервере, возможно, придётся настроить обратный прокси сервер.<br> 
Предполагается, что на сервере уже установлена БД PostgreSQL.<br> 
На локальном компьютере необходимо иметь запущенный Docker Engine.

### 5. Commit+Push в ветку main автоматически запустит процесс развёртывания.

GitHub может потребовать плату за это действие, если лимит бесплатных 
запусков workflow исчерпан.

## Автор

Это учебный проект **Kereot**

* Github: [@kereot](https://github.com/kereot)
