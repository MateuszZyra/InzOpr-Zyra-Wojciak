# RiskR

Lokalne laboratorium do testowania odporności usług przez kontrolowane symulowanie awarii.

**Zespół:** Mateusz Zyra i Adam Wójciak.

## Funkcje v1

- W01: dwie usługi demonstracyjne i sprawdzenie ich gotowości.
- W02: wybór HTTP 500, opóźnienia, przeciążenia lub niedostępności, zapis konfiguracji i walidacja parametrów.
- W03: pomiary HTTP na żywo, ręczne zatrzymanie i automatyczne zakończenie testu.
- Trwała baza SQLite, jeden aktywny eksperyment i limit czasu 300 s.

## Uruchomienie na Windows

Wymagania: Python 3.12 lub nowszy z modułami venv, pip i sqlite3. W katalogu projektu wykonaj:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py init-db
.\.venv\Scripts\python.exe app.py run
```

Otwórz [http://127.0.0.1:5000](http://127.0.0.1:5000). Zatrzymanie serwera: Ctrl+C. Przy zajętym porcie dopisz `--port 5050` do polecenia uruchomienia i otwórz port 5050.

Na stanowisku weryfikacyjnym Python był dostarczony w środowisku narzędziowym i nie był zarejestrowany w programie `py`. Na zwykłym stanowisku można zainstalować go z [python.org](https://www.python.org/downloads/). Każdy komputer tworzy własne środowisko `.venv`; nie należy kopiować tego katalogu między komputerami.

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py init-db
.venv/bin/python app.py run
```

## Baza i tryb lokalny

`init-db` tworzy tabele i dwie usługi demonstracyjne bez usuwania istniejących danych. Baza znajduje się w `instance/riskr.sqlite3`. Opcja `--database` pozwala podać inny plik zarówno podczas inicjalizacji, jak i startu.

Tryb v1 jest jednoosobowy i nie wymaga logowania. Cele to wyłącznie `demo-api` i `demo-worker`, działające na serwerze HTTP w procesie aplikacji, na losowym porcie `127.0.0.1`. Formularz nie przyjmuje zewnętrznych URL-i. Przeciążenie oznacza dodatkowe żądania do usługi demo, a nie obciążanie całego komputera.

Ograniczenie celów nie stanowi izolacji systemowej. `isolation_verified` pozostaje fałszywe; `target_scope_verified` potwierdza gotowość laboratorium. Po awaryjnym restarcie zakłócenia starego procesu przestają istnieć, a przerwane testy otrzymują status `failed` z zachowaniem pomiarów.

Uruchamiaj aplikację przez `app.py run`. Nie używaj reloadera Flask ani kilku workerów na tej samej bazie. Blokada pliku zabezpiecza uruchomienia przez udostępnione polecenie CLI.

## Wariant kontenerowy

Wymaga Docker Engine / Docker Desktop i Docker Compose:

```text
docker compose up --build
```

Konfiguracja publikuje port tylko na `127.0.0.1:5000`, stosuje sieć `internal`, limity zasobów i wolumen `riskr-data`. `docker compose down` zatrzymuje środowisko i zachowuje bazę. Wariant nie został uruchomiony na stanowisku testowym, na którym nie ma Dockera.

## Pierwszy eksperyment

1. W W01 wybierz konfigurację `demo-api`.
2. Ustaw opóźnienie 500 ms i czas 30 s.
3. Zapisz konfigurację lub uruchom eksperyment.
4. Obserwuj pomiary w W03. Bazowa obsługa trwa około 120 ms, dlatego z dodatkowym opóźnieniem średnia wyniesie zwykle nieco ponad 620 ms.
5. Poczekaj na koniec lub użyj przycisku zatrzymania.

Interfejs pobiera dane co 5 s. Okna pomiarowe zamykane są między sondami, dlatego wolna odpowiedź lub timeout mogą opóźnić zamknięcie okna. Przy zatrzymywaniu żądanie w toku może trafić do ostatniego, krótszego okna.

## Testy

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Testy tworzą osobne bazy pod `tmp` oraz lokalne usługi HTTP. Nie korzystają z bazy użytkownika ani zewnętrznych celów. Wynik weryfikacji: **16 testów, wszystkie zakończone powodzeniem**. Szczegóły zawiera [raport testów](docs/testy-v1.md).

## Struktura

```text
app.py                 routing, formularze, API i polecenia startowe
riskr/db.py            schemat SQLite, inicjalizacja i agregacja
riskr/laboratory.py    usługi demonstracyjne i zakłócenia HTTP
riskr/engine.py        runner i reguły eksperymentów
templates/             widoki W01–W03
static/                style i monitorowanie
tests/                 testy automatyczne
docs/                  dokumentacja
```

## Dokumentacja

- [Mapa projektu v1](docs/roadmap-v1.md).
- [Technologie i architektura](docs/technologie.md).
- [Prompty i korekty implementacji](docs/prompty-v1.md).
- [Wyniki testów](docs/testy-v1.md).
- [Zadania projektu](docs/labochat-zadania.md).
- [Lista funkcjonalności PDF](output/pdf/RiskR_lista_funkcjonalnosci.pdf).

Wykresy historyczne, porównanie faz przed/w trakcie/po awarii i raporty pozostają poza v1.
