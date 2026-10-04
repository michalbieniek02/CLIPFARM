import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    implicitHeight: Math.max(352, content.implicitHeight + 40)
    readonly property var sizes: ({"720p60": "14,9", "720p30": "9,5", "480p60": "7,5", "480p30": "4,7"})
    color: Theme.surface; radius: Theme.radius; border.color: Theme.border
    ColumnLayout {
        id: content
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        Label { text: "Pobierz film z linku"; color: Theme.text; font.pixelSize: 21; font.weight: Font.DemiBold }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Label { text: "Serwis"; color: Theme.muted }
            Choice { id: provider; objectName: "vodProvider"; Layout.preferredWidth: root.width < 650 ? 112 : 150; model: backend.downloadProviders; enabled: !backend.busy }
            Label { text: "Jakość"; color: Theme.muted }
            Choice { id: quality; objectName: "vodQuality"; Layout.preferredWidth: root.width < 650 ? 122 : 160; model: backend.downloadQualities; currentIndex: 4; enabled: !backend.busy }
            Item { Layout.fillWidth: true }
        }
        Field { id: link; objectName: "vodLink"; Layout.fillWidth: true; placeholderText: "Link do filmu z Kicka, Twitcha, YouTube lub X"; enabled: !backend.busy; selectByMouse: true }
        RowLayout {
            Label { text: "Od"; color: Theme.muted }
            Field { id: begin; Layout.preferredWidth: root.width < 650 ? 94 : 125; placeholderText: "00:00:00"; enabled: !backend.busy }
            Label { text: "Do"; color: Theme.muted }
            Field { id: finish; Layout.preferredWidth: root.width < 650 ? 94 : 125; placeholderText: "Cały VOD"; enabled: !backend.busy }
            Item { Layout.fillWidth: true }
            CheckBox { id: gpu; objectName: "vodGpu"; text: root.width < 650 ? "NVENC" : "NVIDIA NVENC"; Accessible.name: "Przyspieszenie kompresji NVIDIA NVENC"; checked: true; enabled: !backend.busy && quality.currentText !== "Oryginał"; palette.windowText: Theme.text }
        }
        Label { Layout.fillWidth: true; text: quality.currentText === "Oryginał" ? "Oryginał: najlepsza dostępna jakość bez ponownego kodowania. Rozmiar zależy od źródła." : quality.currentText + " · około " + (root.sizes[quality.currentText] || "—") + " GB / 8 godzin. Przy łączeniu potrzebujesz około dwukrotnie więcej miejsca."; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; text: quality.currentText === "Oryginał" ? "Puste czasy oznaczają cały film. Zakres oryginału pobiera cały plik, a potem wycina go przy klatkach kluczowych." : "Puste czasy oznaczają cały film. Pasującą jakość pobierzemy bez ponownej kompresji; pozostałe materiały kompresujemy z zachowaniem proporcji."; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; text: "Aby wznowić, użyj tego samego linku, zakresu, jakości i folderu. Serwis Auto rozpoznaje źródło linku."; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Label { objectName: "vodProgressInfo"; Layout.fillWidth: true; visible: backend.downloadInfo.length > 0; text: backend.downloadInfo; color: Theme.text; font.pixelSize: 13; wrapMode: Text.WordWrap }
        RowLayout {
            Item { Layout.fillWidth: true }
            PrimaryButton { text: "Przerwij"; visible: backend.busy; onClicked: backend.cancelTask() }
            PrimaryButton { text: "Pobierz / wznów"; primary: true; enabled: !backend.busy && link.text.trim().length > 0; onClicked: backend.downloadVod(link.text.trim(), begin.text, finish.text, gpu.checked, provider.currentText, quality.currentText) }
        }
    }
}
