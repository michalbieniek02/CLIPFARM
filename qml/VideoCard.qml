import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
Rectangle {
    id: root
    implicitHeight: backend.videoPath ? (root.width < 600 ? 228 : 192) : 224
    color: drop.containsDrag ? Theme.raised : Theme.surface
    radius: Theme.radius
    layer.enabled: true
    layer.effect: MultiEffect { shadowEnabled: true; shadowColor: "#30000000"; shadowBlur: 0.3; shadowVerticalOffset: 3 }
    border.color: drop.containsDrag ? Theme.focus : Theme.border
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    DropArea { id: drop; anchors.fill: parent; enabled: !backend.busy; onDropped: event => { if (event.hasUrls) { backend.dropFiles(event.urls); event.acceptProposedAction(); } } }
    RowLayout {
        anchors.fill: parent; anchors.margins: 22; spacing: 24
        Rectangle {
            Layout.preferredWidth: root.width < 600 ? 80 : (backend.videoPath ? 200 : 140)
            Layout.preferredHeight: backend.videoPath ? 114 : 140
            color: "#0d1117"; radius: 12
            Image { anchors.fill: parent; anchors.margins: backend.videoPath ? 0 : (root.width < 600 ? 12 : 24); source: backend.videoThumbnail || "../assets/clipfarm-mark.png"; fillMode: Image.PreserveAspectFit; asynchronous: true }
        }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 12
            Label { Layout.fillWidth: true; text: backend.videoName || "Zacznij od filmu"; color: Theme.text; font.pixelSize: backend.videoPath ? 20 : 25; font.weight: Font.DemiBold; elide: Text.ElideRight }
            Label { Layout.fillWidth: true; text: backend.videoPath ? backend.videoInfo : "Przeciągnij film tutaj lub wybierz go z dysku."; color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap }
            PrimaryButton { text: backend.videoPath ? "Zmień film" : "Wybierz film"; primary: !backend.videoPath; enabled: !backend.busy; onClicked: backend.chooseSource() }
            Label { visible: !!backend.videoPath && root.width < 600; Layout.fillWidth: true; text: backend.transcriptStatus; color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight }
            RowLayout {
                visible: !!backend.videoPath; Layout.fillWidth: true; spacing: 8
                Rectangle { visible: root.width >= 600; width: 6; height: 6; radius: 3; color: backend.transcriptReady ? Theme.green : Theme.muted }
                Label { visible: root.width >= 600; Layout.fillWidth: true; text: backend.transcriptStatus; color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight }
                PrimaryButton { text: "Transkrybuj"; implicitHeight: 32; font.pixelSize: 11; enabled: !backend.busy && !backend.transcriptReady; onClicked: backend.transcribeOnly() }
                PrimaryButton { text: "Wczytaj"; implicitHeight: 32; font.pixelSize: 11; enabled: !backend.busy; onClicked: backend.attachTranscript() }
                PrimaryButton { text: "Pobierz"; implicitHeight: 32; font.pixelSize: 11; enabled: backend.transcriptReady && !backend.busy; onClicked: backend.downloadTranscript() }
            }
        }
    }
}
