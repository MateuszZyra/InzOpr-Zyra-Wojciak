# RiskR — materiał do LaboChat

Materiał do przeniesienia do przestrzeni projektu. Nie jest potwierdzeniem utworzenia zadań w LaboChat.

Przykładowi członkowie: Mateusz i Kamil. Terminy i osoby można zmienić. Pełny opis rezultatów i zależności znajduje się w [mapie v1](roadmap-v1.md#6-mapa-prac-pierwszej-iteracji).

## Opis przestrzeni projektu

RiskR umożliwia kontrolowane testowanie odporności usług w izolowanym laboratorium. MVP obejmuje środowisko testowe, cztery scenariusze awarii, konfigurację parametrów, uruchamianie i zatrzymywanie testów oraz bieżące monitorowanie. W kolejnej iteracji planowane są wykresy wyników, porównania faz i raporty.

Link do mapy na GitHub: DO UZUPEŁNIENIA po publikacji `docs/roadmap-v1.md`.

## Zadania do dodania

Początkowy status wszystkich pozycji: „Do weryfikacji / zaplanowania”. Dokumentacja została przygotowana lokalnie, ale zespół powinien zweryfikować ją przed oznaczeniem etapów planistycznych jako wykonane.

| ID | Tytuł | Osoba | Termin | Zależności | Kryterium zakończenia |
|---|---|---|---|---|---|
| Z01 | Potwierdzić cel i zakres MVP | Mateusz; przegląd Kamil | 25.11.2026 | Lab. 01 | Zaakceptowany cel i F01–F05. |
| Z02 | Zweryfikować widoki i nawigację | Mateusz | 26.11.2026 | Z01 | Trzy szkice i kompletna ścieżka użytkownika. |
| Z03 | Zweryfikować model bazy | Kamil | 27.11.2026 | Z02 | Pola, PK/FK, relacje i ograniczenia. |
| Z04 | Zweryfikować opisy funkcji | Kamil; przegląd Mateusz | 28.11.2026 | Z02, Z03 | Każda funkcja ma warunek odbioru i opis błędu. |
| Z05 | Sprawdzić spójność mapy | Mateusz i Kamil | 29.11.2026 | Z01–Z04 | Zgodność funkcji, widoków i danych. |
| Z06 | Przygotować laboratorium i bazę | Kamil | 30.11.2026 | Z03–Z05 | Izolowane usługi, migracje i kontrola gotowości. |
| Z07 | Wykonać interfejs | Mateusz | 30.11.2026 | Z02–Z05 | Działające W01–W03 i walidacja. |
| Z08 | Wykonać mechanizm eksperymentów | Kamil | 01.12.2026 | Z06 | Cztery scenariusze, start, stop i sprzątanie. |
| Z09 | Zintegrować pomiary | Mateusz; wsparcie Kamil | 01.12.2026 | Z07, Z08 | Dane odświeżane w W03 co 5 s. |
| Z10 | Sprawdzić v1 | Mateusz i Kamil | 02.12.2026 | Z08, Z09 | Zapisane wyniki T01–T10 i usterki. |
| Z11 | Opublikować dokumentację i oddać linki | Mateusz i Kamil | 02.12.2026 | Z05; opcjonalnie Z10 | Mapa na GitHub, przestrzeń LaboChat, własny commit każdej osoby. |

## Czynności przed oddaniem

1. Zmienić przykładowe osoby i terminy na rzeczywiste.
2. Uzgodnić repozytorium GitHub i opublikować pliki w jego właściwym katalogu.
3. Każda osoba samodzielnie sprawdza i zatwierdza własną merytoryczną część dokumentacji ze swojego konta.
4. Utworzyć lub otworzyć przestrzeń RiskR w LaboChat i przenieść do niej powyższe zadania.
5. W zadaniach dodać adres mapy na GitHub; link przestrzeni LaboChat dopisać do README i mapy.
6. Przekazać prowadzącemu oba rzeczywiste adresy.
