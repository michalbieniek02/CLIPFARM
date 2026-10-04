# CLIPFARM

![CLIPFARM](assets/clipfarm-lockup.png)

Lokalna aplikacja desktopowa Windows do tworzenia klipów z filmów z mową.
Interfejs: PySide6 / QML (Qt Quick), ciemne studio z wbudowanym podglądem wideo.

## Uruchomienie na tym komputerze

Kliknij dwukrotnie **CLIPFARM.exe**. Launcher otwiera aplikację bez konsoli.
Alternatywy: **CLIPFARM.vbs** albo `powershell -ExecutionPolicy Bypass -File Start-CLIPFARM.ps1`.
Folder `runtime` musi pozostać obok launchera. To instalacja lokalna, a nie przenośny pojedynczy EXE.

## Instalacja ze świeżego repozytorium

Na Windows zainstaluj **Python 3.11+ 64-bit** oraz **Codex CLI albo Claude Code**.
Zalecana i przetestowana wersja to **Python 3.12**; dostępność bibliotek Whisper/CUDA
na nowszych wydaniach Pythona zależy od przypiętych zależności. Sklonuj repozytorium i otwórz PowerShell
w jego folderze, na przykład:

```powershell
git clone <adres-repozytorium> CLIPFARM
cd CLIPFARM
powershell -ExecutionPolicy Bypass -File .\Install-CLIPFARM.ps1
codex login                 # jeśli używasz Codex CLI
# albo:
npm install -g @anthropic-ai/claude-code
claude                       # dokończ logowanie w terminalu
```

