# Audio manager — uzgodnione założenia monitorowania

Ten dokument opisuje docelową logikę wykrywania urządzeń i usług audio. Nie
należy traktować Avahi jako mechanizmu potwierdzającego, że urządzenie nadal
działa — Avahi służy wyłącznie do wykrywania zmian w publikowanych usługach.

## 1. Avahi — tylko zdarzenia `ItemNew` i `ItemRemove`

- [ ] Utrzymać stałe przeglądarki Avahi dla:
  - `_snapclient._tcp`,
  - `_pulse-server._tcp`.
- [ ] Obsługiwać `ItemNew` jako informację, że usługa pojawiła się w sieci.
- [ ] Obsługiwać `ItemRemove` jako informację, że Avahi wycofało usługę.
- [ ] Po `ItemNew` rozwiązać adres usługi, utworzyć odpowiedni monitor i
  obudzić główną pętlę audio-managera.
- [ ] Po `ItemRemove` usunąć tylko tę usługę. Urządzenie pozostawić w rejestrze,
  jeśli nadal publikuje drugi typ usługi.
- [ ] Nie wykonywać okresowego skanowania Avahi, `AllForNow` ani dodatkowego
  czyszczenia cache Avahi jako mechanizmu wykrywania odłączenia.
- [ ] Nie uznawać obecności wpisu z cache Avahi za potwierdzenie dostępności
  urządzenia.

## 2. Dostępność urządzenia — ICMP ping

- [ ] Dla każdego urządzenia prowadzić jeden monitor urządzenia, wspólny dla
  jego usług PulseAudio i Snapclient.
- [ ] Wysyłać pojedynczy ping: `ping -c 1`.
- [ ] Wykonywać próbę co 5 sekund.
- [ ] Po kodzie wyjścia `0` uznać próbę za udaną i wyzerować licznik błędów.
- [ ] Po 3 kolejnych nieudanych próbach uznać urządzenie za niedostępne.
- [ ] Liczbę kolejnych błędów przechowywać jako parametr konstruktora, aby można
  było ustawić np. 3 albo 5 bez zmiany algorytmu.
- [ ] Po ponownym udanym pingowaniu uznać urządzenie za dostępne, zresetować
  monitory usług i ponownie rozpocząć ich sprawdzanie.
- [ ] Gdy urządzenie jest niedostępne, nie wpisywać go do aktywnej listy JSON.
- [ ] Gdy nie ma żadnego adresu IPv4, nie uznawać tego automatycznie za awarię;
  oczekiwać na rozwiązanie adresu przez Avahi lub Snapserver.
- [ ] ICMP jest testem dostępności hosta, a nie potwierdzeniem działania
  PulseAudio ani Snapclienta.

## 3. PulseAudio — osobny monitor usługi

- [ ] Po dostępności hosta sprawdzać osobno usługę PulseAudio przez lekki
  handshake native protocol.
- [ ] Wykonywać handshake co 5 sekund, z timeoutem 1 sekundy.
- [ ] Brak odpowiedzi oznaczać jako `pulse.active: false`, bez usuwania całego
  urządzenia, jeśli host nadal odpowiada na ping.
- [ ] Udany handshake oznaczać jako `pulse.active: true`.
- [ ] Zmianę dostępności PulseAudio przekazywać do konfiguratora MPD i
  restartować MPD po zastosowaniu zmiany topologii.

## 4. Snapclient — osobny monitor usługi

- [ ] Sprawdzać Snapclient wyłącznie przez lokalny Snapserver
  `Server.GetStatus`.
- [ ] Nie traktować samego `ItemNew` Avahi jako potwierdzenia działania
  Snapclienta.
- [ ] Sprawdzać rekord klienta co 2 sekundy, gdy lokalny Snapserver działa.
- [ ] Weryfikować jednocześnie:
  - `connected == true`,
  - obecność pola `lastSeen.sec`,
  - wiek `lastSeen.sec`.
- [ ] Przyjmować klienta jako aktywnego, gdy `lastSeen` jest młodsze niż
  5 sekund.
- [ ] Po braku klienta w `Server.GetStatus`, rozłączeniu albo przeterminowanym
  `lastSeen` ustawić `snapclient.active: false`.
- [ ] `lastSeen` jest czasem ostatniego potwierdzenia klienta; nie używać
  obecności starego rekordu/cache jako dowodu, że klient nadal działa.
- [ ] Gdy Snapserver nie działa, nie wykonywać sprawdzania `Server.GetStatus`;
  ponowić je po uruchomieniu usługi.

## 5. Aktywne urządzenia i cykl życia Snapservera

- [ ] Zapisywać stan urządzeń atomowo w
  `/run/audio-manager/active-clients.json`.
- [ ] W jednym rekordzie urządzenia przechowywać niezależnie stan:
  - hosta/pinga,
  - PulseAudio,
  - Snapclienta.
- [ ] Nie uwzględniać lokalnego Snapclienta w decyzji o uruchomieniu
  Snapservera.
- [ ] Uruchamiać `snapserver.service`, gdy istnieje co najmniej jeden zdalny
  Snapclient wykryty przez Avahi i jego urządzenie odpowiada na ping.
- [ ] Zatrzymywać `snapserver.service`, gdy nie ma żadnego dostępnego zdalnego
  urządzenia Snapclient.
- [ ] Zmianę `ActiveState` Snapservera odbierać z systemd D-Bus; okresowy odczyt
  stanu systemd pozostaje wyłącznie zabezpieczeniem na wypadek utraty sygnału.
- [ ] Po zmianie stanu Snapservera tworzyć lub utrzymywać wymagane sinki PulseAudio
  i FIFO zgodnie z istniejącą logiką.

## 6. Bluetooth, FIFO i routing

- [ ] Trzymać obsługę Bluetooth w osobnej klasie PulseAudio.
- [ ] Nie zmieniać obecnej funkcjonalności dodatkowego USB Bluetooth.
- [ ] Nie tworzyć FIFO dynamicznie przy każdym połączeniu Bluetooth.
- [ ] Przy aktywnym Snapserverze kierować Bluetooth do `snapcast_bt` i FIFO.
- [ ] Przy wyłączonym Snapserverze kierować Bluetooth bezpośrednio do fizycznego
  sinka PulseAudio.
- [ ] `parec` dla Bluetooth i PC uruchamiać tylko przy aktywnym audio, a po
  60 sekundach bezczynności zatrzymywać.

## 7. Konfigurowalność i diagnostyka

- [ ] Trzymać interwały, timeouty i progi błędów w konstruktorach klas
  monitorujących, a nie w kodzie pojedynczego sprawdzenia.
- [ ] Logować osobno wynik pinga, handshake PulseAudio, status Snapclienta,
  wiek `lastSeen`, zmianę stanu JSON oraz decyzję start/stop Snapservera.
- [ ] Zachować możliwość włączenia szczegółowych logów przez
  `AUDIO_MANAGER_LOG_LEVEL=DEBUG`.
- [ ] Dodać testy przejść: `ItemNew`, `ItemRemove`, ping offline/online,
  PulseAudio unavailable/available, Snapclient stale/active oraz start/stop
  Snapservera.
