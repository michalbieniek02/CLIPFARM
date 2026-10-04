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

Napisy w klipach: frazy do 4 słów, domyślnie czcionka Anton. Użytkownik wybiera spośród
20 lokalnie dołączonych czcionek, rozmiar 24–160 px dla szerokości 1080 px oraz położenie
tekstu przez przeciąganie, strzałki lub pola procentowe. Podgląd i eksport używają
wybranej czcionki. Automatyczne położenie w trybie całego obrazu umieszcza tekst
na czarnym pasie pod filmem. Nowe transkrypcje mają czasy słów; starsze można użyć
ponownie z lokalnym dopasowaniem słów do dźwięku. Słowa dochodzą kolejno do grupy,
aktualne słowo jest żółte, a wcześniej wypowiedziane zostają białe. Dopasowanie jest
zapamiętywane i nie wywołuje Codexa ani nie tworzy tekstu transkrypcji od nowa.

Stały podgląd ustawień w prawym panelu o szerokości 248 px pokazuje lokalne,
przykładowe zdjęcie osoby wewnątrz ramki iPhone odtworzonej z dostarczonej referencji
w natywnej geometrii QML, z zaokrągloną maską, wyspą i dolnym wskaźnikiem.
Ekran ma proporcje 9:19,5. Pionowe 9:16 i oryginalne proporcje pozostają dostępne;
format „Telefon 9:19,5” odpowiada całemu ekranowi podglądu i eksportuje 1080×2340.
„Wypełnij ekran” wybiera ten format, centralne przycięcie, przybliżenie 1× i środek
źródła. Obraz wypełnia ekran przez przycięcie, z zachowaniem proporcji. Jest to
dopasowanie do telefonu w podglądzie; wygląd na innych urządzeniach i platformach
zależy od ich ekranu i odtwarzacza. Podgląd pokazuje
format, kadrowanie, kolor, odbicie i napisy jeszcze przed eksportem. Animacja napisów
uwzględnia tempo, a opis pod kadrem pokazuje wynikową długość klipu i ustawienie
transkrypcji. Podgląd działa także w zakładce pobierania VOD, przy oknie 1360×900
i minimum 1100×780. W trybach całego obrazu i centralnego przycięcia użytkownik
ustawia przybliżenie 1–4× i przesuwa punkt źródła. Cały obraz dopuszcza czarne
dopełnienie; przycięcie ogranicza przesuwanie do krawędzi źródła, aby wypełnienie
pozostało pełne. Napisy można ustawiać na całym wybranym kadrze, także 1080×2340.
Położenie napisów i punkt źródła są zapisane jako współrzędne 0–1. Reset przywraca
automatyczne położenie napisów, przybliżenie 1× i środkowy punkt źródła.
Podgląd i eksport korzystają ze wspólnej geometrii. Format, kadrowanie, czcionka,
rozmiar, położenie i przybliżenie zapisują się w projekcie i wracają po jego otwarciu.
Zdjęcie jest oznaczone jako przykładowe i nie zastępuje materiału użytkownika.

„Edytuj napisy” w nagłówku otwiera rzeczywiste segmenty gotowej transkrypcji z ich
czasami. Zapis poprawionego tekstu zachowuje początek i koniec segmentu. Przy tej samej
liczbie słów zachowuje ich czasy; dodanie lub usunięcie słów rozkłada je ponownie
w istniejącym przedziale czasowym i prosi o sprawdzenie synchronizacji w podglądzie.
Edycja zapisuje się lokalnie, bez wywołania AI ani ponownej transkrypcji.

Podążanie za twarzą wykrywa twarz lokalnie około 8 razy na sekundę. Wygładzanie
uwzględnia rzeczywisty upływ czasu (stała 0,48 s), a ograniczone krzywe sześcienne
wyznaczają położenie każdej klatki bez przeskoków i przekraczania celów ruchu.
Podążanie korzysta z wybranego kadru eksportu. Rzeczywisty eksport jest sprawdzany
dla 2 FPS, 60 FPS, zmiennego klatkażu i tempa 1,1×, z zachowaniem ostatniej klatki.

## Platform
Windows desktop, Python 3.11+ / PySide6 + QML (Qt Quick).
Logika mediów pozostaje w Pythonie; interfejs komunikuje się z backendem QObject.
