# Bezpieczna migracja konfiguracji

`scripts/migrate-config.py` uruchamia się na hoście administracyjnym i domyślnie
tylko odczytuje systemy oraz tworzy lokalny raport. Nie przenosi kluczy hosta
SSH, sekretów, konfiguracji sieciowej, danych aplikacji, cache ani runtime.

## Lista plików

Jedynym źródłem ścieżek przekazywanych do SSH jest
`scripts/migration-files.txt`. Każdy wpis ma jawną klasę i jedną ścieżkę:

```text
A /ścieżka/docelowa
```

Skrypt nie dodaje katalogów rekurencyjnie. Jeśli nowy plik ma być analizowany,
dopisz jeden konkretny wiersz do manifestu i przypisz mu klasę. Wpis bez końcowego
`/` oznacza pojedynczy plik. Wpis zakończony `/` oznacza rekurencyjną zawartość
katalogu; każdy znaleziony plik pojawi się osobno w raporcie i planie. Skrypt nie
zmienia klasy na podstawie nazwy ani lokalizacji pliku. Pliki klas `B`, `C` i
`D` są tylko raportowane lub wymagają decyzji ręcznej. W logu pojawi się każdy
wpis manifestu przed wysłaniem go przez SSH. Jeśli wpis wskazuje na dowiązanie
symboliczne, skrypt rozwiązuje jego cel i dodaje rzeczywisty plik do
inwentaryzacji oraz planu; samo dowiązanie nie jest kopiowane jako zawartość.

## Źródło read-only

Skrypt wykonuje na źródle wyłącznie polecenie `tar -T -`, którego wynik jest
przesyłany do hosta administracyjnego przez SSH. Nie używa `sudo`, `su`, `scp`,
`rsync`, instalacji pakietów, restartów ani poleceń zapisujących. Konto SSH może
być zwykłym kontem administracyjnym, zgodnie z lokalnym modelem zaufania.

Opcjonalny przełącznik `--source-read-only-verified` pozostaje akceptowany dla
zgodności, ale nie jest wymagany.

## Tryby i użycie

`--inventory`/`--report` tworzą snapshot, `--plan` tworzy plan, `--diff`
przygotowuje raport, `--dry-run` symuluje plan, a `--apply` wymaga zarówno
`--plan-file`, jak i `--yes`. Plan dopuszcza wyłącznie kandydatów klasy A;
plik istniejący na celu jest najpierw kopiowany do backupu na hoście. Skrypt
nie restartuje usług i nie wykonuje globalnego rollbacku.

Do testów użyj `--source-root` i `--target-root`. Produkcyjnie podaj oba hosty:

```bash
scripts/migrate-config.py --plan \
  --source-host old-pi --source-user root \
  --target-host new-pi --target-user admin
```

Raporty są w `reports/config-migration/YYYY-MM-DD_HH-MM-SS/`. Inwentaryzacja
obu urządzeń i zapis zatwierdzonych plików odbywają się przez SSH. Przed
`--apply` należy przeglądać `comparison.tsv`, `migration-plan.tsv` i diffy oraz
ponownie zweryfikować, że cel nie zmienił się od czasu inwentaryzacji.

## Yocto

Warstwa dostarcza konfigurację przez `SRC_URI`/`do_install`, między innymi dla
MPD, PulseAudio, Snapcast, MiniDLNA, Samby, Transmission, WPA/networkd, DHCP,
Apache, vsftpd oraz jednostek systemd. Takie pliki należy odtwarzać w
recepturach lub `.bbappend`, zamiast kopiować całe `/etc`. Adresy sieciowe,
tożsamość SSH, sekrety i ustawienia konkretnego wyjścia audio są zależne od
urządzenia. `/var/lib`, `/var/cache` i `/var/log` są danymi/runtime i wymagają
osobnej migracji.

## Odzyskiwanie

Backup istniejącego pliku jest tworzony lokalnie przed zamianą. Operator powinien
przywrócić konkretny plik po weryfikacji backupu, a następnie ręcznie sprawdzić
konfigurację usługi. Dla wpisu katalogowego zakończonego `/` backup całego
katalogu jest tworzony tylko raz; `apply-results.tsv` wskazuje ten sam
`backup_scope` przy każdym zmigrowanym pliku z tego katalogu. Klucze hosta SSH
i sieć nie są kandydatami do automatycznej migracji.

Przed `--apply` skrypt przez SSH sprawdza usługi `mpd`, `snapserver`,
`snapclient`, `minidlna`, `pulseaudio`, `transmission-daemon`, `smbd` i
`jellyfin`. Zatrzymuje tylko te, które są aktywne, wykonuje migrację, a potem
uruchamia ponownie tylko wcześniej aktywne usługi. SSH i usługi sieciowe nie są
zatrzymywane.
