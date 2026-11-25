# RiskR — wyniki weryfikacji v1

**Zespół:** Mateusz Zyra i Adam Wójciak.

## Środowisko

Windows 11, Python 3.12.14, Flask 3.1.3, Waitress 3.0.2, SQLite 3.53.1. Testy automatyczne korzystają z osobnych baz i rzeczywistych usług HTTP na loopback. Test restartu uruchamia oddzielny proces aplikacji. Interfejs sprawdzono w przeglądarce pod adresem `http://127.0.0.1:5050`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Wynik: 16 testów automatycznych zakończonych powodzeniem.** Scenariusze: [tests/test_riskr.py](../tests/test_riskr.py). Testy nie korzystają z roboczej bazy aplikacji.

## Wyniki funkcjonalne

| ID | Przypadek i kroki | Oczekiwany wynik | Rzeczywisty wynik | Status |
|---|---|---|---|---|
| T01 | F01: wyłącz gotowość laboratorium, spróbuj uruchomić szkic. | Brak startu, zachowany szkic. | Start odrzucony; status `draft`. | działa |
| T02a | F02: HTTP 500, 100%, 2 s na demo-api; sprawdź także demo-worker. | Błędy tylko w wybranej usłudze. | demo-api: 500, demo-worker: 200; po końcu demo-api: 200. | działa |
| T02b | F02: opóźnienie 400 ms, 2 s. | Wzrost czasu odpowiedzi. | W pomiarach wystąpiła średnia ≥ 400 ms. | działa |
| T02c | F02: przeciążenie 50 żądań/s, 2 s. | Dodatkowy ograniczony ruch HTTP. | Rzeczywiste żądania przekroczyły sondy o ponad 15; liczba pozostała poniżej 150, eksperyment zakończył się. Limit równoległości 10 wynika z puli wykonawczej. | działa |
| T02d | F02: niedostępność 100%, 1 s. | Błędy połączeń, 0% dostępności. | Zapisano błędy połączeń i 0% dostępności. | działa |
| T03 | F03: czas 0/301, intensywność poza zakresem, pusty parametr, ułamek, bool, URL zamiast usługi. | Odrzucenie bez zapisu. | HTTP 400; brak niepoprawnych rekordów. | działa |
| T04 | F04: uruchom krótki eksperyment i zaczekaj. | `completed`, zakłócenie usunięte. | Stan końcowy i powrót usługi do 200 potwierdzone. | działa |
| T05 | F04: uruchom test na 30 s, wyślij stop dwukrotnie; spróbuj edytować aktywny test. | Idempotentny stop i blokada edycji. | `stopped`, usunięcie zakłócenia w mniej niż 5 s; edycja odrzucona. | działa |
| T06 | F04: uruchom dwa szkice z dwóch wątków, ponów start aktywnego testu. | Jeden aktywny test. | Jeden start przyjęty, drugi zablokowany; ponowienie nie utworzyło nowego uruchomienia. | działa |
| T07 | F05: 3 odpowiedzi 2xx, 1 odpowiedź 500, 1 timeout. | 60% dostępności, 1 HTTP 5xx, 1 timeout. | Wynik zgodny; średnia obejmuje wyłącznie odpowiedzi HTTP. | działa |
| T08 | F05: aktywny rekord bez nowych pomiarów; osobno rzeczywista niedostępność. | Odróżnienie braku danych od awarii usługi. | `stale=true`, `latest=null`; w awarii usługi 0% i błędy połączeń. | działa |
| T09 | Uruchom osobny serwer, utwórz i uruchom eksperyment przez HTTP, zaczekaj na pomiary, zakończ proces i uruchom ponownie. | Zachowane dane i usunięty stan aktywności. | Po restarcie `failed` z informacją o przerwaniu; konfiguracja i pomiary zachowane. | działa |
| T10 | Wymuś wyjątek sprzątania, spróbuj rozpocząć drugi test, usuń wymuszenie i ponów sprzątanie. | `cleanup_failed`, blokada startu, możliwość ponowienia. | Wszystkie przejścia potwierdzone. Wyjątek wstrzyknięto kontrolowanie w teście. | działa |
| T11 | Zapisz szkic, odczytaj formularz i powtórz inicjalizację bazy. | Zachowane wartości, brak duplikatów. | Szkic pozostał `draft`; dokładnie dwie usługi. | działa |
| T12 | Odczytaj PRAGMA i usuń środowisko posiadające usługi. | Aktywne FK, usunięcie odrzucone. | `foreign_keys=1`, wyjątek `IntegrityError`. | działa |
| T13 | Wyślij POST bez CSRF oraz z obcym Origin. | HTTP 403. | Oba żądania odrzucone. | działa |
| T14 | Otwórz drugą blokadę pliku aktywnej bazy. | Kontrolowany błąd drugiej instancji. | Czytelny komunikat i zakończenie drugiego uruchomienia. | działa |

