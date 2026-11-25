# RiskR — prompty i decyzje dla wersji v1

**Zespół:** Mateusz Zyra i Adam Wójciak.

## Kontekst projektu

Zakres wejściowy określa [mapa v1](roadmap-v1.md). Zestaw poniżej porządkuje polecenia do odtworzenia kolejnych etapów implementacji. Nie stanowi zapisu dwóch niezależnych rozmów członków zespołu. Narzędziem użytym przy przygotowaniu kodu w tym środowisku był Codex; korzystanie przez każdą osobę z osobnego bezpłatnego czatu nie zostało zweryfikowane.

## P0 — role elementów aplikacji

> Wyjaśnij na przykładzie rezerwacji sali, co robi widok, serwer i baza danych. Następnie odnieś te role do RiskR: konfiguracji eksperymentu, walidacji parametrów i trwałego zapisu pomiarów. Użyj fikcyjnych danych i nie dodawaj logowania do zakresu v1.

**Wniosek:** widok zbiera dane i pokazuje wynik, serwer egzekwuje reguły, a baza zapewnia trwałość. Wyjaśnienie zapisano w [technologiach](technologie.md).

## P1 — wybór technologii

> Pracujemy nad RiskR — lokalnym laboratorium do kontrolowanego symulowania awarii. Cel v1: wybrać usługę demonstracyjną, uruchomić zakłócenie i obserwować reakcję. Widoki: W01 środowisko i usługi, W02 konfiguracja, W03 monitorowanie. Dane: environment, service, experiment i measurement połączone relacjami 1:N. MVP: F01 ograniczone środowisko testowe, F02 wybór czterech awarii, F03 parametry, F04 start i stop, F05 pomiary. System: Windows 11. Zaproponuj dwa zestawy bez płatnych usług, porównaj je i wybierz wariant z mniejszą liczbą procesów oraz zależności. Podaj narzędzia, role i zmiany wymagane w mapie. Nie dodawaj analizy historii ani raportów.

**Decyzja projektowa:** Flask, Jinja, JavaScript, SQLite i Waitress. Zestaw z React, FastAPI i PostgreSQL wymagałby dodatkowej konfiguracji bez korzyści niezbędnych dla obecnego MVP.

## P2 — szkielet i uruchomienie

> Przygotuj lokalny szkielet RiskR w Pythonie 3.12 i Flask. Plik wejściowy: app.py. Dodaj W01, W02 i W03, wspólny szablon, katalog static, requirements.txt i .gitignore. Uruchamiaj aplikację poleceniem python app.py run przez Waitress na 127.0.0.1. Oddziel polecenie inicjalizacji bazy od startu. Nie używaj automatycznego reloadera, ponieważ runner eksperymentów ma działać w jednym procesie. Podaj strukturę plików i sposób sprawdzenia widoków.

**Rezultat:** [app.py](../app.py), [szablony](../templates/base.html), [zależności](../requirements.txt) i instrukcja w [README](../README.md).

## P3 — widoki zgodne z mapą

> Na podstawie docs/roadmap-v1.md przygotuj W01 z gotowością laboratorium i dwiema usługami demo, W02 z wyborem scenariusza, intensywnością i czasem 1–300 s oraz W03 z bieżącymi pomiarami. Zachowaj nawigację i komunikaty błędów. Po zmianie scenariusza dopasuj jednostkę i zakres intensywności; niedostępność ma stałe 100%. W03 odświeża liczby i tabelę co 5 s, oznacza nieaktualne dane i umożliwia zatrzymanie testu. Nie dodawaj wykresów historycznych ani eksportu raportu. Sprawdź zapis konfiguracji, przejście do monitorowania i ręczny stop.

**Rezultat:** trzy widoki, wspólna nawigacja, walidacja przeglądarki i komunikaty zwracane przez serwer.

## P4 — trwała baza

> Dodaj SQLite przez sqlite3 z tabelami environment, service, experiment i measurement. Zachowaj pola i relacje mapy, dostosowując typy do SQLite. Włącz foreign_keys na każdym połączeniu, stosuj parametry zapytań oraz CHECK dla typów zakłóceń, czasu, intensywności i liczników. Inicjalizacja ma być powtarzalna bez usuwania istniejących danych. Dodaj unikalny indeks dla jednego aktywnego eksperymentu i transakcję BEGIN IMMEDIATE. Sprawdź zachowanie konfiguracji i pomiarów po ponownym uruchomieniu procesu.

**Rezultat:** [riskr/db.py](../riskr/db.py), kontrola relacji i trwały plik bazy.

## P5 — funkcjonalności MVP

### P5.1 — F01

