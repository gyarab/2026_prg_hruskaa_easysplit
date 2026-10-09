# EasySplit – správa a optimalizace skupinových výdajů

Ročníková práce – webová aplikace v Djangu pro správu sdílených financí
(spolubydlení, cestování ve skupině).

## Funkce
- Registrace a přihlášení uživatelů
- Nezávislé skupiny a členové
- Režimy dělení výdajů: rovným dílem, přesné částky, procenta, váhy
- Položkové účtenky s poměrným dýškem/DPH
- Minimalizace počtu vyrovnávacích plateb
- Více měn s automatickým přepočtem (kurzovní API)
- Generování českých SPD QR kódů
- Export statistik do CSV a PDF
- Hesla se ukládají jako hash (PBKDF2 tzv. osolené), niky ne v čisté podobě. Formuláře jsou chráněné CSRF tokenem.

## Technologie
Python 3.x, Django 5.x, SQLite (vývoj), Bootstrap 5

## Instalace
    git clone <url>
    cd splitly
    python -m venv .venv
    source .venv/bin/activate      # bash: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env
    python manage.py migrate
    python manage.py runserver

## Struktura projektu

## Datový model (zatím)
- User – vlastní model uživatele (AbstractUser)
- Group – skupina (název, popis, základní měna, pozvánkový token)
- Membership – vazba uživatel ↔ skupina s rolí (správce / člen)

## Algoritmus minimalizace transakcí

## Testy
    python manage.py test

## Autor
Jméno Příjmení, třída, školní rok