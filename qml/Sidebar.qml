import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    color: Theme.sidebar
    ScrollView {
        objectName: "settingsScroll"
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 18
            anchors.margins: 24
            Item { Layout.preferredHeight: 6 }
            ColumnLayout {
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; spacing: 6
                Label { text: "Po Twojemu"; color: Theme.text; font.pixelSize: 23; font.weight: Font.DemiBold }
                Label { text: "Ustaw styl swoich klipów."; color: Theme.muted; font.pixelSize: 12 }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24
                enabled: !backend.busy; spacing: 12
                Label { text: "TRYB TWORZENIA"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1 }
                SegmentTabs { objectName: "settingsModeTabs"; Layout.fillWidth: true; options: ["AI klipy", "Film · minuty"]; value: backend.settings.mode; onChosen: value => backend.setSetting("mode", value) }
                Label { Layout.fillWidth: true; text: backend.settings.mode === "AI klipy" ? "Liczbę klipów dobierzemy automatycznie do filmu." : "Cały film podzielimy na kolejne minutowe części."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Label { text: "DŁUGOŚĆ KLIPU"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                RowLayout {
                    Layout.fillWidth: true; enabled: backend.settings.mode === "AI klipy"
                    Field { objectName: "minimumField"; Layout.fillWidth: true; text: backend.settings.minimum; placeholderText: "Od"; Accessible.name: "Minimalna długość w sekundach"; onEditingFinished: backend.setSetting("minimum", text) }
                    Label { text: "–"; color: Theme.muted }
                    Field { Layout.fillWidth: true; text: backend.settings.maximum; placeholderText: "Do"; Accessible.name: "Maksymalna długość w sekundach"; onEditingFinished: backend.setSetting("maximum", text) }
                    Label { text: "s"; color: Theme.muted }
                }
                Label { text: "FORMAT I KADROWANIE"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                SegmentTabs { objectName: "settingsFormatTabs"; Layout.fillWidth: true; options: ["Pionowy 9:16", "Oryginalny"]; value: backend.settings.format; onChosen: value => backend.setSetting("format", value) }
                Choice { objectName: "settingsFramingChoice"; Layout.fillWidth: true; model: backend.framingLabels; currentIndex: backend.framingLabels.indexOf(backend.settings.framing); enabled: backend.settings.format === "Pionowy 9:16"; Accessible.name: "Kadrowanie"; onActivated: backend.setSetting("framing", currentText) }
                Label { Layout.fillWidth: true; text: backend.framingHelp; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: backend.settings.format === "Pionowy 9:16" && backend.settings.framing === "Cały obraz · czarne pasy"
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Przybliżenie kadru"; color: Theme.text; font.pixelSize: 12 }
                        Item { Layout.fillWidth: true }
                        Label { objectName: "fitZoomLabel"; text: Number(backend.settings.fit_zoom).toLocaleString(Qt.locale("pl_PL"), "f", 1) + "×"; color: Theme.muted; font.pixelSize: 12 }
                    }
                    SettingSlider {
                        objectName: "fitZoomSlider"
                        Layout.fillWidth: true
                        from: 1; to: 4; stepSize: .1
                        value: backend.settings.fit_zoom
                        Accessible.name: "Przybliżenie kadru w czarnych pasach"
                        onMoved: backend.setSetting("fit_zoom", value)
                    }
                    Label { Layout.fillWidth: true; text: "Przesuń obraz w telefonie, aby wybrać miejsce. Poza obrazem zostają czarne pasy."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                }
                Label { text: "DODATKI EKSPORTU"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                ColumnLayout {
                    spacing: 2
                    ToggleSwitch { objectName: "burnSwitch"; text: "Napisy słowo po słowie"; checked: backend.settings.burn; onToggled: backend.setSetting("burn", checked) }
                    ToggleSwitch { objectName: "colorSwitch"; text: "Delikatna korekcja kolorów"; checked: backend.settings.light_color; onToggled: backend.setSetting("light_color", checked) }
                    ToggleSwitch { objectName: "tempoSwitch"; text: "Przyspieszenie 1,1×"; checked: backend.settings.speed_up; onToggled: backend.setSetting("speed_up", checked) }
                    ToggleSwitch { objectName: "mirrorSwitch"; text: "Odbicie lustrzane"; checked: backend.settings.mirror; onToggled: backend.setSetting("mirror", checked) }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    enabled: backend.settings.burn
                    spacing: 8
                    Label { text: "STYL NAPISÓW"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                    FontChoice {
                        objectName: "captionFontChoice"
                        Layout.fillWidth: true
                        model: backend.fontChoices
                        currentIndex: backend.fontChoices.indexOf(backend.settings.caption_font)
                        Accessible.name: "Czcionka napisów"
                        onActivated: backend.setSetting("caption_font", currentText)
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Rozmiar"; color: Theme.text; font.pixelSize: 12 }
                        SettingSlider { objectName: "captionSizeSlider"; Layout.fillWidth: true; from: 24; to: 160; stepSize: 2; value: backend.captionSize; Accessible.name: "Rozmiar napisów w pikselach dla kadru 1080"; onMoved: backend.setSetting("caption_size", value) }
                        Field {
                            objectName: "captionSizeField"
                            Layout.preferredWidth: 58
                            text: String(backend.captionSize)
                            padding: 8
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: 24; top: 160; decimals: 1; locale: "C" }
                            Accessible.name: "Rozmiar napisów od 24 do 160 pikseli"
                            onEditingFinished: { backend.setSetting("caption_size", Number(text)); text = Qt.binding(function() { return String(backend.captionSize); }); }
                        }
                    }
                    Label { Layout.fillWidth: true; text: "Pozycja środka napisów · % kadru"; color: Theme.muted; font.pixelSize: 11 }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "X"; color: Theme.muted; font.pixelSize: 12 }
                        Field {
                            objectName: "captionXField"
                            Layout.fillWidth: true
                            text: String(Math.round(backend.previewLayout.caption_x / backend.previewLayout.canvas_width * 100))
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: 0; top: 100; decimals: 1; locale: "C" }
                            Accessible.name: "Położenie napisów w poziomie od 0 do 100 procent"
                            onEditingFinished: {
                                if (!backend.settings.caption_custom) backend.setSetting("caption_y", backend.previewLayout.caption_y / backend.previewLayout.canvas_height);
                                backend.setSetting("caption_x", Number(text) / 100);
                                backend.setSetting("caption_custom", true);
                                text = Qt.binding(function() { return String(Math.round(backend.previewLayout.caption_x / backend.previewLayout.canvas_width * 100)); });
                            }
                        }
                        Label { text: "Y"; color: Theme.muted; font.pixelSize: 12 }
                        Field {
                            objectName: "captionYField"
                            Layout.fillWidth: true
                            text: String(Math.round(backend.previewLayout.caption_y / backend.previewLayout.canvas_height * 100))
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: 0; top: 100; decimals: 1; locale: "C" }
                            Accessible.name: "Położenie napisów w pionie od 0 do 100 procent"
                            onEditingFinished: {
                                if (!backend.settings.caption_custom) backend.setSetting("caption_x", backend.previewLayout.caption_x / backend.previewLayout.canvas_width);
                                backend.setSetting("caption_y", Number(text) / 100);
                                backend.setSetting("caption_custom", true);
                                text = Qt.binding(function() { return String(Math.round(backend.previewLayout.caption_y / backend.previewLayout.canvas_height * 100)); });
                            }
                        }
                    }
                    Label { Layout.fillWidth: true; text: "Przeciągnij napisy w podglądzie. Rozmiar dotyczy kadru o szerokości 1080 px; długie linie dopasują się automatycznie."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                }
                Label { text: "DOKŁADNOŚĆ TRANSKRYPCJI"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                Choice { Layout.fillWidth: true; model: ["Szybka", "Zrównoważona", "Dokładna", "Najdokładniejsza"]; currentIndex: model.indexOf(backend.settings.whisper); Accessible.name: "Dokładność transkrypcji"; onActivated: backend.setSetting("whisper", currentText) }
            }
            Label { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; text: "Wideo i transkrypcję przetwarzamy lokalnie. AI pomaga wybrać fragmenty."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            Item { Layout.preferredHeight: 24 }
        }
    }
}
