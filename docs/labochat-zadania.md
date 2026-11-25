# RiskR — zadania projektu

**Zespół:** Mateusz Zyra i Adam Wójciak.

## Opis projektu

RiskR umożliwia kontrolowane testowanie odporności usług w izolowanym laboratorium. MVP obejmuje środowisko testowe, cztery scenariusze awarii, konfigurację parametrów, uruchamianie i zatrzymywanie testów oraz bieżące monitorowanie. W kolejnej iteracji planowane są wykresy wyników, porównania faz i raporty.

Dokumentacja: [mapa pierwszej wersji projektu](roadmap-v1.md).

## Podział zadań

| ID | Tytuł | Osoba | Zależności | Kryterium zakończenia |
|---|---|---|---|---|
| Z01 | Potwierdzić cel i zakres MVP | Mateusz Zyra; przegląd Adam Wójciak | Lab. 01 | Zaakceptowany cel i F01–F05. |
| Z02 | Zweryfikować widoki i nawigację | Mateusz Zyra | Z01 | Trzy szkice i kompletna ścieżka użytkownika. |
| Z03 | Zweryfikować model bazy | Adam Wójciak | Z02 | Pola, PK/FK, relacje i ograniczenia. |
| Z04 | Zweryfikować opisy funkcji | Adam Wójciak; przegląd Mateusz Zyra | Z02, Z03 | Każda funkcja ma warunek odbioru i opis błędu. |
| Z05 | Sprawdzić spójność mapy | Mateusz Zyra i Adam Wójciak | Z01–Z04 | Zgodność funkcji, widoków i danych. |
| Z06 | Przygotować laboratorium i bazę | Adam Wójciak | Z03–Z05 | Izolowane usługi, migracje i kontrola gotowości. |
| Z07 | Wykonać interfejs | Mateusz Zyra | Z02–Z05 | Działające W01–W03 i walidacja. |
| Z08 | Wykonać mechanizm eksperymentów | Adam Wójciak | Z06 | Cztery scenariusze, start, stop i sprzątanie. |
| Z09 | Zintegrować pomiary | Mateusz Zyra; wsparcie Adam Wójciak | Z07, Z08 | Dane odświeżane w W03 co 5 s. |
| Z10 | Sprawdzić v1 | Mateusz Zyra i Adam Wójciak | Z08, Z09 | Zapisane wyniki T01–T10 i usterki. |
| Z11 | Opublikować dokumentację i oddać linki | Mateusz Zyra i Adam Wójciak | Z05; opcjonalnie Z10 | Mapa na GitHub, przestrzeń LaboChat, własny commit każdej osoby. |

## Stan realizacji po laboratorium 03

| Zadania | Stan | Rezultat |
|---|---|---|
| Z01–Z05 | wykonane lokalnie | Mapa, widoki, model danych i opisy funkcji. |
| Z06 | częściowo wykonane | Laboratorium lokalne i SQLite działają; wariant Docker wymaga uruchomienia. |
| Z07–Z09 | wykonane lokalnie | Widoki, eksperymenty i monitorowanie. |
| Z10 | wykonane dla trybu lokalnego | 16 testów automatycznych oraz sprawdzenie w przeglądarce. |
| Z11 | niewykonane | Publikacja GitHub i aktualizacja LaboChat nie zostały wykonane. |

Szczegóły: [technologie](technologie.md), [prompty](prompty-v1.md) i [wyniki testów](testy-v1.md).