Powiązane przypadki są grupowane w metodach, dlatego liczba wierszy z wariantami nie jest równa liczbie testów.

## Weryfikacja w przeglądarce

| Przypadek | Kroki i wynik | Status |
|---|---|---|
| W01 → W02 | Wybór demo-api otworzył formularz z właściwą usługą i etykietami. | działa |
| Zapis | Opóźnienie 500 ms, czas 30 s; po zapisaniu komunikat powodzenia i identyfikator szkicu w adresie. | działa |
| W02 → W03 | Uruchomienie zapisanego szkicu pokazało stan „Trwa”, pomiary i automatyczny stan „Zakończony”. | działa |
| Pomiar opóźnienia | Ostatnia średnia: 633 ms, HTTP 5xx: 0, dostępność: 100%. | działa |
| Zmiana scenariusza | Wybór HTTP 500 zmienił jednostkę na %, wartość na 50, zakres na 1–100. | działa |
| Stop | HTTP 500, 50%, 120 s; przycisk zatrzymania zakończył test jako „Zatrzymany”, wyzerował pozostały czas i umożliwił nowy eksperyment. | działa |

Dowody: [monitorowanie](screenshots/monitorowanie.jpg) i [zatrzymanie](screenshots/zatrzymanie.jpg).

## Wykryte problemy i poprawki

| Problem | Objaw | Poprawka i sprawdzenie |
|---|---|---|
| Katalog tymczasowy | `sqlite3.OperationalError: unable to open database file` w katalogu systemowym środowiska narzędziowego. | Bazy testowe przeniesiono pod `tmp` projektu; testy przeszły. |
| Drugi runner | `PermissionError` podczas odczytu zablokowanego pliku. | Odczyt objęto obsługą błędu i zamknięciem uchwytu; T14 przeszedł. |
| Dostęp do loopback | Sondy nie docierały do lokalnego serwera w ograniczonym wykonaniu. | Testy uruchomiono z dostępem do lokalnych połączeń; dozwolone cele aplikacji pozostały niezmienione. |
| Okno pomiarowe | Kolejna sonda była dopisywana przed zamknięciem poprzedniego okna. | Zamknięcie okna przeniesiono przed następną sondę; ponowiono testy. |

## Niewykonane sprawdzenia

| Obszar | Status | Przyczyna |
|---|---|---|
| Docker Compose i izolacja sieciowa kontenera | niewykonany | Brak Dockera na stanowisku; lokalny test loopback nie potwierdza izolacji kontenerowej. |
| Uruchomienie na dwóch komputerach członków zespołu | niewykonany | Weryfikacja odbyła się na jednym stanowisku Windows. |
| Bezpłatna rozmowa każdego członka zespołu | niewykonany | Nie zweryfikowano kont i odrębnych rozmów obu osób. |
| Wkład na GitHub i aktualizacja LaboChat | niewykonany | Brak skonfigurowanego repozytorium i połączonej przestrzeni projektu. |

## Ocena zgodności

F02–F05 działają w sprawdzonym lokalnym wariancie demonstracyjnym. F01 ogranicza cel do dwóch wbudowanych usług; pełnej izolacji systemowej nie potwierdzono. Cztery tabele i trwałość danych zachowano po zmianie na SQLite. F06–F08 pozostają poza v1.