Instalator tworzy lokalne środowisko `runtime` i pobiera biblioteki. Potem uruchom:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-CLIPFARM.ps1
```

Przy kolejnych uruchomieniach wystarczy dwuklik `CLIPFARM.exe` albo `CLIPFARM.vbs`.
Nie przenoś samego pliku EXE — musi mieć obok cały folder aplikacji, w tym `qml`,
pliki Pythona, `assets` i `runtime`. Modele pobierają się do `models` przy pierwszym użyciu.
Jeśli PowerShell zgłosi brak Pythona, zainstaluj Python 3.12 z opcją „Add python.exe to PATH”,
zamknij i otwórz PowerShell ponownie, a następnie uruchom instalator jeszcze raz.

CLIPFARM wykrywa dostawcę automatycznie: najpierw sprawdza Codex CLI, a jeśli nie może
z niego skorzystać, przechodzi do Claude Code. Na komputerze z oboma narzędziami Codex
ma pierwszeństwo. Użytkownik Claude nie musi instalować Codexa — wystarczy `claude`,
jednorazowe logowanie w terminalu i później zwykły start aplikacji.

1. Przeciągnij film z Eksploratora Windows na okno albo kliknij „Wybierz film”.
2. Domyślne ustawienia: automatyczna liczba propozycji zależna od długości filmu,
   długość 20–30 s (clip może mieć 15–40 s), pionowy obraz 9:16,
   cały film z czarnymi pasami i napisy w obrazie.
3. Kliknij „Znajdź fragmenty”. Whisper robi transkrypcję lokalnie, jeśli nie ma gotowej;
   Codex CLI wysyła tekst do GPT 6.1 Sol i zwraca tytuły, czasy i uzasadnienia.
4. Kliknij „Edytuj”, popraw czasy w sekundach i zatwierdź przyciskiem „Zapisz”.
   „Podgląd” renderuje fragment z bieżącymi ustawieniami i otwiera go we wbudowanym odtwarzaczu.
   Niepotrzebne propozycje możesz usunąć przyciskiem „Usuń”.
5. Zaznacz klipy i kliknij „Eksportuj klipy”. Wybierz folder docelowy.

## Pobieranie filmów z Kicka, Twitcha, YouTube i X

W zakładce „Pobierz VOD” wklej link do zakończonego, dostępnego nagrania.
Wybierz Kick, Twitch, YouTube lub X; „Auto” rozpoznaje serwis z linku.
Obsługiwane są VOD-y i klipy Twitcha, filmy i Shortsy YouTube oraz wpisy X z jednym filmem.
Puste czasy oznaczają cały materiał; opcjonalnie podaj początek i koniec jako HH:MM:SS.
Przycisk „Pobierz / wznów” pyta o folder. Wybierz jakość:

| Tryb | Obraz / dźwięk | Orientacyjnie 8 godzin |
| --- | --- | --- |
| Oryginał | Najlepsze dostępne źródło, bez ponownego kodowania | Zależy od źródła |
| 720p60 | H.264 4 Mb/s / AAC 128 kb/s | 14,9 GB |
| 720p30 | H.264 2,5 Mb/s / AAC 128 kb/s | 9,5 GB |
| 480p60 | H.264 2 Mb/s / AAC 96 kb/s | 7,5 GB |
| 480p30 | H.264 1,2 Mb/s / AAC 96 kb/s | 4,7 GB |

Kompresja zachowuje proporcje i nie powiększa niższej rozdzielczości źródła.
Domyślnie korzysta z NVIDIA NVENC;
przy błędzie sieci odświeża adres nagrania, a przy niedostępnym NVENC przechodzi na CPU.
Postęp odświeża się w trakcie zapisu, razem z szacowanym czasem do końca.

Po przerwaniu wpisz ten sam link, zakres, jakość i wybierz ten sam folder. Ukończone części
w ukrytym folderze `.vod-*` są weryfikowane i używane ponownie; bieżąca część jest powtarzana.
Podczas łączenia skompresowanych części potrzeba około dwukrotności rozmiaru końcowego pliku.
Po ukończeniu części są usuwane, a końcowy MP4 automatycznie staje się źródłem do cięcia.
Oryginał używa wznawiania yt-dlp i zachowuje kodeki, rozdzielczość i FPS źródła.
Osobne ścieżki obrazu i dźwięku są łączone do MKV bez kompresji; pojedynczy strumień
zachowuje swój format. Zakres oryginału najpierw pobiera cały film, potem wycina fragment
bez ponownego kodowania, więc granice mogą trafić na sąsiednie klatki kluczowe.
YouTube używa dostępnego na komputerze Node.js do obsługi odtwarzacza; prywatne nagrania,
filmy wymagające logowania i trwające transmisje nie są obsługiwane przez ten formularz.
Pobieranie działa lokalnie; nie potrzebuje limitów Codexa ani wysyłania plików do Vercela.
Test `tests/vod_review.py` sprawdza lokalny HLS, wszystkie jakości, oryginał, osobny obraz
i dźwięk oraz przerwanie i wznowienie.
Nowe identyfikatory Kicka korzystają z adresu `web.kick.com/api/v1/stream/.../playback`;
starsze nagrania nadal mogą używać poprzedniego API. Poprawka jest lokalna dla CLIPFARM
i nie modyfikuje zainstalowanego yt-dlp. Test `tests/kick_api_review.py` sprawdza oba warianty.

Obok trybu AI dostępny jest tryb „Film · minuty”. Dzieli cały materiał na kolejne
60-sekundowe części (ostatnia może być krótsza), bez wybierania momentów przez model.
Przed napisami można włączyć dodatki eksportu: lekki kolor, tempo 1,1× i odbicie lustrzane.
Ustawienia zapisują się razem z projektem. Napisy mają domyślnie rozmiar 84 przy szerokości
1080 px (o 20% większy); bardzo długie frazy dopasowują się do szerokości kadru.
Przy tempie 1,1× czasy słów w napisach w obrazie i plikach SRT/ASS są skracane
razem z obrazem i dźwiękiem. Zapisana transkrypcja zachowuje czasy filmu źródłowego.

Każdy eksport zawiera MP4, osobny SRT i manifest `clips.json`.
Projekty można zapisać do JSON i wczytać ponownie. Film źródłowy musi nadal istnieć.
Transkrypcje są zapamiętywane w `projects` z identyfikacją ścieżki, rozmiaru i daty pliku.
Modele Whisper są w `models`. Gotowa transkrypcja jest używana ponownie przy wyborze klipów.

## Kadrowanie i ponowne użycie transkrypcji

„Cały obraz · czarne pasy” dopasowuje cały film do 1080×1920 bez obcinania boków.
Dla poziomego filmu pasy pojawiają się u góry i u dołu. „Wypełnij · środek” przycina obraz,
a „Podążaj za twarzą” używa lokalnego YuNet / OpenCV do przesuwania pionowego kadru.
Przy wielu osobach wybierana jest duża twarz z preferencją zachowania ciągłości.
Gdy w całym klipie nie wykryto twarzy, eksport zachowuje cały obraz z pasami.
Po chwilowym zniknięciu twarzy kadr pozostaje w ostatnim położeniu.
Podgląd i eksport używają tego samego trybu. Oryginalny format zachowuje proporcje filmu.

Obok filmu dostępne są trzy działania:

- „Transkrybuj”: tworzy samą lokalną transkrypcję, bez wywoływania GPT.
- „Wczytaj”: dołącza SRT, VTT lub JSON z listą `segments` (start, end, text).
- „Pobierz”: zapisuje pełną transkrypcję filmu do SRT albo JSON.

Jeżeli `film.mp4` ma obok `film.srt`, `film.vtt`, `film.transcript.json` lub `film.json`,
aplikacja może wczytać je automatycznie. Pierwszeństwo ma prawidłowa lokalna pamięć transkrypcji
dla tego samego pliku. Można zastąpić ją ręcznie przyciskiem „Wczytaj”.
Wczytana transkrypcja jest zapamiętywana. Ponowny wybór klipów używa gotowego tekstu,
a zmiana kadrowania wymaga tylko ponownego eksportu; nie wymaga ani Whispera, ani Codexa.
Ponowny wybór innych momentów wywołuje Codex, ale nie powtarza transkrypcji.

## Sprzęt i konto

Przetestowano na NVIDIA RTX 4070 12 GB: Whisper small / CUDA float16 oraz H.264 NVENC.
Biblioteki NVIDIA zostały zainstalowane wewnątrz środowiska aplikacji, bez zmiany sterowników.
Przy niedostępnej akceleracji tryb automatyczny próbuje użyć CPU i informuje o tym w dzienniku.
Pierwsze użycie innego modelu Whisper może pobrać go z Hugging Face.

Aplikacja automatycznie wykrywa zalogowane narzędzie AI. Jeśli istnieje Codex CLI,
używa jego konta i GPT 6.1 Sol. Jeśli Codex nie jest dostępny, a istnieje Claude Code,
używa jego aktywnej sesji i domyślnego modelu Claude. Nie ma przełącznika dostawcy
ani klucza API. Przy problemie z logowaniem uruchom `codex login` albo `claude`.
Tokeny logowania zostają w ich własnych aplikacjach; CLIPFARM ich nie kopiuje.

Film oraz dźwięk pozostają na komputerze. Do modelu trafia transkrypcja i opis wyboru.
W długich filmach analizowane są wszystkie części transkrypcji; podział ma nakładkę,
aby nie gubić fragmentów na granicach. Wyniki są sortowane według oceny modelu,
sprawdzane względem czasu filmu i wybierane bez nakładania się.

Wybór korzysta teraz z logiki zaadaptowanej z AI-Youtube-Shorts-Generator:
ocenia mocny początek, emocje, wyrazistą opinię, odkrycie, konflikt, cytowalność,
puentę i praktyczną wartość. Model uwzględnia rodzaj materiału oraz gęstość informacji.
Tworzy do dwukrotności żądanej liczby kandydatów (maks. 40, z limitem wynikającym
z długości materiału), a aplikacja wybiera najlepsze różne fragmenty. Odrzuca
nakładające się momenty i powtarzające się zdania otwierające.
Pole `hook_sentence` zapisuje cytat otwierający w projekcie i manifeście eksportu;
cytat nieobecny w początkowej transkrypcji fragmentu jest usuwany. Ocena 0–100
jest opinią modelu, nie prognozą rzeczywistych statystyk. Długość wybrana przez
użytkownika nadal ma pierwszeństwo. Licencja i autor: THIRD_PARTY_NOTICES.md.

## Granice pierwszej wersji

- Wybór momentów odbywa się na podstawie mowy. Lokalne wykrywanie twarzy służy kadrowaniu.
- Wykrywanie twarzy nie ustala, kto mówi; przy wielu osobach sprawdź wynik podglądu.
- Napisy w klipach to krótkie frazy do 4 słów, wielkimi literami, czcionką Anton.
  W trybie całego obrazu pojawiają się na dolnym czarnym pasie; jeśli pas jest za mały,
  aplikacja rezerwuje miejsce pod obrazem. Tryby wypełnienia i twarzy mają napisy w dolnej części kadru.
  Słowa dochodzą kolejno w grupie do 4 słów, a aktualnie wypowiadane słowo jest żółte.
  Nowe transkrypcje zapisują czasy słów w JSON. Starsze transkrypcje i SRT są dopasowywane
  do dźwięku lokalnie przez Whisper / CTranslate2, bez zmiany tekstu i bez wywołania Codexa.
  Dopasowanie obejmuje segmenty wybranych klipów; czasy zapisują się do ponownego użycia.
  Synchronizacja jest automatyczna, jej dokładność zależy od dźwięku i poprawności transkrypcji.
  SRT eksportu również pokazuje słowa kolejno. Przy napisach w obrazie ma końcówkę
  `.captions.srt`, żeby odtwarzacz nie nakładał drugiego zestawu napisów automatycznie.
  Podgląd stosuje te same ustawienia napisów co eksport. Pełna pobierana transkrypcja pozostaje zachowana.
- „Obejrzyj fragment” tworzy lokalny plik podglądu i otwiera systemowy odtwarzacz.
- Przerwanie transkrypcji następuje po bieżącym segmencie; ładowanie modelu może potrwać.
- Model może zwrócić mniej klipów niż zamówiono, gdy materiał nie spełnia kryteriów.

## Ponowna instalacja / rozwój

Python 3.12 zalecany. Uruchom `Install-CLIPFARM.ps1`, a następnie zaloguj Codex CLI.
Zależności są przypięte w `requirements.txt`, w tym PyAV 16.1 zgodne z faster-whisper 1.2.1.
Kod: `app.py` (obsługa okna), `ui_layout.py` (interfejs), `ui_media.py` (lokalne miniatury),
`engine.py` (pipeline), `framing.py` (kadrowanie), `transcripts.py` (napisy i pamięć), `Launcher.cs` (launcher).

Interfejs ma jasny wygląd inspirowany aplikacjami Apple. Kliknięcie miniatury klipu otwiera
podgląd w systemowym odtwarzaczu. Dziennik techniczny jest pod przyciskiem „Szczegóły”.
Skróty: Ctrl+O — wybór filmu, Ctrl+S — zapis projektu, Escape — przerwanie zadania.

Weryfikacja: `check_pipeline.py` sprawdza eksport NVENC, audio, proporcje i napisy
na wygenerowanym materiale. `check_voice.ps1` generuje głos testowy przy użyciu Windows.
`check_e2e.py` uruchamia pełny przepływ; używa sieci, pobiera Whisper i zużywa limit konta Codex.
Zapisany wynik testu jest w `checks/e2e/result.json`.
`checks/framing_review.py` sprawdza pasy, ruch twarzy i brak twarzy na lokalnym materiale;
`checks/transcript_review.py` sprawdza zapis i import, cache oraz ponowny wybór z zabronionym
uruchomieniem Whispera. Te testy nie wywołują Codexa.

Raport selekcji AI jest oparty wyłącznie na transkrypcji. Dla każdego wybranego klipu zapisuje
score 1–10, dokładny hook i opcjonalne cięcie startu, dwie alternatywy hooka, strukturę
setup → kulminacja → zakończenie, możliwość pętli, frazy do napisów, plan montażu, trzy tytuły,
opis z hashtagami oraz ryzyka. Reakcje twarzy, czat, muzyka i wydarzenia widoczne tylko na obrazie
mają wartość „brak”, jeśli transkrypcja ich nie potwierdza. Dane są zapisane w projekcie i `clips.json`.

Model twarzy: [OpenCV YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet).
Model jest dołączony w `assets/face/yunet.onnx`, z licencją MIT w `assets/face/LICENSE`.

Źródła integracji: [OpenAI Docs — GPT 6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Codex CLI](https://learn.chatgpt.com/docs/developer-commands?surface=cli),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Uruchomienie i architektura Qt Quick

Po aktualizacji istniejącej instalacji doinstaluj wymagania:

```powershell
cd S:\CLIPFARM
.\runtime\Scripts\python.exe -m pip install -r requirements.txt
.\runtime\Scripts\python.exe app.py
```

Na świeżym komputerze z Pythonem 3.11+:

```powershell
python -m venv runtime
.\runtime\Scripts\python.exe -m pip install -r requirements.txt
.\runtime\Scripts\python.exe app.py
```

`app.py` uruchamia `qt_app.py`, który wystawia `Backend` do QML.
`backend.py` zawiera właściwości/sygnały/sloty oraz model klipów; każdy etap przetwarzania
(probe, miniatury, Whisper, wybór, render, odczyt/zapis projektu) wykonuje `Job(QThread)`.
Wyniki, błędy i postęp wracają do głównego wątku przez sygnały Qt.
`qml/Main.qml` składa ekran z osobnych komponentów, a `qml/Theme.qml` jest singletonem
kolorów, odstępów, narożników i czasów animacji. Moduły silnika mediów pozostają w Pythonie.
Stare `ui_layout.py` i `brand.py` są nieużywanymi pozostałościami UI Tk i nie są importowane przy starcie.

Skróty: Ctrl+O — otwórz projekt, Ctrl+S — zapisz projekt, Escape — zamknij panel
lub przerwij zadanie. Zamykanie okna podczas pracy czeka na bezpieczne zatrzymanie wątku.
Błędy i pełny log znajdziesz w wysuwanym panelu „Szczegóły”; tekst można skopiować.
Animacje respektują ustawienie animacji Windows. Do ręcznego sprawdzenia:
`$env:CLIPFARM_REDUCED_MOTION='1'` przed uruchomieniem.

Test integracyjny: `.\runtime\Scripts\python.exe tests\qt_review.py`.
Wymaga lokalnych materiałów `checks/synthetic.mp4` i `checks/e2e/narrated.mp4`
oraz `checks/e2e/transcript.json` (nie są dostarczane ze świeżym klonem).
Test używa kontrolowanego wyniku AI, natomiast eksport FFmpeg i dekodowanie QtMultimedia są rzeczywiste.

## Pobieranie i aktualizacje

Pobieranie VOD pokazuje zapisane megabajty i postęp podczas zapisu, mniej więcej co 250 ms.
ETA pojawia się po zmierzeniu rzeczywistego tempa pobierania i kompresji; oblicza pozostały
materiał z prędkości z ostatnich 30 sekund. Wznawiane części nie zawyżają prędkości.
Brak postępu przez 90 sekund powoduje zatrzymanie FFmpeg i odświeżenie adresu nagrania.
Każda część ma maksymalnie trzy próby. Błąd sieci zachowuje wybrany NVENC; na CPU
przechodzimy przy błędzie inicjalizacji kodera. Łączenie MP4 jest osobnym etapem.
Oryginał pokazuje otrzymane bajty i ETA yt-dlp; przy osobnych ścieżkach ETA dotyczy bieżącej ścieżki.

Workflow [Windows release](https://github.com/michalbieniek02/CLIPFARM/actions/workflows/release.yml)
po każdym pushu do `main` uruchamia testy na Windows i publikuje gotową paczkę w GitHub Releases.
Nieudany build nie publikuje aktualizacji. Aplikacja sprawdza nowe wydanie po starcie
i co pięć minut w tle; nie pobiera samego repozytorium co pięć minut.

Ikona strzałki w górę w nagłówku oznacza nową wersję. Kliknięcie zapisuje otwarty projekt,
pobiera ZIP z postępem liczonym w bajtach, sprawdza SHA-256 paczki i każdego pliku,
zamyka aplikację, instaluje i uruchamia ją ponownie z zapisanym projektem.
Instalację można rozpocząć po zakończeniu pracy nad filmem. Aktualizator wymienia tylko
pliki aplikacji; `projects`, `exports`, `models`, `runtime`, `.git`, `.env` i `.local` pozostają.
Zmienione wymagania instaluje przed restartem. Pliki poprzedniej wersji trafiają do kopii
w `.local/updates/<wersja>/backup`; przy błędzie następuje wycofanie zmian.
Log instalacji: `.local/updates/<wersja>/install.log`.

Testy aktualizacji: `tests/update_review.py`, `tests/update_restart_review.py`, `tests/update_ui_review.py`.
Pierwsze dwa działają bez sieci; ostatni klika rzeczywisty interfejs Qt i sprawdza zapis projektu,
animację postępu oraz cykliczne sprawdzanie wersji. Wymaga `checks/synthetic.mp4`.
