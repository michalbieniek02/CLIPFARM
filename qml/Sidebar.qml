import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    color: Theme.sidebar
    ScrollView {
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
                SegmentTabs { Layout.fillWidth: true; options: ["AI klipy", "Film · minuty"]; value: backend.settings.mode; onChosen: value => backend.setSetting("mode", value) }
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
                SegmentTabs { Layout.fillWidth: true; options: ["Pionowy 9:16", "Oryginalny"]; value: backend.settings.format; onChosen: value => backend.setSetting("format", value) }
                Choice { Layout.fillWidth: true; model: backend.framingLabels; currentIndex: backend.framingLabels.indexOf(backend.settings.framing); enabled: backend.settings.format === "Pionowy 9:16"; Accessible.name: "Kadrowanie"; onActivated: backend.setSetting("framing", currentText) }
                Label { Layout.fillWidth: true; text: backend.framingHelp; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Label { text: "DODATKI EKSPORTU"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                ColumnLayout {
                    spacing: 2
                    ToggleSwitch { text: "Napisy słowo po słowie"; checked: backend.settings.burn; onToggled: backend.setSetting("burn", checked) }
                    ToggleSwitch { text: "Delikatna korekcja kolorów"; checked: backend.settings.light_color; onToggled: backend.setSetting("light_color", checked) }
                    ToggleSwitch { text: "Przyspieszenie 1,1×"; checked: backend.settings.speed_up; onToggled: backend.setSetting("speed_up", checked) }
                    ToggleSwitch { text: "Odbicie lustrzane"; checked: backend.settings.mirror; onToggled: backend.setSetting("mirror", checked) }
                }
                Label { text: "DOKŁADNOŚĆ TRANSKRYPCJI"; color: Theme.muted; font.pixelSize: 10; font.letterSpacing: 1; Layout.topMargin: 8 }
                Choice { Layout.fillWidth: true; model: ["Szybka", "Zrównoważona", "Dokładna", "Najdokładniejsza"]; currentIndex: model.indexOf(backend.settings.whisper); Accessible.name: "Dokładność transkrypcji"; onActivated: backend.setSetting("whisper", currentText) }
            }
            Label { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; text: "Wideo i transkrypcję przetwarzamy lokalnie. AI pomaga wybrać fragmenty."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            Item { Layout.preferredHeight: 24 }
        }
    }
}
