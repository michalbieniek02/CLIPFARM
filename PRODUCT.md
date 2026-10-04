# CLIPFARM

Desktopowa aplikacja Windows dla właściciela komputera do tworzenia krótkich klipów z lokalnych filmów.
Potwierdzono: wybór fragmentów przez GPT 6.1 Sol na zalogowanym koncie Codex,
lokalne przetwarzanie filmu, domyślnie pionowe 9:16 i długość 30–60 sekund.
Komputer ma NVIDIA RTX 4070 12 GB.

Pierwsza wersja: import filmu, transkrypcja Whisper, propozycje fragmentów,
korekta czasów, podgląd fragmentu w systemowym odtwarzaczu, eksport MP4 i napisów,
zapis i otwarcie projektu. Wybór kadrowania: cały obraz z czarnymi pasami (domyślnie),
centralne przycięcie lub lokalne podążanie za wykrytą twarzą przez OpenCV / YuNet.
Wybór momentów nadal opiera się na transkrypcji.

Transkrypcję można utworzyć osobno, pobrać do SRT / JSON i dołączyć do filmu (SRT / VTT / JSON).
Gotowe transkrypcje i napisy leżące obok filmu są wczytywane i zapamiętywane.
Zmiana kadrowania nie wymaga ponownej transkrypcji ani wyboru momentów przez Codex.
Liczba klipów nie jest pytaniem dla użytkownika: aplikacja dobiera ją automatycznie
do długości filmu i zakresu 30–60 sekund.

Napisy w klipach: frazy do 4 słów, czcionka Anton. Tryb całego obrazu umieszcza tekst
na czarnym pasie pod filmem. Nowe transkrypcje mają czasy słów; starsze można użyć
ponownie z lokalnym dopasowaniem słów do dźwięku. Słowa dochodzą kolejno do grupy,
aktualne słowo jest żółte, a wcześniej wypowiedziane zostają białe. Dopasowanie jest
zapamiętywane i nie wywołuje Codexa ani nie tworzy tekstu transkrypcji od nowa.

## Platform
Windows desktop, Python 3.11+ / PySide6 + QML (Qt Quick).
Logika mediów pozostaje w Pythonie; interfejs komunikuje się z backendem QObject.
