RiskR - bezpieczne środowisko do wykrywania słabości systemów informatycznych

Mateusz Zyra - 174650@student.uwm.edu.pl; kierownik zespołu, deweloper
Adam Wójciak - 180648@student.uwm.edu.pl; deweloper

RiskR to aplikacja wykorzystująca założenia Chaos Engineering, której głównym celem jest testowanie odporności, stabilności oraz niezawodności systemów informatycznych poprzez kontrolowane symulowanie awarii i zakłóceń. Projekt zakłada stworzenie bezpiecznego, izolowanego środowiska testowego, w którym użytkownik będzie mógł przeprowadzać eksperymenty polegające na celowym wprowadzaniu błędów do działających aplikacji i usług. Takie podejście pozwoli sprawdzić, jak system zachowuje się w nieprzewidzianych sytuacjach oraz czy potrafi prawidłowo reagować na występujące problemy. Aplikacja będzie umożliwiała przeprowadzanie różnych scenariuszy awaryjnych, takich jak generowanie błędów HTTP 500, zwiększanie opóźnień odpowiedzi serwera, symulowanie przeciążenia czy czasowej niedostępności wybranych usług. Użytkownik będzie mógł konfigurować parametry eksperymentów, w tym rodzaj zakłócenia, jego intensywność oraz czas trwania. Istotnym elementem projektu będzie monitorowanie zachowania testowanego systemu w czasie rzeczywistym. RiskR będzie zbierać informacje i analizować dane dotyczące m.in. czasu odpowiedzi, liczby błędów, dostępności usług oraz skuteczności mechanizmów obsługi awarii. Wyniki eksperymentów zostaną przedstawione w postaci czytelnych wykresów, statystyk i raportów. Aplikacja ma również umożliwiać porównywanie działania systemu przed wystąpieniem zakłócenia, w jego trakcie oraz po zakończeniu eksperymentu. Dzięki temu użytkownik będzie mógł określić wpływ konkretnej awarii na funkcjonowanie aplikacji i zidentyfikować jej potencjalne słabości. Głównym założeniem RiskR jest wykrywanie problemów, zanim wystąpią one w rzeczywistym środowisku produkcyjnym. Projekt łączy zagadnienia inżynierii oprogramowania, testowania, monitorowania systemów oraz analizy niezawodności, oferując narzędzie wspierające tworzenie bardziej odpornych aplikacji.

ZAKRES:

F01	Użytkownik może przeprowadzać eksperymenty na aplikacjach i usługach w bezpiecznym, izolowanym środowisku testowym.	MVP

F02	Użytkownik może wybrać scenariusz awarii: błędy HTTP 500, zwiększone opóźnienia odpowiedzi, przeciążenie lub czasową niedostępność usługi.	MVP

F03	Użytkownik może skonfigurować eksperyment, wskazując testowaną usługę, intensywność zakłócenia oraz czas jego trwania.	MVP

F04	Użytkownik może uruchomić eksperyment oraz zatrzymać go przed upływem zaplanowanego czasu.	MVP

F05	Użytkownik może monitorować w czasie rzeczywistym czas odpowiedzi, liczbę błędów oraz dostępność testowanych usług.	MVP

F06	Użytkownik może przeglądać wyniki zakończonego eksperymentu w postaci wykresów i statystyk, aby ocenić wpływ zakłócenia na działanie systemu.	Rozszerzenie — poza MVP

F07	Użytkownik może porównać działanie systemu przed zakłóceniem, w jego trakcie i po zakończeniu, aby ocenić skuteczność mechanizmów obsługi awarii oraz powrót do prawidłowego działania.	Rozszerzenie — poza MVP

F08	Użytkownik może wygenerować raport podsumowujący konfigurację eksperymentu, zebrane pomiary oraz zaobserwowane problemy.	Rozszerzenie — poza MVP

POZA ZAKRESEM:

1. Porównywanie działania systemu przed awarią, w jej trakcie i po zakończeniu eksperymentu — pierwsza wersja umożliwi monitorowanie bieżących parametrów, ale nie obejmie porównania tych trzech etapów.
2. Generowanie raportów z eksperymentów — pierwsza wersja nie umożliwi tworzenia raportów podsumowujących konfigurację testu, zebrane pomiary i zaobserwowane problemy.

https://github.com/MateuszZyra/InzOpr-Zyra-Wojciak
https://thebill.labochat.com/
