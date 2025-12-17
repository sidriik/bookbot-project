#!/usr/bin/env python3
"""Создание тестовой книги в файле для загрузки."""

import os

# Создаем тестовый файл с книгой
book_text = """ВОЙНА И МИР
Лев Толстой
Том первый

ЧАСТЬ ПЕРВАЯ

I
— Eh bien, mon prince. Gênes et Lucques ne sont plus que des apanages, des поместья, de la famille Buonaparte. Non, je vous préviens que si vous ne me dites pas que nous avons la guerre, si vous vous permettez encore de pallier toutes les infamies, toutes les atrocités de cet Antichrist (ma parole, j'y crois) — je ne vous connais plus, vous n'êtes plus mon ami, vous n'êtes plus мой верный раб, comme vous dites. Ну, здравствуйте, здравствуйте. Je vois que je vous fais peur, садитесь и рассказывайте.

Так говорила в июле 1805 года известная Анна Павловна Шерер, фрейлина и приближенная императрицы Марии Феодоровны, встречая важного и чиновного князя Василия, первого приехавшего на ее вечер. Анна Павловна кашляла несколько дней, у нее был грипп, как она говорила (грипп был тогда новое слово, употреблявшееся только редкими). В записочках, разосланных утром с красным лакеем, было написано без различия во всех:
«Si vous n'avez rien de mieux à faire, Monsieur le comte (или mon prince), et si la perspective de passer la soirée chez une pauvre malade ne vous effraye pas trop, je serai charmée de vous voir chez moi entre 7 et 10 heures. Annette Scherer».

— Dieu, quelle virulente sortie! — отвечал, нисколько не смутясь такою встречей, вошедший князь, в придворном, шитом мундире, в чулках, башмаках и звездах, с светлым выражением плоского лица.

Он говорил на том изысканном французском языке, на котором не только говорили, но и думали наши деды, и с теми тихими, покровительственными интонациями, которые свойственны состаревшемуся в свете и при дворе значительному человеку. Он подошел к Анне Павловне, поцеловал ее руку, подставив ей свою надушенную и сияющую лысину, и покойно уселся на диване.

— Avant tout dites-moi, comment vous allez, chère amie? Успокойте друга, — сказал он, не изменяя голоса и тоном, в котором из-за приличия и участия просвечивало равнодушие и даже насмешка."""

# Сохраняем в файл
filename = "test_book.txt"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(book_text)

print(f" Тестовый файл создан: {filename}")
print(f" Размер: {os.path.getsize(filename)} байт")
print(f" Текст: {len(book_text)} символов")
print("\nТеперь можно загрузить этот файл через бота:")
print("1. Нажмите 'Загрузить файл' в боте")
print("2. Отправьте файл test_book.txt")
print("3. Введите: Война и мир | Лев Толстой | Роман")