> Utwórz dwie wbudowane usługi HTTP: demo-api i demo-worker. Klient pomiarowy może łączyć się tylko z serwerem laboratorium na 127.0.0.1 i wybiera ścieżkę ze stałej listy. Odrzucaj dowolne zewnętrzne adresy i nie korzystaj z proxy środowiskowego. Sprawdź gotowość przed startem. Opisz różnicę między takim ograniczeniem celu a izolacją kontenera. Przygotuj opcjonalny Docker Compose z siecią wewnętrzną i limitami zasobów.

### P5.2 — F02

> Dodaj HTTP 500 dla wskazanego procentu żądań, opóźnienie 1–5000 ms, dodatkowy ruch 1–50 żądań/s i niedostępność przez przerwanie połączenia. Przeciążenie może mieć najwyżej 10 żądań w toku. Sprawdź, czy zakłócenie dotyczy tylko wybranej usługi.

### P5.3 — F03

> Zapisuj i edytuj konfiguracje o statusie draft. Waliduj na serwerze usługę, scenariusz i całkowite wartości parametrów. Odrzuć puste wartości, liczby ułamkowe, wartości logiczne i przekroczenie limitów. Po uruchomieniu zablokuj edycję. Sprawdź, że błędne dane nie tworzą rekordu.

### P5.4 — F04

> Dodaj start, automatyczny koniec oraz idempotentny stop. Tylko jeden eksperyment może być aktywny. Zamknięcie strony nie zatrzymuje runnera. Zakłócenia mają czas ważności. Nie potwierdzaj zakończenia przed usunięciem zakłócenia; przy błędzie użyj cleanup_failed i zablokuj nowy start. Dodaj możliwość ponowienia sprzątania. Po awaryjnym restarcie oznacz przerwane testy jako failed i zachowaj pomiary.

### P5.5 — F05

> Wykonuj sondy HTTP z timeoutem 2 s, niezależnie od ruchu przeciążenia. Agreguj odpowiedzi, HTTP 5xx, timeouty, błędy połączenia i średni czas odpowiedzi. Dostępność to procent odpowiedzi 2xx lub 3xx. Brak pomiarów pokazuj jako brak danych, a po 10 s bez aktualizacji oznacz dane jako nieaktualne. Dla trzech odpowiedzi 2xx, jednej 500 i jednego timeoutu oczekuj dostępności 60%, jednego HTTP 5xx i jednego timeoutu.

**Rezultat:** [laboratorium HTTP](../riskr/laboratory.py), [runner](../riskr/engine.py) oraz powiązanie funkcji z formularzem i API.

## P6 — poprawka na podstawie błędu

> Polecenie testowe: python -m unittest discover -s tests -v, Windows 11, Python 3.12.14. W teście blokady procesu otwórz drugi ProcessLock dla już zablokowanego pliku. Oczekiwany wynik: kontrolowany komunikat o działającej instancji. Rzeczywisty wynik: PermissionError: [Errno 13] Permission denied w self.file.read(1), przed wejściem do bloku try. Popraw wyłącznie obsługę blokady w app.py: obejmij odczyt i inicjalizację pliku obsługą wyjątku oraz zamknij uchwyt po niepowodzeniu. Sprawdź ponownie blokadę i pełny zestaw testów.

**Poprawka:** odczyt i przygotowanie pierwszego bajtu pliku przeniesiono do bloku `try`. Błąd blokady zamyka uchwyt i kończy drugi proces czytelnym komunikatem. Test `test_process_lock_prevents_second_runner` przeszedł.

**Pozostałe korekty implementacji:**

- Pliki tymczasowe testów umieszczono w katalogu `tmp` projektu, ponieważ środowisko uruchomieniowe odmawiało dostępu do systemowego katalogu tymczasowego.
- Test restartu rozszerzono o rzeczywisty start serwera, uruchomienie eksperymentu przez HTTP, zapis pomiarów, przerwanie procesu i ponowny start.
- Agregację okien przeniesiono przed rozpoczęcie kolejnej sondy, aby nowa sonda nie wydłużała zakończonego okna.

## P7 — odbiór wersji

> Porównaj aktualny kod z docs/roadmap-v1.md. Dla F01–F05 podaj dane wejściowe, kroki, oczekiwany wynik i wynik rzeczywisty. Sprawdź wszystkie scenariusze, zły zakres parametrów, równoczesny start, powtórny stop, brak telemetrii, awarię sprzątania i restart procesu. Oddziel testy wykonane od niewykonanych: nie przypisuj wyniku „działa” kontenerom ani drugiemu komputerowi bez uruchomienia. Zapisz wyniki w docs/testy-v1.md.

**Rezultat:** [wyniki testów](testy-v1.md), automatyczne scenariusze w [tests/test_riskr.py](../tests/test_riskr.py) oraz zrzuty widoków w katalogu `docs/screenshots`.
