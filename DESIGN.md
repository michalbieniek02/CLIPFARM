# Clipfarm — Apple-inspired studio

Użytkownik poprosił o redesign w stylu iPhone'a. Jasne tło, białe powierzchnie,
niebieskie akcje i miękkie narożniki. Typografia Segoe UI Variable dostępna w Windows.

Tokeny: tło #f5f5f7, powierzchnia #ffffff, tekst #1d1d1f, tekst pomocniczy #63636e,
akcja #0071e3, kontrolka #e9e9ef, nieaktywna kontrolka #e7e7ed.
Typografia 12–32 px. Odstępy 4, 8, 12, 16, 18, 20, 24, 30 px. Narożniki 8–18 px.

Toolbar: marka, otwarcie i zapis projektu. Panel boczny: ustawienia, opis wyboru,
dokładność transkrypcji. Główna przestrzeń: rzeczywista miniatura filmu, lista klipów i eksport.
Miniatury są dekodowane lokalnie przez PyAV. Nie dostarczamy dekoracyjnego przykładowego filmu.

Tylko dostępne akcje są aktywne. Przerwanie pojawia się podczas pracy.
Pola mają niebieskie obramowanie przy focusie. Zaznaczenie steruje liczbą eksportowanych klipów.
Dziennik jest zwinięty pod Szczegóły. Panel boczny i klipy przewijają się niezależnie.
Ctrl+O wybiera film, Ctrl+S zapisuje projekt, Escape prosi o przerwanie zadania.

Przyjazne nazwy dokładności mapują się na tiny, small, medium, large-v3.
Proces przetwarzania i format zapisu projektów pozostają zgodne z pierwszą wersją.

Weryfikacja: puste i wypełnione okno 1320×880, stan pracy 1100×780,
miniatury, edycja czasów, zapis, zaznaczenie, stan przycisków i rozwijane szczegóły.

Logo: dostarczony przez użytkownika znak CLIPFARM. Pełna kompozycja na pustym ekranie,
symbol i oryginalny napis w nagłówku, sam symbol jako placeholder i ikona Windows / EXE.
Źródło oraz wersje PNG i ICO znajdują się w assets. Logo nie jest nakładane na eksportowane filmy.

Pole źródła obsługuje natywne przeciąganie jednego filmu z Windows. Podczas przeciągania
ma niebieskie obramowanie i delikatnie niebieskie tło. Drop na miniaturę, tekst i przycisk
też działa. W czasie zadania odrzuca zmianę źródła. Ścieżki są parsowane jako lista Tcl,
co zachowuje spacje i polskie znaki; błędne pliki pozostawiają obecny film i klipy.

Pod formatem znajduje się wybór kadrowania i krótki opis efektu. Domyślnie cały obraz
z czarnymi pasami; pozostałe opcje to środek oraz podążanie za twarzą. W formacie
oryginalnym kontrolka kadrowania jest nieaktywna.
Pod źródłem jest stan transkrypcji i akcje Transkrybuj / Wczytaj / Pobierz.
Po wczytaniu tekstu transkrypcja nie jest uruchamiana ponownie przy kolejnym wyborze klipów.

Napisy: krótkie frazy do 4 słów, Anton, wielkie litery, białe z ciemnym obrysem.
Jawna rozdzielczość ASS zapobiega ogromnym blokom tekstu. W trybie całego obrazu
napisy trafiają pod film na czarny pas; zbyt mały pas jest powiększany przez dopasowanie
całego obrazu do przestrzeni nad napisami. Podgląd i eksport stosują ten sam wygląd.
Grupa do 4 słów ma stałą pozycję. Przyszłe słowa pozostają niewidoczne, ale rezerwują
miejsce; kolejne pojawiają się zgodnie z czasami mowy. Aktualne słowo jest żółte,
wcześniejsze białe. Po grupie następuje nowa grupa, bez migania całego zdania.
